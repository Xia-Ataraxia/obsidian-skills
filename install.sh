#!/usr/bin/env sh
# install.sh — obsidian-skills installer for Agent Skills runtimes.
#
# What this script does
#   * resolves the confirmed route for a runtime and prints the commands you run
#     yourself, together with the evidence each route was confirmed from;
#   * copies complete skill packages from this checkout into a confirmed native
#     skill directory, after a full pre-flight collision report and a
#     post-copy completeness readback.
#
# What this script never does
#   * reach the network;
#   * execute a runtime's install / marketplace / clone command, or any runtime
#     CLI at all;
#   * touch your profile or caches: no settings.json, config.toml, taps.json,
#     known_marketplaces.json, registry, plugin cache or lockfile is read for
#     mutation or written;
#   * overwrite, merge into, or delete anything that already existed.
#
# Writes: anchored route directories, private staging beneath the skill root,
# and atomic no-replace publication of a verified package. Failed staging may
# remain for explicit recovery; public destinations are never recursively removed.
#
# This script is the front end: the route table, the help, the option grammar
# and the selection rules. The part that touches your filesystem lives in
# scripts/install_packages.py and runs under python3 (3.8 or newer, standard
# library only), because holding a directory open and writing into *that object*
# needs openat-style calls that POSIX sh does not have. Path names alone cannot
# keep a checked directory from being swapped for a symlink before the write, or
# a reservation from being renamed away before the rollback. `copy` therefore
# requires python3 and refuses without it; there is no unanchored fallback.
#
# The approved root is $HOME for --scope user and --project-root for --scope
# project. A symlink anywhere on the route below it is refused outright — by the
# open that would otherwise have followed it — so a pre-placed link can never
# redirect a write out of the directory you named. The link and its target are
# only inspected, never followed, replaced or removed. A package whose source in
# this checkout is itself a symlink is refused rather than copied through.
#
# Dry run is the default. Copying requires an explicit --apply.
#
# Exit codes: 0 ok · 1 refused (collision / escape / unsupported / incomplete)
#             2 usage · 128+N interrupted by signal N, after the unfinished
#             reservation was removed.

set -eu

PROG=$(basename -- "$0")
REPO_DIR=$( (CDPATH= cd -P -- "$(dirname -- "$0")" && pwd -P) || : )
if [ -z "$REPO_DIR" ]; then
  printf 'REFUSED: cannot resolve the directory of %s\n' "$0" >&2
  exit 1
fi
SKILLS_SRC="${REPO_DIR}/skills"
# The copier. It is part of this checkout, not an installed dependency.
COPIER="${REPO_DIR}/scripts/install_packages.py"
PYTHON=''

PKG_NAME=obsidian-skills
PKG_VERSION=0.1.0
PKG_STATUS=unreleased
PKG_ORG=Xia-Ataraxia
PKG_SLUG="${PKG_ORG}/${PKG_NAME}"
PKG_LICENSE=MIT

# The nine packages this release declares. A name outside this list is refused.
PACKAGE_SKILLS='obsidian-markdown obsidian-bases obsidian-canvas obsidian-mermaid obsidian-visualize obsidian-cli obsidian-clipper obsidian-doctor obsidian-sync'

KNOWN_RUNTIMES='claude codex gjc grok hermes cursor agent-skills'

# ── output ────────────────────────────────────────────────────────────────────

say()     { printf '%s\n' "$*"; }
blank()   { printf '\n'; }
title()   { printf '\n== %s ==\n\n' "$1"; }
kv()      { printf '  %-22s %s\n' "$1" "$2"; }
cmdline() { printf '      %s\n' "$*"; }
note()    { printf '  note: %s\n' "$*"; }
refuse()  { printf 'REFUSED: %s\n' "$*" >&2; exit 1; }
usage_err() {
  printf 'USAGE ERROR: %s\n' "$*" >&2
  printf "Run './%s --help' for usage.\n" "$PROG" >&2
  exit 2
}

