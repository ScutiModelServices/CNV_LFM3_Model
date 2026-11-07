# CNV_LFM3_Model: Docker Desktop on this PC

Run Liquid LFM3-1.7B on the CPU in Docker Desktop on the machine you work on, so other programs on it can call it.

## Requirements

- Docker Desktop with Compose v2 (Windows: WSL2 backend).
- About 5 GB of RAM **per replica** (each replica holds the model), plus the same again for every loaded
  project model. Keep `LFM3_REPLICAS=1` on a PC. Docker Desktop on Windows caps its engine at about half of your RAM unless you raise it in `.wslconfig`.
- Network access on the first start to download the weights (about 4 GB) from Hugging Face.
- CPU only. The Dockerfile installs the CPU build of torch and fails the build if a CUDA or ROCm build is found.

## Steps

1. Configure. In `CNV_LFM3_Model/`:
   ```bash
   cp .env.example .env
   ```
   Set `LFM3_ADMIN_PASSWORD` (empty = no auth and no admin page, fine for a local test). Leave `LFM3_PORT=29202`. Leave `LFM3_REPLICAS=1`.
2. Start:
   ```bash
   docker compose up -d --build
   ```
   The first start downloads about 4 GB of weights into the `cnv_lfm3_model_models` volume. `cnv_lfm3_model_lb` starts only after the service is healthy
   (up to 300 s grace). Watch with `docker compose ps` and `docker compose logs -f cnv_lfm3_model`.
3. Check:
   ```bash
   curl http://127.0.0.1:29202/health
   ```
   `ready` is `false` until the model has loaded, then `true`.
4. Open the admin page: `http://127.0.0.1:29202/admin/` (see [guide-web-ui.md](guide-web-ui.md)) and make a token for each caller.
5. Try a call:
   ```bash
   curl -X POST http://127.0.0.1:29202/v1/chat -H "Content-Type: application/json" -H "X-Internal-Token: lfm3_..." -d '{"messages":[{"role":"user","content":"Say hello in one sentence."}]}'
   ```
   Expect a JSON answer.
6. Callers connect to the published port. The caller holds the URL and token:
   - Caller on the host: `http://127.0.0.1:29202`.
   - Caller in another Docker stack on the same host: `http://host.docker.internal:29202`.

## Settings

In `.env` next to `docker-compose.yml`:

| Variable | Default | Effect |
|---|---|---|
| `LFM3_REPLICAS` | `1` | Number of `cnv_lfm3_model` containers. Read by Compose. |
| `LFM3_MEM_LIMIT` | `0` (no cap) | RAM cap per container, for example `7g` (bfloat16 weights use about 5.3 GiB). An out-of-memory kill then stays in the container instead of starving the host. Read by Compose. |
| `LFM3_PORT` | `29202` | Host port `cnv_lfm3_model_lb` publishes. |
| `LFM3_ADMIN_PASSWORD` | empty | Password for `/admin/`. When set, every call except `/health` must send a project token as `X-Internal-Token`. Empty = no auth. |
| `LFM3_NUM_THREAD` | torch decides | Starting value for the CPU threads card; a value saved on `/admin/` wins. Use the number of physical cores (`lscpu`: cores x sockets), not logical CPUs; more threads than cores slows every call. |

On the **Settings** card of `/admin/` (saved in `settings.json` beside the tokens, shared by all replicas; a saved
value beats the environment variable named in brackets): update check hours (`LFM3_UPDATE_CHECK_HOURS`, 6),
in-flight cap (`LFM3_MAX_INFLIGHT`, 0 = 4), answers kept per replica (`LFM3_CACHE_SIZE`, 256, 0 = off), project models loaded per replica (`LFM3_MAX_PROJECT_MODELS`, 2),
project models folder (`LFM3_PROJECT_MODELS_DIR`, empty = off; in Docker use `/models/projects`), base model
(`LFM3_MODEL`, restart), number format (`LFM3_DTYPE`, restart: `bfloat16` or `float32`; try `float32` if answers take many seconds on a CPU without native bfloat16 maths, it needs twice the RAM) and load at start (`LFM3_WARM`, restart). Compose does not pass these; add the variable
under `environment:` of `cnv_lfm3_model` to use one as a starting value.

## Daily use

```bash
docker compose ps          # state
docker compose logs -f cnv_lfm3_model
docker compose down        # stop (the weights volume is kept)
docker compose up -d --build && docker compose restart cnv_lfm3_model_lb   # after a code change
```

## Problems

| Symptom | Fix |
|---|---|
| `address already in use` on 29202 | Another copy (`run.bat`, or the same stack on another compose project) is running. Stop it or change `LFM3_PORT`. |
| `/health` shows `ready: false` for minutes | First start: the weights are downloading or loading. Check `docker compose logs -f cnv_lfm3_model`. |
| 401 Invalid token | The caller's token is missing or revoked; make one on `/admin/`. |
| Container restarts in a loop | Out of RAM. Raise the Docker Desktop memory limit or lower the replica count. |
| `cnv_lfm3_model_lb` never starts | No replica is healthy yet (first download, or out of memory). `docker compose logs cnv_lfm3_model`. |
| Replicas restart in a loop | Out of RAM. Lower `LFM3_REPLICAS`. |
| 422 on `tools`, `schema` or `thinking` | Not supported by this service. |
| 429 | Over the token's rate limit, or too many calls waiting for the model. |
| Slow answers | CPU speed with `transformers` is modest for any model of this size; use a 4-bit GGUF runtime if speed matters. Raise CPU threads on `/admin/`. |
| nginx 502 after scaling | `cnv_lfm3_model_lb` not restarted after the replica count changed. |

The load balancer also joins external `citadel_core` as `cnv_lfm3_model_lb`. Start the Citadel stack first so that network exists; tool services on it use `http://cnv_lfm3_model_lb:29202`. Docker project and API image are `cnv_lfm3_model` and `cnv_lfm3_model:latest`; persistent volumes have explicit `cnv_lfm3_model_*` names. Volume migration and rollback instructions are in [CHANGELOG.md](../CHANGELOG.md).
