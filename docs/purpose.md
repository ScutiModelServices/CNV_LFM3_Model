# Purpose

**Kind:** chat messages → text (conversation, small)

**Group:** Conversation

**Tags:** `cpu`, `streaming`, `host-threads`, `variants`

| | |
|---|---|
| Input | Chat messages, temperature and maximum tokens. |
| Output | JSON content, finish reason and usage; NDJSON streaming available. |
| Runs on | CPU API; inference runs on the external Ollama host with LFM3-1.7B GGUF. The Model variant card lists the quantizations (`Q4_K_M` to `F16`) with an estimate of the memory each takes and whether this machine can run it. API memory has not been measured. |

**Use for:** everyday conversation through one shared Ollama model.
**Not for:** project checkpoint selection, schemas or per-request thinking (422).
