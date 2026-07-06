---
name: dm
description: >-
  Compose Slack messages in Jake's voice and deliver them the right way:
  client-facing messages become Slack drafts Jake sends himself (avoids the
  platform-enforced "via Claude" badge), internal teammate messages are
  direct-sent after Jake approves the text. Use whenever Jake asks to draft,
  write, send, or reply to a Slack message, DM, thread, or channel update —
  e.g. "message Rudo", "draft a slack update for the client", "reply in that
  thread", "send a status to the ample channel".
when_to_use: >-
  draft a slack message; send a slack message; message <person>; slack update;
  reply to thread; DM someone; client update in slack; status message
argument-hint: recipient and gist (e.g. "Rudo - staging test passed")
user-invocable: true
---

# Drafting Slack Messages

Compose Slack messages in Jake's voice and deliver them through the correct channel for the audience.

## 1. Voice first (mandatory)

Read `~/VOICE.md` before composing anything. It defines the two registers:

- **Internal** (Rudo, Fred, Melissa, other Ample folks): relaxed and brief, NO greeting or salutation — start with the point. Correct capitalization and punctuation. Light emoji okay, sparingly.
- **Client-facing** (the ample-* channels, clients, cross-team partners): polished. Open with a greeting and their name, one-line framing, bullets for status/next steps/blockers, warm close.

Never use em dashes in either register.

## 2. Pick the delivery path by audience

**The one hard rule: NEVER `slack_send_message` to clients or client channels.**
Messages sent through the connector carry a platform-enforced "via Claude" badge that cannot be disabled and undercuts Jake's client register. This is Slack behavior, not a setting.

| Audience | Path | Why |
|---|---|---|
| Client-facing | `slack_send_message_draft` | Draft lands in Jake's composer; he sends as himself — **no badge** (verified 2026-07-02) |
| Internal teammates | `slack_send_message` after Jake approves the text | Badge is acceptable internally |

When the audience is ambiguous (unknown recipient, shared channel with externals), default to the draft path and say so.

## 3. Workflow

1. Compose in the correct register.
2. **Internal**: show the draft in chat for proofreading. Send only after Jake approves — approval of one message does not extend to the next. If replying in a thread, pass `thread_ts` of the parent.
3. **Client-facing**: show the text in chat AND create the Slack draft (`slack_send_message_draft`) in the target channel. Tell Jake it's in his composer to edit and send. Do not "helpfully" fall back to direct send if the draft path fails.
4. Report the `message_link` / `channel_link` from the tool result.

## 4. Mechanics and gotchas

- Find people with `slack_search_users`; for a DM, use the person's `user_id` as `channel_id`. Find channels with `slack_search_channels`.
- Thread replies: `thread_ts` = parent message timestamp (from a prior send's `message_context.message_ts` or `slack_read_thread`).
- **One attached draft per channel.** `draft_already_exists` means Jake has an unsent draft there — ask him to send or discard it in Slack; do not overwrite or reroute.
- Messages support standard markdown; keep formatting light (Jake's messages are prose and simple bullets, not headers/tables).
- Cannot post to externally shared (Slack Connect) channels via the connector.
- If the Slack tools are deferred, load them in ONE ToolSearch call (`select:` accepts a comma-separated list).

## 5. Content bar

Only the important bits, in complete sentences. Lead with the point. If Jake asked for "brief", cut aggressively — a short message that reads well beats a complete one that doesn't. Skip closing filler unless the register calls for a handoff line ("Let me know...") and Jake hasn't asked to drop it.
