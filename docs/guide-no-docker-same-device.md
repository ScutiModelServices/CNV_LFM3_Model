# LFM3Model: without Docker, on Windows

Run Liquid LFM3-1.7B on the CPU directly with Python: one process, no load balancer, listening on `127.0.0.1:9170`.

## Requirements
- Windows with Python 3.11 or newer and uv (`winget install astral-sh.uv`).
- Internet on the first start (about 4 GB of weights).
- RAM for the model (one copy).

## Start
Double-click `run.bat`, or run it in a terminal from `LFM3Model\`. Choose **1 Run the service** in the menu, or run `run.bat run` to skip the menu. It runs `uv sync` to create or update `.venv`, then starts
`python src/app.py`. The first start downloads about 4 GB of weights.

Linux or macOS:
```bash
cd LFM3Model
uv sync
uv run python src/app.py
```

## Settings
`run.bat` loads `.env` in this folder (copy `.env.example`); a real environment variable wins over it. Set variables in `.env` or in the environment before starting:

| Variable | Default | Effect |
|---|---|---|
| `LFM3_HOST` | `127.0.0.1` | Bind address. Use `0.0.0.0` only if other devices must reach it. |
| `LFM3_PORT` | `9170` | Port. |
| `LFM3_ADMIN_PASSWORD` | empty | Unlocks `/admin/` and requires tokens on every call but `/health`. Empty = no auth. |
| `LFM3_WARM` | `1` | Load the model at start; with `0` the first request pays the load time. |
| `LFM3_NUM_THREAD` | the library decides | CPU threads. Set it to the number of **physical** cores. |

PowerShell: `$env:LFM3_ADMIN_PASSWORD = "secret"; .\run.bat`
Bash: `LFM3_ADMIN_PASSWORD=secret uv run python src/app.py`

## Check
```bash
curl http://127.0.0.1:9170/health
```
`ready` is `false` until the model has loaded. Then open `http://127.0.0.1:9170/admin/` (see [guide-web-ui.md](guide-web-ui.md)),
make a token, and try a call:
```bash
curl -X POST http://127.0.0.1:9170/v1/chat -H "Content-Type: application/json" -H "X-Internal-Token: lfm3_..." -d '{"messages":[{"role":"user","content":"Say hello in one sentence."}]}'
```

## Stop
Ctrl+C in the terminal. Do not run this and the Docker stack together: both use port 9170.

## Tests
`uv run pytest`.
