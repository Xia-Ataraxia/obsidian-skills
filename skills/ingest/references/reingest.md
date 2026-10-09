# Re-ingest procedure

Select legacy candidates by category, Concept connections and secondary-source relationships. Markers include `source_locator`-only identity, unlinked author strings and an absent `## Ingest Notes`; markers are hints, not proof of corruption. The owner names the batch: N items in one category, default 10. Each item is still one ingest and one commit.

Sameness is `source_identity`, otherwise the canonical `source_url` or `source_locator`; never the title. An item already re-ingested is found by its `Ingest-Source` trailer in `git log`, which is the only record: no manifest or queue field is kept.

An existing Raw body is never rewritten. A better extraction becomes a new Raw whose `referenced` points at the earlier one; existing Wiki pages are updated by the Step 3 rules.

An interrupted run is resumed by reading `git status`: finish the remaining steps for the uncommitted files, or stop and report them. Never reset or check out to clean up.

Pilot one representative per category before a batch. A web-book pilot needs an owner-selected multi-page source with at least five chapters and two directly fetched chapter URLs. A commercial or offline book follows the [books](books.md) file and page locator adaptation. Pilot success does not authorize the full batch.
