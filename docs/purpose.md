# Purpose

**Kind:** chat messages → text (conversation, small)

**Group:** Conversation

**Tags:** `cpu`, `streaming`

| | |
|---|---|
| Input | Chat messages, temperature and maximum tokens. |
| Output | JSON content, finish reason and usage; NDJSON streaming available. |
| Runs on | CPU API; inference runs on the external Ollama host with LFM3-1.7B GGUF. API memory has not been measured. |

**Use for:** everyday conversation through one shared Ollama model.
**Not for:** project checkpoint selection, tool calls, schemas or per-request thinking (422).
