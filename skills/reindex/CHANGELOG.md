# Changelog

## 0.2.2 — 2026-10-07

- 2026-10-07 — Collection release `0.2.2`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.
## 0.2.1 — 2026-10-07

- 2026-10-07 — Hermes Agent v0.21.5 `skills_guard` refused community installs of four 0.2.0 packages with a CAUTION verdict; `scripts/reindex.py` copied the process environment to add `PYTHONIOENCODING=utf-8` for qmd, which the guard's HIGH `python_os_environ` rule matches. qmd is a Node CLI, so that variable never affected it. The helper now passes no environment override, decodes qmd stdout as strict UTF-8 regardless of the caller's locale (a non-UTF-8 locale previously crashed on non-ASCII member paths), refuses undecodable stdout as `qmd_output_undecodable`, and decodes stderr readbacks with replacement. `metadata.version` follows the collection release `0.2.1`.
