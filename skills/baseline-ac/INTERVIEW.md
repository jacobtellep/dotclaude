# Engineering Context interview

Establish the engineering context a human developer would settle before starting work. Grilling covers what the feature is; this covers how it gets built and shipped.

Run it after grilling converges and before the spec exists.

## Rules

If a fact can be found by exploring the repo — deploy config, CI, infra files, existing error handling, migration tooling — look it up rather than asking.

The decisions are the user's. Ask one item at a time, lead with a recommended answer, and wait for a response before continuing.

## Agenda

Work through these in order. Skip any the conversation has already settled.

1. **Deployment.** How does this deploy? What already exists upstream for retries, failure handling, and rollback? Anything the platform already handles stays out of the code.
2. **Compatibility.** Is backward compatibility actually required, or do old callers just break? Default: old code is deleted and old callers break loudly. Compatibility gets built only when the user requires it here.
3. **Migrations and data.** Any schema or data changes? Is there existing migration tooling to follow? Is a rollback path needed?
4. **Pointing.** How big should this be, in the user's own sizing terms — points, hours, "half a day touching the search module"? Record it verbatim.
5. **Testing proportion.** Which seams get tested (see the `tdd` skill's seam rules), and how much testing is proportionate to the pointed size? A 2-point change does not get a 5-point test suite.

## Output

Write an **Engineering Context** block: one line per agenda item, decisions only, no discussion. Record the pointing verbatim.

Write it to a file, so it survives the context being cleared before the work starts:

- A spec already exists → into the spec, under Implementation Decisions.
- No spec yet → alongside wherever planning artifacts live for this repo. Consult `docs/agents/issue-tracker.md` if present; otherwise `.scratch/<feature>/engineering-context.md`.

State the block in the conversation too, and name the file path you wrote.

Then stop. This branch establishes context and writes it down — it does not write the spec.
