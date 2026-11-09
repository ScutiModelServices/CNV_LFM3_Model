# CNV_LFM3_Model

First start: open `/admin/` → **Updates** → **Download**; see [the web UI guide](docs/guide-web-ui.md#updating-the-model-files). Startup and requests load downloaded files only; an empty installation keeps health/admin available and returns 503 for inference.

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

The Updates card compares the downloaded Ollama manifest digest with the online registry manifest at startup, every `update_check_hours` and on **Check now**. Checks fetch metadata only; only **Download** runs `ollama pull`. A successful download invalidates every replica through shared storage; each replica reloads on its next request.

## Run

Start Ollama and the API, then download from `/admin/` → **Updates** → **Download**:

```bash
curl -X POST http://127.0.0.1:29202/admin/updates/weights -H "X-Internal-Token: <ADMIN_PASSWORD>"
```

```bash
docker compose --env-file .env.compose up -d --build
```

Docker defaults to `http://host.docker.internal:11434`. A local run defaults to `http://127.0.0.1:11434` when `SERVICE_OLLAMA_URL` is unset. An explicitly empty URL is an error. Without Docker use `run.bat run` with a running Ollama; copy `.env.example` to `.env.local` and set the local URL there; `.env.compose` (Docker Desktop here) and `.env` (the deployment device) keep the Docker one.

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

## Admin pages and navigation

Open `/admin/` and sign in. Overview opens first; each sidebar destination has its own URL fragment and supports browser Back/Forward and direct links:

- `#overview`: health, model readiness, replicas, active tokens and request counts.
- `#playground`: service-specific request forms and streamed or media responses.
- `#tokens`: create, edit, expire and revoke scoped access tokens.
- `#runtime`: CPU threads where supported, replica information and live/restart settings.
- `#updates`: check versions and explicitly download weights.
- `#connections`: caller addresses and public endpoints.
- `#models` and `#voices`: project models and cloned voices, shown only when supported.

Collapse/Expand switches between labeled sidebar and icon rail on desktop and mobile. The non-secret sidebar preference is saved per service in this browser. Navigation preserves form drafts and active Playground requests; sign-out still clears credentials and cancels work. Page names appear once in the main header. No preview data or cross-service selector ships in the real admin UI. Existing authentication, quotas, settings precedence and explicit-download policy remain in effect.
