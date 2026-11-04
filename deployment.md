# Deploying LFM3Model

LFM3Model is one HTTP service (port 9170). It runs as `lfm3` replicas behind an nginx load balancer,
`lfm3_lb`. Callers use `http://<host>:9170`; they never reach a replica directly.

## Requirements

- Docker with Compose v2.
- About 5 GB of RAM **per replica** (each replica holds the model), plus the same again for every loaded
  project model.
- Network access on the first start to download the weights (about 4 GB) from Hugging Face.
- CPU only. The Dockerfile installs the CPU build of torch and fails the build if a CUDA or ROCm build is found.

## Settings

In `.env` next to `docker-compose.yml`:

| Variable | Default | Effect |
|---|---|---|
| `LFM3_REPLICAS` | `1` | Number of `lfm3` containers. Read by Compose. |
| `LFM3_MEM_LIMIT` | `0` (no cap) | RAM cap per container, for example `7g` (bfloat16 weights use about 5.3 GiB). An out-of-memory kill then stays in the container instead of starving the host. Read by Compose. |
| `LFM3_PORT` | `9170` | Host port `lfm3_lb` publishes. |
| `LFM3_ADMIN_PASSWORD` | empty | Password for `/admin/`. When set, every call except `/health` must send a project token as `X-Internal-Token`. Empty = no auth. |
| `LFM3_NUM_THREAD` | torch decides | Starting value for the CPU threads card; a value saved on `/admin/` wins. Use the number of physical cores (`lscpu`: cores x sockets), not logical CPUs; more threads than cores slows every call. |

On the **Settings** card of `/admin/` (saved in `settings.json` beside the tokens, shared by all replicas; a saved
value beats the environment variable named in brackets): update check hours (`LFM3_UPDATE_CHECK_HOURS`, 6),
in-flight cap (`LFM3_MAX_INFLIGHT`, 0 = 4), answers kept per replica (`LFM3_CACHE_SIZE`, 256, 0 = off), project models loaded per replica (`LFM3_MAX_PROJECT_MODELS`, 2),
project models folder (`LFM3_PROJECT_MODELS_DIR`, empty = off; in Docker use `/models/projects`), base model
(`LFM3_MODEL`, restart), number format (`LFM3_DTYPE`, restart: `bfloat16` or `float32`; try `float32` if answers take many seconds on a CPU without native bfloat16 maths, it needs twice the RAM) and load at start (`LFM3_WARM`, restart). Compose does not pass these; add the variable
under `environment:` of `lfm3` to use one as a starting value.

## Start

```bash
docker compose up -d --build
curl http://127.0.0.1:9170/health
```

Expect `"ready": true` once a replica has loaded the model. The first start downloads the weights into the `models`
volume, so `lfm3_lb` can take a few minutes to appear (the health check allows 300 s before failures count; run
`docker compose ps` and wait).

## Scaling

```bash
LFM3_REPLICAS=3 docker compose up -d --build
docker compose restart lfm3_lb
```

The restart is needed because nginx resolves replica addresses once at start.

## Project models

Copy a complete checkpoint folder into the shared volume and set the **Project models folder** on the Settings card
to `/models/projects`:

```bash
docker compose exec lfm3 mkdir -p /models/projects
docker compose cp ./garrison lfm3:/models/projects/garrison
```

Call `/v1/chat` with `"project": "garrison"`. Restart replicas after replacing an already loaded checkpoint.

## Updating the weights

The **Updates** card compares the downloaded revision of the Hugging Face repository with its newest one. **Download
new weights** fetches it into the models volume; every replica drops its old copy within a few seconds and loads the
new one on its next request (it needs RAM for both for a moment). The download is the repository's current `main`.
Updating the service itself: `docker compose up -d --build`, then `docker compose restart lfm3_lb`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `lfm3_lb` never starts | No replica is healthy yet (first download, or out of memory). `docker compose logs lfm3`. |
| Replicas restart in a loop | Out of RAM. Lower `LFM3_REPLICAS`. |
| 401 "Invalid token" | The caller sends no project token, or a revoked one. |
| 422 on `tools`, `schema` or `thinking` | Not supported by this service. |
| 429 | Over the token's rate limit, or too many calls waiting for the model. |
| Slow answers | CPU speed with `transformers` is modest for any model of this size; use a 4-bit GGUF runtime if speed matters. Raise CPU threads on `/admin/`. |
| nginx 502 after scaling | `lfm3_lb` not restarted after the replica count changed. |

## Releasing

A plain publish (`tools\deploy.bat` option 1) only updates the `live` branch. For a release set `VERSION` (and
`pyproject.toml` to the same number), commit, then run `tools\deploy.bat` option R or
`py tools\publish_live.py --release`. `tools\make_zip.bat` then builds `zip_versions\LFM3Model-<VERSION>.zip`.