# ── route table ───────────────────────────────────────────────────────────────
#
# R_KIND is what the runtime actually offers for this package:
#   plugin-marketplace  native plugin/marketplace route that consumes a manifest
#                       shipped in this repository
#   registry-tap        native per-skill registry route, no plugin manifest
#   skill-directory     no self-serve native plugin route; the Agent Skills
#                       directory import is the only route
#
# R_MANIFEST names the file in this repository that backs the native route, or
# '-' when no file here backs it. A directory import is never called a plugin
# install.
#
# R_DOC is the published reference. R_EVIDENCE records how the route was
# confirmed. A runtime with no published reference says so instead of borrowing
# somebody else's URL.
#
# R_USER_REL and R_PROJ_REL are the route *below the approved anchor* — $HOME for
# user scope, --project-root for project scope. Both scopes are therefore an
# anchor plus a relative route, which is what the path-escape gates police.
# R_USER_DIR is the display form and is never used to build a write path.

route_load() {
  R_ID=$1
  R_LABEL=''; R_KIND=''; R_MANIFEST='-'
  R_USER_REL=''; R_USER_DIR=''; R_PROJ_REL=''
  R_DOC=''; R_EVIDENCE=''; R_NOTE=''
  case "$R_ID" in
    claude)
      R_LABEL='Claude Code'
      R_KIND='plugin-marketplace'
      R_MANIFEST='.claude-plugin/marketplace.json + .claude-plugin/plugin.json'
      R_USER_REL='.claude/skills'
      R_PROJ_REL='.claude/skills'
      R_DOC='https://code.claude.com/docs/en/plugins/create-marketplace'
      R_EVIDENCE='published doc, plus observed help of "claude plugin marketplace add" (source: URL, path or GitHub repo) and "claude plugin install" (plugin@marketplace, --scope user|project|local)'
      R_NOTE='the marketplace root is this repository root, so skills/ is auto-discovered from the plugin standard layout'
      ;;
    codex)
      R_LABEL='Codex / ChatGPT desktop app'
      R_KIND='plugin-marketplace'
      R_MANIFEST='.agents/plugins/marketplace.json + .codex-plugin/plugin.json'
      R_USER_REL='.agents/skills'
      R_PROJ_REL='.agents/skills'
      R_DOC='https://developers.openai.com/plugins/build/plugins'
      R_EVIDENCE='published doc names $REPO_ROOT/.agents/plugins/marketplace.json as the repo marketplace and .codex-plugin/plugin.json as the supported compatibility manifest; observed help of "codex plugin marketplace add" and "codex plugin add"'
      R_NOTE='the same doc names the ChatGPT desktop app Plugins Directory as the install surface for a local or repo marketplace; restart the app after adding one'
      ;;
    gjc)
      R_LABEL='GJC (Gajae Code)'
      R_KIND='plugin-marketplace'
      R_MANIFEST='.claude-plugin/marketplace.json'
      R_USER_REL='.gjc/agent/skills'
      R_PROJ_REL='.gjc/skills'
      R_DOC='installed CLI help: gjc plugin --help'
      R_EVIDENCE='observed on gjc v0.18.0: "gjc plugin" actions include install and marketplace, with --scope user|project; the binary resolves .claude-plugin/marketplace.json, ~/.gjc/agent/skills and .gjc/skills. No public documentation URL is published, so none is claimed here'
      R_NOTE='GJC reads the Claude-compatible marketplace manifest; an installed package is advertised as <plugin>:<skill>'
      ;;
    grok)
      R_LABEL='Grok Build'
      R_KIND='plugin-marketplace'
      R_MANIFEST='.claude-plugin/marketplace.json (documented Claude Code compatibility)'
      R_USER_REL='.grok/skills'
      R_PROJ_REL='.grok/skills'
      R_DOC='https://docs.x.ai/build/features/skills-plugins-marketplaces'
      R_EVIDENCE='published doc states Grok automatically reads Claude Code marketplaces, plugins and skills with zero configuration, discovers skills from ~/.grok/skills, ./.grok/skills and ~/.agents/skills, and installs marketplace plugins under ~/.grok/plugins/marketplaces/; observed help of "grok plugin marketplace add" and "grok plugin install"'
      R_NOTE='no Grok-specific manifest exists; after adding the source you browse and install it from the TUI Marketplace tab'
      ;;
    hermes)
      R_LABEL='Hermes Agent'
      R_KIND='registry-tap'
      R_MANIFEST='-'
      R_USER_REL='.hermes/skills'
      R_PROJ_REL='.hermes/skills'
      R_DOC='https://hermes-agent.nousresearch.com/docs/user-guide/features/skills'
      R_EVIDENCE='published doc documents "hermes skills tap add <owner/repo>" (default tap path skills/), per-skill install, and ~/.hermes/skills as the source of truth; observed help of "hermes skills tap add" and "hermes skills install"'
      R_NOTE='one install unit per skill, never a bundle; repo-local project skills load only after "hermes skills trust"'
      ;;
    cursor)
      R_LABEL='Cursor'
      R_KIND='skill-directory'
      R_MANIFEST='-'
      R_USER_REL='.cursor/skills'
      R_PROJ_REL='.cursor/skills'
      R_DOC='https://cursor.com/docs/skills'
      R_EVIDENCE='https://cursor.com/docs/plugins documents the Cursor Marketplace as review-and-submission only and team marketplaces as Teams/Enterprise dashboard features; an Agent Plugin additionally needs a root plugin.json, which this package does not ship. https://cursor.com/docs/skills documents the skill directories this script writes to'
      R_NOTE='Cursor also loads ~/.agents/skills, .agents/skills, and for compatibility .claude/skills and .codex/skills'
      ;;
    agent-skills)
      R_LABEL='Agent Skills (vendor-neutral)'
      R_KIND='skill-directory'
      R_MANIFEST='-'
      R_USER_REL='.agents/skills'
      R_PROJ_REL='.agents/skills'
      R_DOC='https://agentskills.io/specification'
      R_EVIDENCE='the specification defines the SKILL.md package format, naming rules and optional directories only; it defines no install, plugin or marketplace route'
      R_NOTE='Codex, Cursor and Grok all read ~/.agents/skills, so this scope is the portable user-level import'
      ;;
    *)
      return 1
      ;;
  esac
  R_USER_DIR="${HOME:-~}/${R_USER_REL}"
  return 0
}

