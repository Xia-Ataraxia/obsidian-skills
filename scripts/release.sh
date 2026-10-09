#!/bin/sh
# Lock-step release: set one version on every SKILL.md and plugin.json, tag, publish.
set -eu
v=${1:?usage: scripts/release.sh <version>}
cd "$(git rev-parse --show-toplevel)"
[ "$(git branch --show-current)" = main ] || { echo "release from main only" >&2; exit 1; }
git diff --quiet HEAD || { echo "working tree not clean" >&2; exit 1; }
perl -pi -e "s/^(  version: )\".*\"/\$1\"$v\"/" skills/*/SKILL.md
perl -pi -e "s/^(  \"version\": )\".*\"/\$1\"$v\"/" .claude-plugin/plugin.json
git commit -qam "release: $v"
git tag "$v"
git push origin main "$v"
gh release create "$v" --prerelease --generate-notes --title "$v"
