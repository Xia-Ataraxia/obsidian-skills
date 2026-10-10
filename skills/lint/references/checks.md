# Lint one-liners

Starting points, not a pipeline. Replace `<scope>`, `<vault>` and `<mothership>` with live paths. Prefer `obsidian-cli` for link questions when Obsidian is running; it resolves aliases and headings that `rg` cannot.

```bash
# Inventory
rg --files -g '*.md' <scope> | wc -l

# Link targets used in scope (strip alias and heading)
rg -o --no-filename '\[\[[^]|#]+' <scope> | sort -u

# Does a target exist anywhere in the vault
rg --files -g '<name>.md' <vault>

# Inbound links to one page from the whole vault
rg -l "\[\[<basename>(\||#|\]\])" <vault>

# Contradiction callouts
rg -n '> \[!warning\] Contradiction' <scope>

# Field presence: lists notes lacking the field
rg -L '^purpose:' <raw-scope>
rg -l '^purpose_origin: (inferred|unknown)' <raw-scope>
rg -L '^explored:' <wiki-scope>
rg -L '^## Sources' <wiki-scope>
# Raw-only keys on a Wiki page
rg -l '^(source_identity|source_locator|source_extraction|purpose|purpose_origin|fidelity\w*|user_intent_interview):' <wiki-scope>

# High confidence without a Bias Check
rg -l '^confidence: "?high"?$' <wiki-scope> | xargs rg -L 'Bias Check'

# Confidence outside high, medium, low
rg -n '^confidence:' <wiki-scope> | rg -v 'confidence: "?(high|medium|low)"?$'

# Age of a page
git log -1 --format=%cs -- <page>

# Mothership deeplinks to decode and stat
rg -o --no-filename 'obsidian://open\?vault=[^&]+&file=[^)"\s]+' <scope>
```

Decode the `file` component (percent-decoding) before checking it exists under `<mothership>`, with and without `.md`. Drop matches that sit inside code spans or fenced blocks.

`rg -L` lists files with no match; a field in the body rather than frontmatter will hide a gap, so spot-read a few results.
