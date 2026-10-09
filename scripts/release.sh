#!/bin/sh
# Lock-step release: one version on every SKILL.md and manifest, then tag and publish.
set -eu
V=${1:?usage: scripts/release.sh <version>}; export V
cd "$(git rev-parse --show-toplevel)"
[ "$(git branch --show-current)" = main ] || { echo "release from main only" >&2; exit 1; }
git diff --quiet HEAD || { echo "working tree not clean" >&2; exit 1; }
git fetch -q origin && [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "main is not at origin/main" >&2; exit 1; }
perl -pi -e 's/^(  version: )".*"/$1"$ENV{V}"/' skills/*/SKILL.md
perl -pi -e 's/^(  "version": )".*"/$1"$ENV{V}"/' .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json
grep -L "^  version: \"$V\"" skills/*/SKILL.md | grep . && { echo "packages above have no metadata.version" >&2; exit 1; }
git commit -qam "release: $V"
git tag "$V"
git push --atomic origin main "$V"
gh release create "$V" --prerelease --generate-notes --title "$V"
