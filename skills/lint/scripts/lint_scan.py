"""Bounded Markdown, link, boundary, and cross-vault lint checks."""
import hashlib
import os
from pathlib import Path
import re
from typing import Dict, List, Set, Tuple


class Refused(Exception):
    """A path, request, or policy input cannot be used safely."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def digest(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def text(value, field: str, empty: bool = False) -> str:
    if not isinstance(value, str) or "\x00" in value or (not empty and not value.strip()):
        raise Refused("invalid_input", field + " must be text")
    return value


def relative(value: str) -> str:
    text(value, "path")
    if (
        "\\" in value
        or ":" in value
        or any(part in ("", ".", "..") or part.startswith(".") for part in value.split("/"))
    ):
        raise Refused("unsafe_path", "path must be literal and vault-relative")
    return value


def route(root: Path, value: str) -> Path:
    path = root
    for part in relative(value).split("/"):
        path = path / part
        if path.is_symlink():
            raise Refused("unsafe_path", "symlink in selected path")
    return path


def corpus(root: Path, scopes: List[str]) -> List[str]:
    notes: Set[str] = set()
    for scope in scopes:
        selected = route(root, scope)
        if selected.is_file() and selected.suffix == ".md":
            notes.add(scope)
        elif selected.is_dir():
            for parent, directories, filenames in os.walk(str(selected), followlinks=False):
                base = Path(parent)
                directories[:] = sorted(
                    name
                    for name in directories
                    if not name.startswith(".") and not (base / name).is_symlink()
                )
                for filename in sorted(filenames):
                    item = base / filename
                    if (
                        filename.startswith(".")
                        or item.is_symlink()
                        or not item.is_file()
                        or item.suffix != ".md"
                    ):
                        continue
                    notes.add(item.relative_to(root).as_posix())
        else:
            raise Refused("missing_scope", "scope is not an existing note or directory")
    return sorted(notes)


def note_index(root: Path) -> Dict[str, str]:
    """Index note names from directory metadata without opening note bodies."""
    by_name: Dict[str, str] = {}
    for parent, directories, filenames in os.walk(str(root), followlinks=False):
        base = Path(parent)
        directories[:] = [
            name
            for name in directories
            if not name.startswith(".") and not (base / name).is_symlink()
        ]
        for filename in filenames:
            item = base / filename
            if (
                filename.startswith(".")
                or item.is_symlink()
                or not item.is_file()
                or item.suffix != ".md"
            ):
                continue
            path = item.relative_to(root).as_posix()
            by_name[path[:-3]] = path
            by_name.setdefault(item.stem, path)
    return by_name


def metadata(body: str) -> Tuple[Dict[str, str], str]:
    if not body.startswith("---\n"):
        return {}, "missing frontmatter"
    end = body.find("\n---\n", 4)
    if end < 0:
        return {}, "unterminated frontmatter"
    result: Dict[str, str] = {}
    for line in body[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result, ""


def links(body: str) -> List[str]:
    return re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]", body)


def link_key(value: str) -> str:
    """Remove one real Markdown suffix without truncating legal title characters."""
    return value[:-3] if value.endswith(".md") else value


def finding(category: str, path: str, detail: str) -> dict:
    return {"category": category, "path": path, "detail": detail}


def check_note(
    path: str,
    body: str,
    required: List[str],
    known: Dict[str, str],
) -> Tuple[List[dict], List[str]]:
    found: List[dict] = []
    properties, structure_error = metadata(body)
    if structure_error:
        found.append(finding("structure", path, structure_error))
    if not re.search(r"^# [^\n]+$", body, flags=re.MULTILINE):
        found.append(finding("structure", path, "missing level-one heading"))
    for key in required:
        if key not in properties:
            found.append(finding("properties", path, key))
    definitions = set(re.findall(r"^\[\^([^\]]+)\]:", body, flags=re.MULTILINE))
    references = set(re.findall(r"\[\^([^\]]+)\](?!:)", body))
    for identifier in sorted(references - definitions):
        found.append(finding("citations", path, identifier))
    local_links = []
    for link in links(body):
        if link.startswith("vault:"):
            continue
        local_links.append(link)
        if link_key(link) not in known:
            found.append(finding("broken_link", path, link))
    return found, local_links


def boundary_findings(
    selected: List[str],
    bodies: Dict[str, str],
    known: Dict[str, str],
    boundaries: List[dict],
) -> List[dict]:
    found: List[dict] = []
    for boundary in boundaries:
        if not isinstance(boundary, dict) or set(boundary) != {
            "name",
            "root",
            "forbidden_roots",
        }:
            raise Refused("invalid_input", "boundary fields are invalid")
        name = text(boundary["name"], "boundary name")
        root = relative(text(boundary["root"], "boundary root")).rstrip("/") + "/"
        forbidden = boundary["forbidden_roots"]
        if not isinstance(forbidden, list) or any(not isinstance(item, str) for item in forbidden):
            raise Refused("invalid_input", "forbidden_roots must be a path list")
        roots = [relative(item).rstrip("/") + "/" for item in forbidden]
        for path in selected:
            if not path.startswith(root):
                continue
            for link in links(bodies[path]):
                resolved = known.get(link_key(link), "")
                if any(resolved.startswith(item) for item in roots):
                    found.append(finding("persona_boundary", path, name + ": " + link))
    return found


def cross_vault_findings(
    selected: List[str],
    bodies: Dict[str, str],
    cross_vault,
) -> Tuple[List[dict], List[str], dict]:
    encountered = [
        link
        for path in selected
        for link in links(bodies[path])
        if link.startswith("vault:")
    ]
    if cross_vault is None:
        limits = []
        if encountered:
            limits.append(
                "Cross-vault links were encountered, but no target or read permission "
                "was supplied."
            )
        return [], limits, {
            "target_name": "",
            "permission_confirmed": False,
            "checked": False,
            "links_encountered": len(encountered),
            "blocks_fix": bool(encountered),
        }
    required = {"target_name", "target_root", "permission_state", "permission_basis"}
    if not isinstance(cross_vault, dict) or set(cross_vault) != required:
        raise Refused("invalid_input", "cross_vault fields are invalid")
    name = text(cross_vault["target_name"], "cross-vault target name")
    permitted = (
        cross_vault["permission_state"] == "approved"
        and isinstance(cross_vault["permission_basis"], str)
        and bool(cross_vault["permission_basis"].strip())
    )
    target_root = Path(cross_vault["target_root"]).absolute()
    if not permitted or target_root.is_symlink() or not target_root.is_dir():
        return [], ["Cross-vault target or read permission is unconfirmed."], {
            "target_name": name,
            "permission_confirmed": False,
            "checked": False,
            "links_encountered": len(encountered),
            "blocks_fix": True,
        }
    target_index = note_index(target_root)
    found: List[dict] = []
    prefix = "vault:" + name + "/"
    unchecked = [link for link in encountered if not link.startswith(prefix)]
    for path in selected:
        for link in links(bodies[path]):
            if link.startswith(prefix) and link_key(link[len(prefix) :]) not in target_index:
                found.append(finding("cross_vault_link", path, link))
    limits = []
    if unchecked:
        limits.append("Cross-vault links outside the confirmed target were not checked.")
    return found, limits, {
        "target_name": name,
        "permission_confirmed": True,
        "checked": True,
        "links_encountered": len(encountered),
        "blocks_fix": bool(unchecked),
    }
