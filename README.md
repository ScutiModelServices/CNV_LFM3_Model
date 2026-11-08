# CNV_LFM3_Model

LFM3-1.7B chat over HTTP through Ollama, port 29202. Callers share one Ollama model through API replicas, with admin settings, tokens, rate limits, metrics, streaming and answer caches. No tool service is required.

## API

| Call | Purpose |
|---|---|
| `POST /v1/chat` | `messages`, optional `temperature`, `max_tokens`, `stream`; returns `content`, `finish_reason`, `model`, `fallback` (always false), `usage`, `duration_ms`. |
| `GET /health` | `status`, `model`, `ready`, `num_thread`; no token required. |

**Input.** One to 64 messages with roles `system`, `user`, or `assistant`, each at most 100,000 characters. Temperature is 0 to 2 (default 0); maximum tokens is 1 to 4096 (default 512). Unknown fields, including `project`, `tools`, `schema` and `thinking`, return 422. Thinking is controlled through admin settings.

**Result.** JSON with answer text, finish reason, selected Ollama model and token usage. An unavailable Ollama or missing model returns 503 with a hint to start Ollama and pull the model. The API and admin page remain available during failed warm-up.

**Streaming.** `stream: true` returns NDJSON `content` lines followed by `done` with the ordinary response body. Errors before the first piece are HTTP errors; later errors are `error` lines. Hide reasoning is on by default, so content is held until completion and text through the last `</think>` is dropped.

**Cache.** Only temperature 0 answers are kept, per replica, with `X-Cache: hit|miss`. The cache key includes model generation, messages, maximum tokens and reasoning settings. Download invalidates answers across replicas. Streamed and plain requests share answers.

**Tokens.** With `SERVICE_ADMIN_PASSWORD` set, public calls require `X-Internal-Token`. Tokens support expiry, rate limits and revocation. Token project restrictions are removed: lists return 422; omitted or null `projects` stays compatible with the shared editor. Legacy stored scopes are hidden from the listing.

## Admin page

Open `/admin/` with `SERVICE_ADMIN_PASSWORD`. Tokens, usage, replicas, Settings and Updates share the standard model-service page. CPU thread values are saved and reported only; Ollama chooses its own threads. Settings retain update-check hours, in-flight cap, answer cache size, thinking, hide reasoning and warm-up. The model name is the startup value `SERVICE_OLLAMA_MODEL`.

Updates checks the installed Ollama digest without downloading; **Download new weights** runs an Ollama pull. A marker in the shared data volume tells replicas to discard old adapters and cached answers. This digest check does not discover newer remote manifests before a pull. Download remains available after a successful check and always pulls, even when the installed digest is unchanged.

## Run

Start Ollama and pull the model first:

```bash
ollama pull hf.co/LiquidAI/LFM3-1.7B-GGUF:Q4_K_M
```

```bash
docker compose up -d --build
```

Docker defaults to `http://host.docker.internal:11434`. A local run defaults to `http://127.0.0.1:11434` when `SERVICE_OLLAMA_URL` is unset. An explicitly empty URL is an error. Without Docker use `run.bat run` with a running Ollama; when copying `.env.example`, change the Docker URL to the local one.

```bash
curl -X POST http://127.0.0.1:29202/v1/chat -H "Content-Type: application/json" -H "X-Internal-Token: lfm3_..." -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

## Tests

```bash
uv run pytest
```

Browser tests need Playwright and Chromium. Docker builds and real Ollama inference have not been verified for this migration.

## Limits worth knowing

- One generation per API replica; excess waiting calls return 429 with `Retry-After: 5`.
- Rate limits are per replica. Ollama owns model memory and scheduling; API replicas share its model.
- Generation network timeout is 120 seconds. Readiness becomes true after a successful model load and false after a failed generation.
- No per-project model selection. Old checkpoint directories are unused; migration and rollback notes are in the changelog.

## Try it from the admin page

Use **Try it** with a public token kept only in memory. Chat takes messages, temperature, maximum tokens and streaming. Status, latency, errors, cancellation and redacted curl appear in the panel. See [web UI guide](docs/guide-web-ui.md#try-it-send-a-real-request).

## Documentation

- [Purpose](docs/purpose.md)
- [Deployment](deployment.md)
- [Changelog](CHANGELOG.md)
- [Admin page](docs/guide-web-ui.md)
- [Docker on this PC](docs/guide-docker-same-device.md)
- [Docker on another machine](docs/guide-docker-deployment-device.md)
- [Without Docker](docs/guide-no-docker-same-device.md)
- [Command-line calls](docs/guide-cli.md)
