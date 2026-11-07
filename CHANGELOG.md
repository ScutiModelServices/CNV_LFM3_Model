# Changelog

## Unreleased

### Breaking: common service environment variables

Service-owned environment variables now use `SERVICE_*`. Old names are no longer read.
Rename old names once in your real `.env`, Compose `environment:` block, and CI/secret settings.

| Old name | New name |
|---|---|
| `LFM3_ADMIN_PASSWORD` | `SERVICE_ADMIN_PASSWORD` |
| `LFM3_CACHE_SIZE` | `SERVICE_CACHE_SIZE` |
| `LFM3_DTYPE` | `SERVICE_DTYPE` |
| `LFM3_HIDE_REASONING` | `SERVICE_HIDE_REASONING` |
| `LFM3_HOST` | `SERVICE_HOST` |
| `LFM3_MAX_INFLIGHT` | `SERVICE_MAX_INFLIGHT` |
| `LFM3_MAX_PROJECT_MODELS` | `SERVICE_MAX_PROJECT_MODELS` |
| `LFM3_MEM_LIMIT` | `SERVICE_MEM_LIMIT` |
| `LFM3_MODEL` | `SERVICE_MODEL` |
| `LFM3_NUM_THREAD` | `SERVICE_NUM_THREAD` |
| `LFM3_OLLAMA_MODEL` | `SERVICE_OLLAMA_MODEL` |
| `LFM3_OLLAMA_URL` | `SERVICE_OLLAMA_URL` |
| `LFM3_PORT` | `SERVICE_PORT` |
| `LFM3_PROJECT_MODELS_DIR` | `SERVICE_PROJECT_MODELS_DIR` |
| `LFM3_REPLICAS` | `SERVICE_REPLICAS` |
| `LFM3_THINKING` | `SERVICE_THINKING` |
| `LFM3_TOKENS_FILE` | `SERVICE_TOKENS_FILE` |
| `LFM3_UPDATE_CHECK_HOURS` | `SERVICE_UPDATE_CHECK_HOURS` |
| `LFM3_WARM` | `SERVICE_WARM` |
| `LFM3_WEB_DIR` | `SERVICE_WEB_DIR` |
| `LFM3_WEIGHTS_MARKER` | `SERVICE_WEIGHTS_MARKER` |

- Default HTTP port moves from 9170 to 29202. Update explicit old ports in your real `.env`, saved tool-service `backends.json` connections, and browser/MCP client configurations once. Compose now uses 29202 inside API replicas and nginx; deployments using the old Compose default must recreate containers. A custom host-port override stays in effect until you change it; container ports still move to 29202.

- Renamed `LFM3Model` to `CNV_LFM3_Model`; Docker project, API image, services, load balancer and volumes now use `cnv_lfm3_model` names. Callers on `citadel_core` connect to `cnv_lfm3_model_lb` at the existing port.
- Docker volume migration: existing volumes with old names are orphaned; renaming does not move data. Stop the old stack before copying; never use `down -v`. The commands below assume the previous default Compose project name; substitute actual volume names if `-p` or `COMPOSE_PROJECT_NAME` overrode it.
  - `lfm3_models` → `cnv_lfm3_model_models`: `docker volume inspect lfm3_models && docker volume create cnv_lfm3_model_models && docker run --rm -v lfm3_models:/from:ro -v cnv_lfm3_model_models:/to alpine:3.21 sh -c "cd /from && cp -a . /to/"`
  - `lfm3_tokens` → `cnv_lfm3_model_data`: `docker volume inspect lfm3_tokens && docker volume create cnv_lfm3_model_data && docker run --rm -v lfm3_tokens:/from:ro -v cnv_lfm3_model_data:/to alpine:3.21 sh -c "cd /from && cp -a . /to/"`
- To retain an old volume instead, set its top-level volume definition to `external: true` and `name: <old-volume-name>` in a local Compose override. Rollback: stop the renamed stack, restore the previous checkout and folder name, and restart the old stack with its original volumes; copy back newer data first if the renamed stack accepted writes.

- `run.bat` loads `.env` from the service folder for a local run: it passes `--dotenv`, the service prints which variable names it loaded (never the values), and a real environment variable still wins. A plain `python src/app.py` and Docker never read `.env`.
- Untracked folders now start with `.` or `_`: `zip_versions/` is `_zip_versions/`. A local `voices`, `tem_code` or `zip_versions` folder from an older checkout needs renaming by hand.
- `run.bat` is now a menu (run the service, deploy, build the release ZIP) and `run.bat run|deploy|zip` skips it. `tools/deploy.bat`, `tools/make_zip.bat` and `tools/deploy.local.example.bat` are gone; the local deploy target is `tools/deploy.local.ini` (copy `tools/deploy.local.example.ini`).
- Admin page: **Connect to this service** card with the addresses other services can use (this page's address, same PC, Docker network, `host.docker.internal`) and every endpoint, each with a Copy button.
- Ollama backend: `SERVICE_THINKING` (`off` or `on`, also on the Settings card) and `SERVICE_HIDE_REASONING` (default on). With hide on, reasoning the model wrote into its answer is dropped (everything before the last `</think>`) and a streamed reply is sent in one piece when complete. Turn it off to stream the raw text.

- Optional Ollama backend: set `SERVICE_OLLAMA_URL` (and `SERVICE_OLLAMA_MODEL`) to answer through an Ollama server with a quantised GGUF, thinking off. Streaming, the answer cache and the admin page work as before; project models and CPU threads are not forwarded. Unset = the torch engine as before.

- Admin **Try it** panel: descriptor-driven public API requests, live text streams, JSON/media output, status and latency, cancellation and redacted curl. Auth choice (b): pasted public token stays in memory; normal scope, limits and caches apply. Shared `web/playground.js` is copied across all model and tool services.

- `run.bat`: runs `uv sync` directly; `python -m uv` failed when uv was installed only as a program (winget).
- Docker: `.dockerignore` keeps `.git`, `.venv`, tests and local state out of the build context (the same file in every model service).
- Docs: set CPU threads to the number of physical cores, not logical CPUs.
- `/metrics` also returns `lfm3_request_seconds`, a histogram of how long `/v1` calls took on that replica.
- Compose: optional `SERVICE_MEM_LIMIT` caps the container's RAM (default no cap).

- Answer cache (`SERVICE_CACHE_SIZE`, default 256, 0 = off; `X-Cache` header): the last answers to identical `temperature` 0 requests are sent again without generating.
- `POST /v1/chat` accepts `"stream": true`: the answer arrives as JSON lines (`content` pieces, then `done`).

- First version: LFM3-1.7B served on the CPU with `transformers`, with the admin page, project
  tokens (scope, rate limit, expiry), metrics, Settings card, update checks and weight downloads shared with
  `CNV_BitNet2B_Model`, `CNV_MiniCPM52B_Model` and `DSC_Laya_Model`.
- `POST /v1/chat` takes `messages`, `project`, `temperature` and `max_tokens`. Tools, schemas and thinking are refused
  with 422.
- Project models are checkpoint folders loaded in process (LRU).
