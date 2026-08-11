---
name: pre-flight
description: Interview the user about engineering context before writing a spec, covering deployment, compatibility, migrations, pointing, and testing proportion. Run after grilling converges and before /to-spec.
disable-model-invocation: true
---

# Pre-Flight

Establish the engineering context a human developer would settle before starting work.
Grilling covers what the feature is; this covers how it gets built and shipped.

Follow the grilling rules: if a fact can be found by exploring the repo (deploy config, CI, infra files, existing error handling, migration tooling), look it up rather than asking.
The decisions are the user's — ask them one at a time, with a recommended answer for each, and wait for a response before continuing.

## Agenda

Work through these in order. Skip any the conversation has already settled.

1. **Deployment.** How does this deploy? What already exists upstream for retries, failure handling, and rollback? Anything the platform already handles must not be rebuilt in code.
2. **Compatibility.** Is backward compatibility actually required, or do old callers just break? Default: no compatibility work — old code is deleted, old callers break loudly. Compatibility is built only when the user explicitly requires it here.
3. **Migrations and data.** Any schema or data changes? Is there existing migration tooling to follow? Is a rollback path needed?
4. **Pointing.** How big should this be, in the user's own sizing terms (points, hours, "half a day touching the search module")? Record it verbatim; this is the scope anchor everything downstream is measured against.
5. **Testing proportion.** Which seams get tested (see the tdd skill's seam rules), and how much testing is proportionate to the pointed size? A 2-point change does not get a 5-point test suite.

## Output

When the agenda is done, state an **Engineering Context** block into the conversation as a short bulleted summary: one line per agenda item, decisions only, no discussion.
End with: "This context constrains the spec — /to-spec should fold it into Implementation Decisions and Acceptance Criteria."

Do not write any files and do not start the spec. This skill only establishes context.
