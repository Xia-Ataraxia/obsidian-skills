# Agent sessions and topic bundles

## Unit: the topic, not the session

One session is usually thin: a few owner turns that matter, surrounded by tool output. The owner also tends to give several agents related but different jobs on the same subject. So the capture unit is the topic. One candidate holds every selected session that worked on it, and ingest later reads the bundle as one source.

This differs from a multi-platform research bundle, where one question goes to several models and the answers are compared. Here each member had its own task. Record that task; do not line the members up as rival answers to one question.

## Building a bundle

1. The owner names the topic and the sessions, or a bounded way to find them ("today's sessions about the inbox redesign"). Read through an available read-only runtime interface or a selected export. Never sweep every session, schedule exports or archive whole sessions.
2. Give each session one source entry with its stable session id, the agent or runtime and range as `source_locator`, and `role`: the task that session was given, in one line.
3. Choose the mode per member by density:
   - `excerpt` — the default for a working session: the owner's own turns verbatim (questions, decisions, corrections, concerns) and the agent's conclusions, with tool output left out and named as an omission;
   - `transcript` — a short session, or one whose reasoning is itself the point;
   - `manifest-only` — a session that could not be read.
4. Write the candidate at `{topic-slug}` in the agent lane. A later session on the same topic is a new candidate that names the earlier one in its notes; an existing candidate is never rewritten.

## Agent Capture Notes

Fixed items, each grounded in the members above and labelled as the agent's reading:

- the topic in one paragraph;
- a manifest table: session, agent, role, mode;
- what the sessions share — said once, with the members that said it;
- where they differ: different task, different result, or a real disagreement;
- the owner's concerns and decisions, with the member each came from;
- what is missing or unresolved;
- Wiki pages ingest should create or update.

The last item is the handoff: ingest starts its analysis from that list.

## Limits

A runtime report, a transcript and a machine ledger are different records. A report's Attempt/Why/Result sections do not prove a transcript was acquired. A truncated span is partial. Never fill missing messages from a summary; reconstruction is Agent Capture Notes, never original text.

A line range in an export is not a turn range unless the exporter says so. Say the runtime was queried only when a real tool queried it.
