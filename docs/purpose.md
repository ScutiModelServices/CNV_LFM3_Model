# Purpose

**Kind:** chat messages → text (conversation, small)

**Group:** Conversation

**Tags:** `cpu`, `streaming`, `project-models`

| | |
|---|---|
| Input | Chat messages, temperature, max tokens, project. |
| Output | JSON: content, finish reason, usage. Streamable. |
| Runs on | CPU (`transformers`, LFM3-1.7B). |

Same API as BitNet, so callers swap with one config change.

**Use for:** fast everyday replies, A/B comparison against BitNet.
**Not for:** tool calls, schemas, thinking (all return 422).