require_runtime() {
  [ -n "${1:-}" ] || usage_err 'a runtime is required: --runtime <id>'
  route_load "$1" \
    || refuse "unknown runtime '$1'. Known: ${KNOWN_RUNTIMES}. No route is guessed."
}

# ── validation ────────────────────────────────────────────────────────────────

is_declared_skill() {
  for _known in $PACKAGE_SKILLS; do
    if [ "$_known" = "$1" ]; then
      return 0
    fi
  done
  return 1
}

# First path-escape gate: a skill name must be one Agent Skills-legal path
# segment — no '/', no '..', no absolute, hidden or traversing form. The rules
# match https://agentskills.io/specification: 1-64 characters, lowercase
# alphanumerics and hyphens, no leading, trailing or consecutive hyphen.
is_safe_segment() {
  case "$1" in
    ''|.|..)      return 1 ;;
    */*|*\\*)     return 1 ;;
    -*|*-)        return 1 ;;
    *--*)         return 1 ;;
    *[!a-z0-9-]*) return 1 ;;
  esac
  [ "$(printf '%s' "$1" | wc -c)" -le 64 ] || return 1
  return 0
}

# ── the copier ────────────────────────────────────────────────────────────────

# 'copy' needs python3, because every destination write is anchored to a
# directory handle and POSIX sh cannot hold one. A missing interpreter or a
# missing copier is refused rather than worked around: the only workaround would
# be the unanchored path-string copy this replaced, which is the defect.
require_copier() {
  [ -f "$COPIER" ] \
    || refuse "the package copier is missing: ${COPIER}. This checkout is incomplete, so 'copy' cannot run."
  PYTHON=$(command -v python3) || PYTHON=''
  [ -n "$PYTHON" ] \
    || refuse "'copy' needs python3 (3.8 or newer, standard library only) on PATH to anchor every write to a directory handle, and none was found. Install Python 3, or use the native route from './${PROG} native --runtime ${R_ID}'. There is no unanchored fallback."
}

# Runs the copier as a job of this shell and waits for it.
#
# The wait is deliberate. A caught signal interrupts `wait`, so INT or TERM is
# acted on the moment it arrives: it is forwarded to the copier, which rolls back
# its own unfinished reservation, and this script then exits non-zero. A handler
# that merely cleaned up and returned would let an interrupted run carry on
# copying and still report success.
run_copier() {
  _c_status=0
  "$@" &
  _c_pid=$!
  # A failing `kill` means the copier already exited, which is not an error here.
  trap 'kill -TERM "$_c_pid" 2>/dev/null || :; wait "$_c_pid" || :; trap - INT TERM; exit 143' TERM
  trap 'kill -INT "$_c_pid" 2>/dev/null || :; wait "$_c_pid" || :; trap - INT TERM; exit 130' INT
  wait "$_c_pid" || _c_status=$?
  trap - INT TERM
  return "$_c_status"
}

# ── command: routes ───────────────────────────────────────────────────────────

cmd_routes() {
  title "Confirmed routes — ${PKG_NAME} ${PKG_VERSION} (${PKG_STATUS})"
  for _rt in $KNOWN_RUNTIMES; do
    route_load "$_rt"
    printf '  %s  (%s)\n' "$R_ID" "$R_LABEL"
    kv 'route kind' "$R_KIND"
    kv 'manifest in this repo' "$R_MANIFEST"
    kv 'user skill dir' "$R_USER_DIR"
    kv 'project skill dir' "<project-root>/${R_PROJ_REL}"
    kv 'reference' "$R_DOC"
    kv 'confirmed by' "$R_EVIDENCE"
    if [ -n "$R_NOTE" ]; then note "$R_NOTE"; fi
    blank
  done
  say '  Route kinds'
  say '    plugin-marketplace  native plugin install, backed by a manifest shipped here'
  say '    registry-tap        native per-skill registry install, no plugin manifest'
  say '    skill-directory     no self-serve native plugin route; the Agent Skills'
  say '                        directory import is the only route'
  blank
  say "  ${PKG_NAME} ${PKG_VERSION} is ${PKG_STATUS}: nothing is published to a public"
  say '  plugin directory, and no runtime lists it. A native route therefore needs'
  say "  either a published repository or a local path to this checkout — run"
  say "  './${PROG} native --runtime <id>' for the exact commands."
  blank
  say '  A runtime outside this table has no resolved route and is refused, not guessed.'
  blank
}

# ── command: skills ───────────────────────────────────────────────────────────

cmd_skills() {
  title "Declared packages — ${PKG_NAME} ${PKG_VERSION} (${PKG_LICENSE}, ${PKG_ORG})"
  _present=0
  _total=0
  for _s in $PACKAGE_SKILLS; do
    _total=$((_total + 1))
    if [ -f "${SKILLS_SRC}/${_s}/SKILL.md" ]; then
      printf '  [present] %s\n' "$_s"
      _present=$((_present + 1))
    elif [ -e "${SKILLS_SRC}/${_s}" ] || [ -L "${SKILLS_SRC}/${_s}" ]; then
      printf '  [BROKEN ] %s  (present without SKILL.md)\n' "$_s"
    else
      printf '  [absent ] %s\n' "$_s"
    fi
  done
  blank
  say "  ${_present} of ${_total} declared packages are installable from this checkout."
  say '  Each package stands alone: no router, no dispatcher, no shared runtime.'
  blank
}

# ── command: native ───────────────────────────────────────────────────────────

cmd_native() {
  require_runtime "${OPT_RUNTIME:-}"
  title "Native route — ${R_LABEL}"
  kv 'route kind' "$R_KIND"
  kv 'manifest in this repo' "$R_MANIFEST"
  kv 'reference' "$R_DOC"
  kv 'confirmed by' "$R_EVIDENCE"
  if [ -n "$R_NOTE" ]; then note "$R_NOTE"; fi
  blank

  case "$R_KIND" in
    plugin-marketplace)
      say '  Run these yourself; this script executes nothing and reaches no network.'
      blank
      case "$R_ID" in
        claude)
          say '    1. register the marketplace, from the published repository'
          cmdline "claude plugin marketplace add ${PKG_SLUG}"
          say "       or, while ${PKG_VERSION} is ${PKG_STATUS}, from this checkout"
          cmdline "claude plugin marketplace add ${REPO_DIR}"
          say '    2. install the plugin, as <entry-name>@<marketplace-name>'
          cmdline "claude plugin install ${PKG_NAME}@${PKG_NAME}"
          blank
          note 'in a session the same two steps are /plugin marketplace add and /plugin install'
          note 'claude plugin install takes --scope user|project|local; user is its default'
          ;;
        codex)
          say '    1. register the marketplace, from the published repository'
          cmdline "codex plugin marketplace add ${PKG_SLUG}"
          say "       or, while ${PKG_VERSION} is ${PKG_STATUS}, from this checkout"
          cmdline "codex plugin marketplace add ${REPO_DIR}"
          say '    2. install the plugin, as <plugin>@<marketplace>'
          cmdline "codex plugin add ${PKG_NAME}@${PKG_NAME}"
          blank
          note 'OpenAI documents the ChatGPT desktop app Plugins Directory as the install and test surface for a local or repo marketplace; restart the app after step 1'
          ;;
        gjc)
          say '    1. register the marketplace'
          cmdline "gjc plugin marketplace add ${PKG_SLUG}"
          say '    2. install the plugin, as <name>@<marketplace>'
          cmdline "gjc plugin install ${PKG_NAME}@${PKG_NAME} --scope user"
          blank
          note 'swap --scope user for --scope project to install into the current project'
          note "installed packages are advertised as ${PKG_NAME}:<name>"
          note 'gjc plugin --help documents <source> for marketplace add without naming the accepted forms, so no local-path form is claimed here'
          ;;
        grok)
          say '    1. register the marketplace source'
          cmdline "grok plugin marketplace add ${PKG_SLUG}"
          say "       or, while ${PKG_VERSION} is ${PKG_STATUS}, from this checkout"
          cmdline "grok plugin marketplace add ${REPO_DIR}"
          say '    2. install it from the TUI Marketplace tab; grok plugin marketplace'
          say '       list shows the source and the plugins it exposes'
          blank
          say '    Direct install, without registering a marketplace:'
          cmdline "grok plugin install ${PKG_SLUG}"
          blank
          note 'this is the documented Claude Code compatibility path, not a Grok-specific manifest'
          note 'grok plugin install takes a git URL, GitHub shorthand or local path, never a plugin@marketplace id'
          ;;
      esac
      ;;
    registry-tap)
      say '  This runtime reads no plugin manifest from this repository. Its native'
      say '  route is a per-skill registry install. Run these yourself; this script'
      say '  executes nothing and reaches no network.'
      blank
      say '    1. subscribe to the repository as a skill source'
      cmdline "hermes skills tap add ${PKG_SLUG}"
      say '    2. install one package at a time, by tap identifier'
      cmdline "hermes skills install ${PKG_SLUG}/<name>"
      say '    3. refresh installed packages later'
      cmdline 'hermes skills update'
      blank
      say '    Direct install of one package, without adding the tap — the identifier'
      say '    then carries the in-repo path:'
      cmdline "hermes skills install ${PKG_SLUG}/skills/<name>"
      blank
      note "substitute <name> with one of the nine packages; './${PROG} skills' lists them"
      note 'a tap defaults to the repository skills/ directory, which is where these packages live'
      note 'repo-local project skills load only after "hermes skills trust"'
      ;;
    skill-directory)
      say "  UNSUPPORTED: ${R_LABEL} offers no self-serve native plugin or marketplace"
      say "  route for this package. Copying into its Agent Skills directory is a"
      say '  generic import, not a native plugin install, and this script will not'
      say '  present it as one.'
      blank
      say '  Supported route for this runtime:'
      cmdline "./${PROG} copy --runtime ${R_ID} --skill all --scope user"
      ;;
  esac

  blank
  say '  The Agent Skills directory import is available for every runtime in the table:'
  cmdline "./${PROG} copy --runtime ${R_ID} --skill <name>|all --scope user|project"
  blank
  say "  Route confirmed is not install verified. Nothing above has been executed, and"
  say '  no runtime has loaded this package as a result of running this script.'
  blank
}

# ── command: copy ─────────────────────────────────────────────────────────────

collect_selection() {
  SELECTED=''
  _want_all=no
  _want_named=no
  for _sel in $OPT_SKILLS; do
    if [ "$_sel" = all ]; then
      _want_all=yes
    else
      _want_named=yes
    fi
  done
  if [ "$_want_all" = yes ] && [ "$_want_named" = yes ]; then
    usage_err "--skill all cannot be combined with named packages; choose one form"
  fi
  if [ "$_want_all" = yes ]; then
    SELECTED=$PACKAGE_SKILLS
    return 0
  fi
  for _sel in $OPT_SKILLS; do
    is_safe_segment "$_sel" \
      || refuse "illegal skill name '${_sel}': not a single lowercase Agent Skills path segment."
    is_declared_skill "$_sel" \
      || refuse "'${_sel}' is not one of the nine packages declared by ${PKG_NAME} ${PKG_VERSION}."
    _dup=no
    for _seen in $SELECTED; do
      if [ "$_seen" = "$_sel" ]; then _dup=yes; fi
    done
    if [ "$_dup" = no ]; then
      SELECTED="${SELECTED}${SELECTED:+ }${_sel}"
    fi
  done
  [ -n "$SELECTED" ] \
    || usage_err 'the skill selection resolved to nothing; pass --skill <name> or --skill all'
}

cmd_copy() {
  require_runtime "${OPT_RUNTIME:-}"
  [ -n "$OPT_SKILLS" ] || usage_err 'a skill selection is required: --skill <name> (repeatable) or --skill all'
  [ -n "$OPT_SCOPE" ]  || usage_err 'a scope is required: --scope user|project'
  collect_selection

  # The anchor is the only directory the user authorised to be written under,
  # and the route is what may be created below it. Both are handed to the copier
  # exactly as they were named. The copier resolves them once, against directory
  # handles it then keeps open, so no later check or write is built from a path
  # string that could mean something different by the time it is used.
  case "$OPT_SCOPE" in
    user)
      [ -n "$R_USER_REL" ] || refuse "no user skill directory is confirmed for runtime '${R_ID}'."
      _anchor=${HOME:-}
      _anchor_kind=home
      _route=$R_USER_REL
      ;;
    project)
      _anchor=$PROJECT_ROOT
      _anchor_kind=project
      _route=$R_PROJ_REL
      ;;
    *)
      usage_err "scope must be 'user' or 'project' (got '${OPT_SCOPE}')"
      ;;
  esac

  _copy_mode=plan
  if [ "$OPT_APPLY" = yes ]; then _copy_mode=apply; fi

  require_copier

  _copy_status=0
  # SELECTED holds already-validated single path segments, so splitting it into
  # separate arguments is exactly what is wanted here.
  # shellcheck disable=SC2086
  run_copier "$PYTHON" "$COPIER" \
    --repo "$REPO_DIR" \
    --source "$SKILLS_SRC" \
    --anchor "$_anchor" \
    --anchor-kind "$_anchor_kind" \
    --route "$_route" \
    --scope "$OPT_SCOPE" \
    --runtime "$R_ID" \
    --label "$R_LABEL" \
    --kind "$R_KIND" \
    --prog "$PROG" \
    --package "$PKG_NAME" \
    --mode "$_copy_mode" \
    -- $SELECTED || _copy_status=$?
  exit "$_copy_status"
}

# ── help ──────────────────────────────────────────────────────────────────────

cmd_help() {
  cat <<EOF
${PKG_NAME} ${PKG_VERSION} (${PKG_STATUS}) — ${PKG_ORG} — ${PKG_LICENSE}
Nine Obsidian Agent Skills. No router, no dispatcher: each package stands alone.

USAGE
  ./${PROG} <command> [options]

COMMANDS
  routes                     Print every runtime's confirmed route, the manifest
                             that backs it, its skill directories, its published
                             reference and the evidence it was confirmed from.
  skills                     List the nine declared packages and whether each is
                             present in this checkout.
  native  --runtime <id>     Print the native install commands for one runtime.
                             Nothing is executed. A runtime without a self-serve
                             native plugin route is reported as unsupported.
  copy    --runtime <id> --skill <name>|all --scope user|project [--apply]
                             Copy complete skill packages into that runtime's
                             confirmed Agent Skills directory.

OPTIONS
  --runtime <id>             One of: ${KNOWN_RUNTIMES}. Give it once.
  --skill <name>             Repeatable. Or 'all' for the nine declared packages.
                             'all' and named packages cannot be mixed.
  --scope user|project       Required for 'copy'. No default is assumed.
  --project-root <path>      Consumer project for --scope project. Default: \$PWD.
                             Rejected with --scope user.
  --apply                    Perform the copy. Without it, 'copy' is a dry run.
  --dry-run                  Explicit form of the default. Conflicts with --apply.
  -h, --help                 This text.

BEHAVIOUR
  * Dry run is the default. Writing requires --apply, and --apply with --dry-run
    is a usage error rather than a silent winner.
  * Runtime, selection and scope are each exact. A repeated --runtime or --scope
    with a different value, an unknown runtime, an undeclared package name, an
    option given an empty value, or an empty selection is refused instead of
    resolved. --project-root '' is a usage error, never a silent "here".
  * Every selected package is pre-flighted first. Any existing file, directory,
    symlink or dangling symlink at a destination refuses the whole operation, and
    nothing is written. A package whose source in this checkout is itself a
    symlink is refused too, rather than copied through.
  * 'copy' runs its filesystem work through scripts/install_packages.py under
    python3 (3.8 or newer, standard library only). Without python3 it refuses:
    anchoring each write to a directory handle is the whole point, and an
    unanchored fallback would reintroduce the defect it exists to prevent.
    Everything else here -- routes, skills, native, help -- is plain POSIX sh.
  * Writing is anchored. The approved root is your HOME for --scope user and the
    --project-root directory for --scope project, and the route below it is
    opened one component at a time, each through a handle on the component just
    opened. A symlink on that route is refused by the open that would otherwise
    have followed it, whether or not it currently points inside, and the link and
    its target are left exactly as they are. A component that is not a directory
    is refused. Missing components are created relative to the handle of their
    parent, one at a time, never with mkdir -p, so a component swapped for a link
    after the check cannot redirect the next create.
  * A skill name must be one lowercase Agent Skills path segment. The destination
    root must be reachable from the approved root through that handle walk, and
    its real parent chain must reach the approved root without passing through
    this checkout. Containment is decided from filesystem object identity, not
    from comparing path strings. Anything else is a path escape, and there is no
    fallback.
  * Packages are built and verified in private staging, then published with an
    atomic no-replace rename (macOS or Linux). A destination appearing after
    pre-flight is left untouched. Missing platform support refuses publication,
    with no unsafe fallback. Failed publication leaves named staging for recovery.
  * Each copied package is read back against its source by content: identical
    paths and types, every regular file byte-identical, and SKILL.md present.
    Source symlinks are refused. A failed readback removes exactly the
    entries this run recorded creating and exits non-zero; packages already
    verified are kept and named. A destination that is no longer this run's own
    reservation, or one somebody has added content to, is reported and left as it
    is -- it is never recursively deleted.
  * Generated caches (__pycache__, *.pyc, *.pyo, .pytest_cache, .mypy_cache,
    .ruff_cache, .DS_Store) are build residue, so they are never copied at all.
    Finding one in a destination is a readback failure rather than an exclusion,
    and your checkout is never modified.
  * INT or TERM stops the run where it is. The unfinished reservation is rolled
    back and the exit status is 128 plus the signal number; an interrupted copy
    never reports success.
  * An unknown runtime is refused. No route is inferred, and a directory import
    is never presented as a native plugin install.
  * The script never reaches the network, never runs a runtime CLI, and never
    reads or writes a profile, settings file, marketplace registry, tap list or
    plugin cache. It only creates the destination root and copies package
    directories. No temporary file is used anywhere.

EXAMPLES
  ./${PROG} routes
  ./${PROG} skills
  ./${PROG} native --runtime claude
  ./${PROG} copy --runtime grok --skill obsidian-markdown --scope user
  ./${PROG} copy --runtime cursor --skill all --scope project --project-root ~/work/notes --apply
EOF
}

# ── dispatch ──────────────────────────────────────────────────────────────────

OPT_RUNTIME=''
OPT_SKILLS=''
OPT_SCOPE=''
OPT_APPLY=''
OPT_PROJECT_ROOT=''
# Presence is tracked apart from the value: an option that was given is given,
# even if what followed it was empty.
OPT_PROJECT_ROOT_SET=no
PROJECT_ROOT="$PWD"

if [ "$#" -eq 0 ]; then
  cmd_help
  exit 0
fi

case "$1" in
  routes|skills|native|copy) COMMAND=$1; shift ;;
  -h|--help|help)            cmd_help; exit 0 ;;
  -*)                        usage_err "expected a command before options (got '$1')" ;;
  *)                         usage_err "unknown command '$1'" ;;
esac

# An option that names one exact thing may not be given twice with two different
# values. Silently letting the last one win would make the selected runtime,
# scope or project root depend on argument order.
reject_reset() {
  # $1 option name, $2 current value, $3 new value
  if [ -n "$2" ] && [ "$2" != "$3" ]; then
    usage_err "$1 was given twice with different values ('$2' then '$3')"
  fi
}

# An option that was given but left empty names nothing. Reading '' as "not
# given" would quietly substitute a default the user never asked for, which is
# how '--project-root ""' used to resolve to the current directory and write
# there. Both argument forms are rejected the same way.
require_value() {
  # $1 option name, $2 value
  [ -n "$2" ] || usage_err "$1 was given an empty value; it must name something"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --runtime)        [ "$#" -ge 2 ] || usage_err '--runtime needs a value'
                      require_value --runtime "$2"
                      reject_reset --runtime "$OPT_RUNTIME" "$2"
                      OPT_RUNTIME=$2; shift 2 ;;
    --runtime=*)      require_value --runtime "${1#--runtime=}"
                      reject_reset --runtime "$OPT_RUNTIME" "${1#--runtime=}"
                      OPT_RUNTIME=${1#--runtime=}; shift ;;
    --skill)          [ "$#" -ge 2 ] || usage_err '--skill needs a value'
                      require_value --skill "$2"
                      OPT_SKILLS="${OPT_SKILLS}${OPT_SKILLS:+ }$2"; shift 2 ;;
    --skill=*)        require_value --skill "${1#--skill=}"
                      OPT_SKILLS="${OPT_SKILLS}${OPT_SKILLS:+ }${1#--skill=}"; shift ;;
    --scope)          [ "$#" -ge 2 ] || usage_err '--scope needs a value'
                      require_value --scope "$2"
                      reject_reset --scope "$OPT_SCOPE" "$2"
                      OPT_SCOPE=$2; shift 2 ;;
    --scope=*)        require_value --scope "${1#--scope=}"
                      reject_reset --scope "$OPT_SCOPE" "${1#--scope=}"
                      OPT_SCOPE=${1#--scope=}; shift ;;
    --project-root)   [ "$#" -ge 2 ] || usage_err '--project-root needs a value'
                      require_value --project-root "$2"
                      reject_reset --project-root "$OPT_PROJECT_ROOT" "$2"
                      OPT_PROJECT_ROOT=$2; OPT_PROJECT_ROOT_SET=yes; shift 2 ;;
    --project-root=*) require_value --project-root "${1#--project-root=}"
                      reject_reset --project-root "$OPT_PROJECT_ROOT" "${1#--project-root=}"
                      OPT_PROJECT_ROOT=${1#--project-root=}; OPT_PROJECT_ROOT_SET=yes; shift ;;
    --apply)          [ "$OPT_APPLY" != no ] || usage_err '--apply conflicts with --dry-run'
                      OPT_APPLY=yes; shift ;;
    --dry-run)        [ "$OPT_APPLY" != yes ] || usage_err '--dry-run conflicts with --apply'
                      OPT_APPLY=no; shift ;;
    -h|--help)        cmd_help; exit 0 ;;
    *)                usage_err "unknown option '$1' for command '${COMMAND}'" ;;
  esac
done

[ -n "$OPT_APPLY" ] || OPT_APPLY=no

case "$COMMAND" in
  routes|skills)
    if [ -n "${OPT_RUNTIME}${OPT_SKILLS}${OPT_SCOPE}" ] || [ "$OPT_PROJECT_ROOT_SET" = yes ]; then
      usage_err "'${COMMAND}' takes no options"
    fi
    [ "$OPT_APPLY" = no ] || usage_err "'${COMMAND}' never writes anything, so --apply is meaningless"
    if [ "$COMMAND" = routes ]; then cmd_routes; else cmd_skills; fi
    ;;
  native)
    [ -z "$OPT_SKILLS" ] || usage_err "'native' does not take --skill; use 'copy'"
    [ -z "$OPT_SCOPE" ] || usage_err "'native' does not take --scope; use 'copy'"
    [ "$OPT_PROJECT_ROOT_SET" = no ] || usage_err "'native' does not take --project-root; use 'copy'"
    [ "$OPT_APPLY" = no ] || usage_err "'native' never executes anything, so --apply is meaningless"
    cmd_native
    ;;
  copy)
    if [ "$OPT_PROJECT_ROOT_SET" = yes ]; then
      [ "$OPT_SCOPE" = project ] \
        || usage_err "--project-root applies to --scope project only (scope is '${OPT_SCOPE:-unset}')"
      PROJECT_ROOT=$OPT_PROJECT_ROOT
    fi
    cmd_copy
    ;;
esac
