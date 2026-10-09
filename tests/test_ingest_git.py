"""Phase 3-b git transaction: temp bare remote and two clones simulate two hosts."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills/ingest/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("ingest_git_runtime", SCRIPTS / "ingest.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
import vaultgit
from source import Refused, parse


class Crash(Exception):
    pass


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args), check=True, capture_output=True, text=True).stdout.strip()


class IngestGitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.remote = self.root / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.remote)], check=True)
        seed = self.root / "seed"
        subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
        self.identity(seed)
        for name in ("Raw", "Concepts", "Entities", "Inbox"):
            (seed / name).mkdir()
            (seed / name / ".keep").write_text("")
        (seed / "Raw/existing.md").write_text('---\nsource_identity: "urn:synthetic:existing"\n---\n\nOld body\n')
        (seed / "notes.md").write_text("Unrelated\n")
        git(seed, "add", "-A")
        git(seed, "commit", "-qm", "baseline")
        git(seed, "remote", "add", "origin", str(self.remote))
        git(seed, "push", "-q", "origin", "main")
        self.a, self.b = self.clone("a"), self.clone("b")
        self.addCleanup(setattr, vaultgit, "HOOK", None)

    def identity(self, repo):
        git(repo, "config", "user.name", "Synthetic Host")
        git(repo, "config", "user.email", "host" + "@" + "example.invalid")
        git(repo, "config", "core.autocrlf", "false")

    def clone(self, name):
        path = self.root / name
        subprocess.run(["git", "clone", "-q", str(self.remote), str(path)], check=True)
        self.identity(path)
        return path

    def request(self, **updates):
        data = dict(source_input="text", source_kind="article", locator="urn:synthetic:one", identity="urn:synthetic:one",
                    text="Selected public evidence\n", obtained_at="2026-10-08", purpose="Study provenance",
                    purpose_origin="stated", raw_path="Raw/one.md", extraction="defuddle")
        data.update(updates)
        return data

    def session(self, host, request, members=None):
        changes, inputs, captures, results = [], {}, [], []
        for member in members or [request]:
            results.append(runtime.build(host, parse(member), changes, inputs, captures))
        return {"vault": str(host), "changes": changes, "inputs": inputs, "captures": captures, "members": results}

    def run_git(self, host, session, title=None, state=None):
        state = state or self.root / ("state-%s.json" % host.name)
        return runtime.git_apply(host, session, state, title)

    def remote_log(self):
        git(self.a, "fetch", "-q", "origin")
        return git(self.a, "log", "--format=%s", "origin/main").splitlines()

    def push_from_b(self, path, text):
        git(self.b, "pull", "-q", "--ff-only")
        (self.b / path).write_text(text)
        git(self.b, "add", "--", path)
        git(self.b, "commit", "-qm", "human: " + path)
        git(self.b, "push", "-q", "origin", "main")

    def test_create_absent_absent_commits_exact_paths_with_trailers(self):
        (self.a / "notes.md").write_text("Unrelated human edit\n")
        (self.a / "draft.md").write_text("Untracked\n")
        result = self.run_git(self.a, self.session(self.a, self.request()), "Public article")
        self.assertEqual(result["state"], "published")
        self.assertEqual(result["paths"], ["Raw/one.md"])
        self.assertEqual(git(self.a, "rev-parse", "origin/main"), result["sha"])
        self.assertEqual(git(self.a, "show", "--name-only", "--format=", result["sha"]), "Raw/one.md")
        body = git(self.a, "log", "-1", "--format=%B", result["sha"])
        self.assertTrue(body.startswith("ingest: Public article"))
        self.assertIn("Ingest-Source: urn:synthetic:one", body)
        self.assertIn("Ingest-Paths: sha256:", body)
        self.assertEqual((self.a / "notes.md").read_text(), "Unrelated human edit\n")
        self.assertIn("draft.md", git(self.a, "status", "--porcelain"))
        self.assertFalse((self.a / ".git/ingest.lock").exists())

    def test_cli_flag_and_without_flag_no_commit(self):
        request = self.root / "request.json"
        request.write_text(json.dumps(self.request()))
        run = subprocess.run([sys.executable, "-B", str(SCRIPTS / "ingest.py"), "--vault", str(self.a), "--request", str(request),
                              "--state", str(self.root / "cli.json"), "--apply", "--git", "--title", "CLI"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertEqual(json.loads(run.stdout)["status"], "published")
        self.assertEqual(self.remote_log()[0], "ingest: CLI")
        request.write_text(json.dumps(self.request(raw_path="Raw/two.md", identity="urn:synthetic:two")))
        run = subprocess.run([sys.executable, "-B", str(SCRIPTS / "ingest.py"), "--vault", str(self.a), "--request", str(request), "--apply"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertEqual(self.remote_log()[0], "ingest: CLI")

    def test_line_ending_conversion_refused(self):
        git(self.a, "config", "core.autocrlf", "input")
        with self.assertRaisesRegex(Refused, "autocrlf"):
            self.run_git(self.a, self.session(self.a, self.request()))
        self.assertFalse((self.a / "Raw/one.md").exists())
        self.assertEqual(self.remote_log(), ["baseline"])

    def test_crlf_note_round_trips_exact_bytes(self):
        crlf = b'---\r\nsource_identity: "urn:synthetic:crlf"\r\n---\r\n\r\nCRLF body\r\n'
        (self.b / "Raw/crlf.md").write_bytes(crlf)
        git(self.b, "add", "--", "Raw/crlf.md")
        git(self.b, "commit", "-qm", "human crlf")
        git(self.b, "push", "-q", "origin", "main")
        git(self.a, "pull", "-q", "--ff-only")
        self.assertEqual(vaultgit.base_bytes(self.a, "Raw/crlf.md"), crlf)
        self.assertEqual(vaultgit.local_bytes(self.a, "Raw/crlf.md"), crlf)

    def test_unrelated_staged_entry_refused(self):
        (self.a / "notes.md").write_text("Staged by a human\n")
        git(self.a, "add", "notes.md")
        with self.assertRaisesRegex(Refused, "staged"):
            self.run_git(self.a, self.session(self.a, self.request()))
        self.assertFalse((self.a / "Raw/one.md").exists())

    def test_human_edit_before_write_refused(self):
        session = self.session(self.a, self.request(raw_path="Raw/existing.md", identity="urn:synthetic:existing"))
        (self.a / "Raw/existing.md").write_text((self.a / "Raw/existing.md").read_text() + "Human line\n")
        with self.assertRaisesRegex(Refused, "stale or human-edited"):
            self.run_git(self.a, session)

    def test_human_edit_after_write_refused(self):
        vaultgit.HOOK = lambda p: p == "written" and (self.a / "Raw/one.md").write_text("Human rewrite\n")
        with self.assertRaisesRegex(Refused, "edited after write"):
            self.run_git(self.a, self.session(self.a, self.request()))
        self.assertEqual(git(self.a, "rev-list", "origin/main..HEAD"), "")

    def test_human_edit_before_add_caught_by_staged_blob(self):
        vaultgit.HOOK = lambda p: p == "pre-add" and (self.a / "Raw/one.md").write_text("Human rewrite\n")
        with self.assertRaisesRegex(Refused, "staged blob differs"):
            self.run_git(self.a, self.session(self.a, self.request()))
        self.assertEqual(git(self.a, "rev-list", "origin/main..HEAD"), "")

    def test_stale_owned_update_refused(self):
        session = self.session(self.a, self.request(raw_path="Raw/existing.md", identity="urn:synthetic:existing"))
        self.push_from_b("Raw/existing.md", '---\nsource_identity: "urn:synthetic:existing"\n---\n\nNewer remote\n')
        with self.assertRaisesRegex(Refused, "stale"):
            self.run_git(self.a, session)

    def test_base_present_local_absent_refused(self):
        session = self.session(self.a, self.request())
        self.push_from_b("Raw/one.md", "Remote created first\n")
        with self.assertRaisesRegex(Refused, "base present, local absent"):
            self.run_git(self.a, session)
        self.assertFalse((self.a / "Raw/one.md").exists())

    def test_base_absent_local_present_refused(self):
        session = self.session(self.a, self.request())
        (self.a / "Raw/one.md").write_text("Resurrected locally\n")
        with self.assertRaisesRegex(Refused, "base absent, local present"):
            self.run_git(self.a, session)
        self.assertEqual((self.a / "Raw/one.md").read_text(), "Resurrected locally\n")

    def test_concurrent_push_non_fast_forward_keeps_committed_local(self):
        state = self.root / "nonff.json"
        vaultgit.HOOK = lambda p: p == "committed" and self.push_from_b("notes.md", "Concurrent\n")
        session = self.session(self.a, self.request())
        with self.assertRaisesRegex(Refused, "non-fast-forward"):
            self.run_git(self.a, session, state=state)
        saved = runtime.state_decode(json.loads(state.read_text()))["git"]
        self.assertEqual(saved["state"], "committed-local")
        self.assertEqual(saved["sha"], git(self.a, "rev-parse", "HEAD"))
        self.assertEqual(self.remote_log()[0], "human: notes.md")
        self.assertIn(saved["sha"], git(self.a, "rev-list", "origin/main..HEAD"))

    def crash_written(self, request, state):
        def hook(p):
            if p == "written":
                raise Crash()
        vaultgit.HOOK = hook
        session = self.session(self.a, request)
        with self.assertRaises(Crash):
            self.run_git(self.a, session, state=state)
        vaultgit.HOOK = None
        (self.a / ".git/ingest.lock").exists() and self.fail("lock leaked")
        return runtime.state_decode(json.loads(state.read_text()))

    def test_crash_after_write_resume_create_and_update(self):
        for request in (self.request(), self.request(raw_path="Raw/existing.md", identity="urn:synthetic:existing")):
            state = self.root / ("crash-%s.json" % request["raw_path"].replace("/", "-"))
            saved = self.crash_written(request, state)
            self.assertEqual(saved["git"]["state"], "written")
            before = len(self.remote_log())
            result = self.run_git(self.a, saved, state=state)
            self.assertEqual(result["state"], "published")
            self.assertEqual(len(self.remote_log()), before + 1)

    def test_crash_after_write_refuses_local_and_remote_drift(self):
        state = self.root / "drift-local.json"
        saved = self.crash_written(self.request(), state)
        (self.a / "Raw/one.md").write_text("Human edit after crash\n")
        with self.assertRaisesRegex(Refused, "local postimage drift"):
            self.run_git(self.a, saved, state=state)
        state = self.root / "drift-remote.json"
        saved = self.crash_written(self.request(raw_path="Raw/existing.md", identity="urn:synthetic:existing"), state)
        self.push_from_b("Raw/existing.md", "Remote changed preimage\n")
        with self.assertRaisesRegex(Refused, "remote preimage drift"):
            self.run_git(self.a, saved, state=state)

    def test_crash_after_write_refuses_human_staged_blob_matching_disk(self):
        state = self.root / "staged-human.json"
        saved = self.crash_written(self.request(), state)
        intended = (self.a / "Raw/one.md").read_bytes()
        (self.a / "Raw/one.md").write_text("Human staged rewrite\n")
        git(self.a, "add", "--", "Raw/one.md")
        (self.a / "Raw/one.md").write_bytes(intended)
        index, head, remote = git(self.a, "ls-files", "--stage"), git(self.a, "rev-parse", "HEAD"), self.remote_log()
        with self.assertRaisesRegex(Refused, "staged owned entry differs"):
            self.run_git(self.a, saved, state=state)
        self.assertEqual(git(self.a, "ls-files", "--stage"), index)
        self.assertEqual(git(self.a, "show", ":Raw/one.md"), "Human staged rewrite")
        self.assertEqual((git(self.a, "rev-parse", "HEAD"), self.remote_log()), (head, remote))
        self.assertEqual((self.a / "Raw/one.md").read_bytes(), intended)
        self.assertFalse((self.a / ".git/ingest.lock").exists())

    def test_crash_after_write_resumes_with_intended_staged_entry(self):
        state = self.root / "staged-intended.json"
        saved = self.crash_written(self.request(), state)
        git(self.a, "add", "--", "Raw/one.md")
        before = len(self.remote_log())
        result = self.run_git(self.a, saved, state=state)
        self.assertEqual(result["state"], "published")
        self.assertEqual(len(self.remote_log()), before + 1)
        self.assertEqual(git(self.a, "show", "--name-only", "--format=", result["sha"]), "Raw/one.md")

    def test_owned_glob_like_name_is_literal_pathspec(self):
        (self.a / "Raw/existing.md").write_text("Dirty unrelated human edit\n")
        result = self.run_git(self.a, self.session(self.a, self.request(raw_path="Raw/*.md")), "Literal")
        self.assertEqual(result["state"], "published")
        self.assertEqual(git(self.a, "show", "--name-only", "--format=", result["sha"]), "Raw/*.md")
        self.assertEqual(git(self.a, "diff", "--cached", "--name-only"), "")
        self.assertEqual(git(self.a, "status", "--porcelain", "--", "Raw/existing.md"), "M Raw/existing.md")
        self.assertEqual(git(self.a, "rev-parse", ":Raw/existing.md"), git(self.a, "rev-parse", "HEAD:Raw/existing.md"))
        self.assertEqual((self.a / "Raw/existing.md").read_text(), "Dirty unrelated human edit\n")

    def test_crash_after_commit_before_push_publishes_on_resume(self):
        state = self.root / "commit.json"
        def hook(p):
            if p == "committed":
                raise Crash()
        vaultgit.HOOK = hook
        with self.assertRaises(Crash):
            self.run_git(self.a, self.session(self.a, self.request()), state=state)
        vaultgit.HOOK = None
        saved = runtime.state_decode(json.loads(state.read_text()))
        self.assertEqual(saved["git"]["state"], "committed-local")
        result = self.run_git(self.a, saved, state=state)
        self.assertEqual((result["state"], result["sha"]), ("published", saved["git"]["sha"]))
        self.assertEqual(git(self.a, "rev-parse", "origin/main"), result["sha"])

    def test_local_ahead_refuses_reset(self):
        (self.a / "notes.md").write_text("Local commit\n")
        git(self.a, "commit", "-qam", "unpublished")
        head = git(self.a, "rev-parse", "HEAD")
        with self.assertRaisesRegex(Refused, "ahead"):
            self.run_git(self.a, self.session(self.a, self.request()))
        self.assertEqual(git(self.a, "rev-parse", "HEAD"), head)
        self.assertFalse((self.a / "Raw/one.md").exists())

    def test_same_title_different_source_two_commits(self):
        first = self.run_git(self.a, self.session(self.a, self.request()), "Same title")
        second = self.run_git(self.a, self.session(self.a, self.request(raw_path="Raw/two.md", identity="urn:synthetic:two")),
                              "Same title", self.root / "second.json")
        self.assertNotEqual(first["sha"], second["sha"])
        trailers = git(self.a, "log", "-2", "--format=%(trailers:key=Ingest-Source,valueonly)", "origin/main").split()
        self.assertEqual(sorted(trailers), ["urn:synthetic:one", "urn:synthetic:two"])

    def test_canary_a_batch_is_one_commit(self):
        member = self.request(analyses=[dict(path="Concepts/scope.md", body="Bounded", quote="Selected public evidence", anchor="l1", role="concept",
                                             confidence="medium — one synthetic public line"),
                                        dict(path="Entities/source.md", body="Source", quote="Selected public evidence", anchor="l1", role="entity", description="Synthetic source")])
        other = self.request(raw_path="Raw/two.md", identity="urn:synthetic:two")
        before = len(self.remote_log())
        result = self.run_git(self.a, self.session(self.a, None, [member, other]), "Canary A")
        self.assertEqual(len(self.remote_log()), before + 1)
        self.assertEqual(sorted(git(self.a, "show", "--name-only", "--format=", result["sha"]).split()),
                         ["Concepts/scope.md", "Entities/source.md", "Raw/one.md", "Raw/two.md"])

    def outside(self, name, blob):
        path = self.root / name
        path.write_bytes(blob)
        return str(path), runtime.digest(blob)

    def test_combined_create_and_update_members_are_one_owned_commit(self):
        secondary = '---\nsource_identity: "urn:synthetic:secondary"\nreferenced: []\n---\n\n## Original Content\n\nSecondary author wrote this.\n'
        concept = "---\ntype: note\n---\n\n# Topic\n\n## Owner section\nHuman paragraph\n"
        self.push_from_b("Raw/secondary.md", secondary)
        self.push_from_b("Concepts/topic.md", concept)
        git(self.a, "pull", "-q", "--ff-only")
        (self.a / "notes.md").write_text("Unrelated human edit\n")
        sec_before, con_before = secondary.encode(), concept.encode()
        sec_after = runtime.patch_fields(sec_before, {"referenced": ["[[Raw/primary]]"]})
        con_after = con_before.replace(b"# Topic\n\n", b"# Topic\n\n## Overview\nReviewed\n\n")
        start = sec_before.index(b"Secondary author")
        owner = con_before.index(b"## Owner section")
        pdf = b"%PDF-1.4\nsynthetic original\n%%EOF\n"
        pdf_path, pdf_sha = self.outside("orig.pdf", pdf)
        sec_path, sec_sha = self.outside("secondary-post.md", sec_after)
        con_path, con_sha = self.outside("concept-post.md", con_after)
        primary = self.request(raw_path="Raw/primary.md", attachment_path="Raw/primary.pdf", attachment_source=pdf_path, attachment_sha256=pdf_sha,
                               coverage="full", notes=["Text layer checked against page image"],
                               analyses=[dict(path="Entities/primary.md", role="entity", body="Primary author", quote="Selected public evidence", anchor="l1",
                                              description="Synthetic primary author", related=["[[Entities/secondary]]"])])
        sec_member = {"update_path": "Raw/secondary.md", "preimage_sha256": runtime.digest(sec_before), "postimage_file": sec_path, "postimage_sha256": sec_sha,
                      "preserve": [{"block": "original_content", "start": start, "end": len(sec_before), "sha256": runtime.digest(sec_before[start:])}],
                      "obtained_at": "2026-10-08",
                      "analyses": [dict(path="Entities/secondary.md", role="entity", body="Secondary author", quote="Secondary author wrote this.", anchor="Original Content",
                                        description="Synthetic secondary author", related=["[[Entities/primary]]"])]}
        con_member = {"update_path": "Concepts/topic.md", "preimage_sha256": runtime.digest(con_before), "postimage_file": con_path, "postimage_sha256": con_sha,
                      "preserve": [{"block": "body", "start": owner, "end": len(con_before), "sha256": runtime.digest(con_before[owner:])}]}
        session = runtime.plan(self.a, {"purpose": "Study provenance", "members": [primary, sec_member, con_member]})
        rows = {r["path"]: r for r in session["changes"]}
        self.assertEqual((rows["Raw/secondary.md"]["before"], rows["Raw/secondary.md"]["after"]), (sec_before, sec_after))
        self.assertEqual((rows["Concepts/topic.md"]["before"], rows["Concepts/topic.md"]["after"]), (con_before, con_after))
        before = len(self.remote_log())
        result = self.run_git(self.a, session, "Combined")
        self.assertEqual(result["state"], "published")
        self.assertEqual(len(self.remote_log()), before + 1)
        owned = ["Concepts/topic.md", "Entities/primary.md", "Entities/secondary.md", "Raw/primary.md", "Raw/primary.pdf", "Raw/secondary.md"]
        self.assertEqual(sorted(git(self.a, "show", "--name-only", "--format=", result["sha"]).split()), owned)
        self.assertEqual(subprocess.run(["git", "-C", str(self.a), "cat-file", "blob", "origin/main:Raw/primary.pdf"], capture_output=True).stdout, pdf)
        self.assertEqual((self.a / "Raw/secondary.md").read_bytes(), sec_after)
        self.assertEqual((self.a / "Concepts/topic.md").read_bytes(), con_after)
        self.assertIn(b"Notes:\n- Text layer checked against page image\n", (self.a / "Raw/primary.md").read_bytes())
        self.assertEqual((self.a / "notes.md").read_text(), "Unrelated human edit\n")

    def test_legacy_raw_short_span_refused_before_any_git_effect(self):
        leaf = "10. Raw Sources/legacy.md"
        before = "---\r\ntitle: legacy\r\n---\r\n\ufeff\r\n# Legacy capture\r\n\r\nPara one\r\n\r\nPara two tail\r\n".encode()
        git(self.b, "pull", "-q", "--ff-only")
        (self.b / "10. Raw Sources").mkdir()
        (self.b / leaf).write_bytes(before)
        git(self.b, "add", "--", leaf)
        git(self.b, "commit", "-qm", "human: legacy raw")
        git(self.b, "push", "-q", "origin", "main")
        git(self.a, "pull", "-q", "--ff-only")
        (self.a / "notes.md").write_text("Unrelated human edit\n")
        after = b'---\r\ntype: "article"\r\ntitle: legacy\r\n---\r\n' + before[before.index("\ufeff".encode()):before.index(b"Para two")]
        post, sha = self.outside("legacy-post.md", after)
        start = before.index(b"Para one")
        member = {"update_path": leaf, "preimage_sha256": runtime.digest(before), "postimage_file": post, "postimage_sha256": sha,
                  "purpose": "Study provenance", "purpose_origin": "stated",
                  "preserve": [{"block": "body", "start": start, "end": start + 10, "sha256": runtime.digest(before[start:start + 10])}]}
        request = self.root / "legacy-request.json"
        request.write_text(json.dumps(member))
        head, remote, index = git(self.a, "rev-parse", "HEAD"), self.remote_log(), git(self.a, "write-tree")
        state = self.root / "legacy-state.json"
        run = subprocess.run([sys.executable, "-B", str(SCRIPTS / "ingest.py"), "--vault", str(self.a), "--request", str(request),
                              "--state", str(state), "--apply", "--git", "--title", "Legacy"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("unchanged prefix", json.loads(run.stdout)["error"])
        self.assertEqual((self.a / leaf).read_bytes(), before)
        self.assertEqual((git(self.a, "rev-parse", "HEAD"), self.remote_log(), git(self.a, "write-tree")), (head, remote, index))
        self.assertEqual(git(self.a, "diff", "--cached", "--name-only"), "")
        self.assertEqual(git(self.a, "status", "--porcelain"), "M notes.md")
        self.assertFalse(state.exists())
        self.assertFalse((self.a / ".git/ingest.lock").exists())

    def inbox_ingested(self):
        (self.a / "Inbox/one.md").write_text("Selected inbox note\n")
        git(self.a, "add", "Inbox/one.md")
        git(self.a, "commit", "-qm", "human: inbox")
        git(self.a, "push", "-q", "origin", "main")
        state = self.root / "inbox-state.json"
        session = self.session(self.a, self.request(source_input="file", locator="Inbox/one.md", text=""))
        self.run_git(self.a, session, state=state)
        return state

    def inbox_delete(self, state):
        request = self.root / "delete.json"
        digest = "sha256:" + __import__("hashlib").sha256((self.a / "Inbox/one.md").read_bytes()).hexdigest()
        request.write_text(json.dumps({"approval_state": "approved", "approval_effect": ["delete"], "approval_basis": "Synthetic.",
                                       "approval_scope": ["Inbox/one.md"], "approval_preimage": {"Inbox/one.md": digest}}))
        run = subprocess.run([sys.executable, "-B", str(REPO / "skills/inbox/scripts/inbox.py"), "delete", "--vault", str(self.a),
                              "--scope", "Inbox", "--request", str(request), "--ingest-state", str(state)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout)
        result = self.root / "deleted.json"
        result.write_text(run.stdout)
        return result

    def record(self, state, deleted):
        run = subprocess.run([sys.executable, "-B", str(SCRIPTS / "ingest.py"), "--vault", str(self.a), "--apply-state", str(state),
                              "--record-deletions", str(deleted)], capture_output=True, text=True)
        return run.returncode, json.loads(run.stdout)

    def test_inbox_delete_recorded_as_one_published_commit(self):
        state = self.inbox_ingested()
        ingest_sha = git(self.a, "rev-parse", "origin/main")
        (self.a / "notes.md").write_text("Unrelated dirty edit\n")
        code, result = self.record(state, self.inbox_delete(state))
        self.assertEqual(code, 0, result)
        self.assertEqual(result["state"], "published")
        self.assertEqual(git(self.a, "rev-parse", "HEAD"), git(self.a, "rev-parse", "origin/main"))
        self.assertEqual(self.remote_log()[0], "inbox: delete 1 ingested originals")
        self.assertEqual(git(self.a, "show", "--name-status", "--format=", "HEAD"), "D\tInbox/one.md")
        self.assertIn("Ingest-Source: " + ingest_sha, git(self.a, "log", "-1", "--format=%B"))
        self.assertEqual((self.a / "notes.md").read_text(), "Unrelated dirty edit\n")
        self.assertIn("Raw/one.md", git(self.a, "ls-tree", "-r", "--name-only", "origin/main"))

    def test_inbox_delete_record_refuses_remote_drift_and_resurrection(self):
        state = self.inbox_ingested()
        deleted = self.inbox_delete(state)
        (self.a / "Inbox/one.md").write_text("Resurrected\n")
        code, result = self.record(state, deleted)
        self.assertEqual(code, 1, result)
        self.assertIn("local postimage drift", result["error"])
        (self.a / "Inbox/one.md").unlink()
        self.push_from_b("Inbox/one.md", "Remote session append\n")
        code, result = self.record(state, deleted)
        self.assertEqual(code, 1, result)
        self.assertIn("remote preimage drift", result["error"])
        self.assertEqual(len([l for l in self.remote_log() if l.startswith("inbox:")]), 0)

    def test_inbox_delete_record_refuses_unpublished_ingest_and_foreign_path(self):
        state = self.inbox_ingested()
        deleted = self.root / "foreign.json"
        deleted.write_text(json.dumps({"deleted_paths": ["notes.md"]}))
        self.assertEqual(self.record(state, deleted)[0], 1)
        saved = runtime.state_decode(json.loads(state.read_text()))
        saved["git"]["state"] = "committed-local"
        state.write_text(json.dumps(runtime.state_encode(saved)))
        code, result = self.record(state, self.inbox_delete(state))
        self.assertEqual(code, 1, result)
        self.assertIn("published", result["error"])

    def book_on_remote(self):
        """A synthetic chapter stub (with human Reading Notes) and its Book Index, published by host B."""
        placeholder = runtime.stub_placeholder().decode()
        chapter = ('---\ntype: book\nstatus: stub\ndate_modified: "2026-10-01"\nsource_url: "https://example.org/order/ch01"\n'
                   'source_locator: "https://example.org/order/ch01"\nbookIndex: "[[Raw/index]]"\nchapterNumber: 1\nchapterPart: "제1부"\n'
                   'chapterPrev: null\nchapterNext: "[[Raw/ch2]]"\n---\n\n# First\n\n## Original Content\n\n' + placeholder
                   + "\n\n## Reading Notes\n\n사람이 쓴 메모\n")
        index = ('---\ntype: book\nsource_locator: "https://example.org/order"\n---\n\n# Order\n\n## Original Content\n\nPreface\n\n## TOC\n\n'
                 "- [ ] [[Raw/ch1]] — First\n- [ ] [[Raw/ch2]] — Second\n\n## Progress Tracking\n\n| Ch | Title | Status | Read on |\n| --- | --- | --- | --- |\n"
                 "| 1 | [[Raw/ch1]] | stub | — |\n| 2 | [[Raw/ch2]] | stub | — |\n")
        git(self.b, "pull", "-q", "--ff-only")
        for name, text in (("Raw/ch1.md", chapter), ("Raw/ch2.md", chapter.replace("Raw/ch2", "Raw/ch1")), ("Raw/index.md", index)):
            (self.b / name).write_bytes(text.encode())
        git(self.b, "add", "--", "Raw/ch1.md", "Raw/ch2.md", "Raw/index.md")
        git(self.b, "commit", "-qm", "human: book scaffold")
        git(self.b, "push", "-q", "origin", "main")
        git(self.a, "pull", "-q", "--ff-only")
        return chapter.encode(), index.encode()

    def promotion_member(self, chapter, index, text, coverage):
        placeholder = runtime.stub_placeholder()
        start = chapter.index(placeholder)
        status = "completed" if coverage == "full" else "reading"
        post = runtime.patch_fields(chapter[:start] + text + chapter[start + len(placeholder):], {"status": status, "date_modified": "2026-10-09"})
        index_post = index.replace("| 1 | [[Raw/ch1]] | stub | — |".encode(), ("| 1 | [[Raw/ch1]] | %s | 2026-10-09 |" % status).encode())
        # The actually read chapter is checked for reading and completed alike; the row status keeps coverage explicit.
        index_post = index_post.replace(b"- [ ] [[Raw/ch1]]", b"- [x] [[Raw/ch1]]")
        files = {}
        for name, blob in (("post.md", post), ("text.txt", text), ("index.md", index_post)):
            (self.root / name).write_bytes(blob)
            files[name] = (str(self.root / name), runtime.digest(blob))
        member = {"update_path": "Raw/ch1.md", "preimage_sha256": runtime.digest(chapter), "postimage_file": files["post.md"][0], "postimage_sha256": files["post.md"][1],
                  "purpose": "Read chapter one", "purpose_origin": "stated", "obtained_at": "2026-10-09",
                  "analyses": [dict(path="Concepts/order.md", role="concept", body="Order idea", quote="beyond order", anchor="p. 3",
                                    confidence="medium — one synthetic chapter passage")],
                  "promotion": {"placeholder": {"start": start, "end": start + len(placeholder), "sha256": runtime.digest(placeholder)},
                                "text_file": files["text.txt"][0], "text_sha256": files["text.txt"][1], "locator": "https://example.org/order/ch01",
                                "coverage": coverage, "date": "2026-10-09",
                                "index": {"path": "Raw/index.md", "preimage_sha256": runtime.digest(index), "postimage_file": files["index.md"][0], "postimage_sha256": files["index.md"][1]}}}
        return member, post, index_post

    def test_book_promotion_and_index_progress_publish_as_one_commit(self):
        chapter, index = self.book_on_remote()
        sibling = (self.a / "Raw/ch2.md").read_bytes()
        member, post, index_post = self.promotion_member(chapter, index, "Synthetic chapter text beyond order.\n".encode(), "full")
        result = self.run_git(self.a, runtime.plan(self.a, member), "Order ch1")
        self.assertEqual(result["state"], "published")
        self.assertEqual(result["paths"], ["Concepts/order.md", "Raw/ch1.md", "Raw/index.md"])
        self.assertEqual(self.remote_log()[:2], ["ingest: Order ch1", "human: book scaffold"])
        self.assertEqual(git(self.a, "show", "--name-only", "--format=", result["sha"]).splitlines(), ["Concepts/order.md", "Raw/ch1.md", "Raw/index.md"])
        self.assertEqual(vaultgit.base_bytes(self.a, "Raw/ch1.md"), post)
        self.assertEqual(vaultgit.base_bytes(self.a, "Raw/index.md"), index_post)
        self.assertIn("사람이 쓴 메모".encode(), post)
        self.assertIn(b"- [ ] [[Raw/ch2]]", index_post)
        self.assertEqual((self.a / "Raw/ch2.md").read_bytes(), sibling)
        self.assertEqual(git(self.a, "status", "--porcelain"), "")

    def test_titled_scaffold_publishes_then_promotes_preserving_title_and_reading_paths(self):
        title, paths = "질서 너머 — Synthetic Edition", "Path A: Part One first.\n\n- Path B: chapter two alone\n"
        scaffold = self.request(source_kind="book", raw_path="Raw/index.md", text="Public preface\n", book_title=title, reading_paths=paths, chapters=[
            dict(path="Raw/ch1.md", title="First", part="제1부", locator="https://example.org/order/ch01", toc_description="Obtained one-liner."),
            dict(path="Raw/ch2.md", title="Second", part="제1부")])
        result = self.run_git(self.a, self.session(self.a, scaffold), "Order scaffold")
        self.assertEqual(result["state"], "published")
        self.assertEqual(result["paths"], ["Raw/ch1.md", "Raw/ch2.md", "Raw/index.md"])
        chapter, index = vaultgit.base_bytes(self.a, "Raw/ch1.md"), vaultgit.base_bytes(self.a, "Raw/index.md")
        self.assertIn(("\n# " + title + "\n\n## Original Content\n").encode(), index)
        self.assertIn(("## Reading Paths\n\n" + paths + "\n\n## Progress Tracking").encode(), index)
        member, post, index_post = self.promotion_member(chapter, index, "Synthetic chapter text beyond order.\n".encode(), "full")
        result = self.run_git(self.a, runtime.plan(self.a, member), "Order ch1")
        self.assertEqual(result["state"], "published")
        self.assertEqual(self.remote_log()[:2], ["ingest: Order ch1", "ingest: Order scaffold"])
        self.assertEqual(vaultgit.base_bytes(self.a, "Raw/index.md"), index_post)
        self.assertIn(("- [x] [[Raw/ch1]] — First — Obtained one-liner.\n- [ ] [[Raw/ch2]] — Second\n").encode(), index_post)
        self.assertIn(("## Reading Paths\n\n" + paths + "\n\n## Progress Tracking").encode(), index_post)
        self.assertEqual(vaultgit.base_bytes(self.a, "Raw/ch1.md"), post)
        self.assertIn(b"## TOC Preview\n\nObtained one-liner.\n", post)
        self.assertEqual(git(self.a, "status", "--porcelain"), "")

    def test_book_promotion_refuses_remote_reading_notes_edit(self):
        chapter, index = self.book_on_remote()
        member, post, _ = self.promotion_member(chapter, index, b"Partial synthetic text beyond order.\n", "partial")
        session = runtime.plan(self.a, member)
        self.push_from_b("Raw/ch1.md", chapter.decode().replace("사람이 쓴 메모", "사람이 고친 메모"))
        with self.assertRaisesRegex(Refused, "stale"):
            self.run_git(self.a, session)
        self.assertEqual((self.a / "Raw/ch1.md").read_bytes(), chapter)
        self.assertEqual((self.a / "Raw/index.md").read_bytes(), index)
        self.assertEqual(self.remote_log()[0], "human: Raw/ch1.md")

if __name__ == "__main__":
    unittest.main()
