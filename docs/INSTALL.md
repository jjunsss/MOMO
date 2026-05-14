# Local/server install paths

For first-time evaluators who do not want a local install, use the
[Colab trial notebook](COLAB.md). This page is for local/server users
who want the GUI on their own machine.

The basic local install is just `scripts/start-gui.sh` (see the
[README Local/server quick start](../README.md#localserver-quick-start)).
This page covers what the shell installer handles automatically and
the Docker Compose path — both fully automated, no manual server setup
required after the host GPU driver is working.

## What the shell installer handles

`scripts/start-gui.sh` runs `scripts/bootstrap.sh` when setup is missing.
The bootstrapper auto-installs common system packages when possible:

- `curl`
- `ffmpeg`
- `python3`
- `python3-venv`
- `python3-pip` / package-manager equivalent

Supported package managers: `apt`, `dnf`, `yum`, `pacman`, `zypper`, `apk`.
It may ask for `sudo`. To disable system package installation:

```bash
SKIP_SYSTEM_DEPS=1 scripts/start-gui.sh
```

MOMO needs Python 3.10 or newer. If the server's `python3` is older
(for example Ubuntu 20.04 often defaults to Python 3.8), the installer
first looks for `python3.10`/`python3.11`/`python3.12`/`python3.13`.
If none is available, it installs `uv` into `~/.local/bin` and uses it
to install a user-local Python 3.10. You can still force a specific
interpreter:

```bash
scripts/start-gui.sh --setup --python /path/to/python3.10
```

NVIDIA drivers are not auto-installed. The server must already pass:

```bash
nvidia-smi
```

Ubuntu version normally does not need manual handling if the above GPU
driver check passes. The shell path handles old system Python versions,
and the Docker path uses a fixed Ubuntu 22.04 CUDA image. The host-level
pieces that still vary by server are NVIDIA driver support and, for
Docker, NVIDIA Container Toolkit / Docker Compose GPU support.

If `8501` is already occupied, the shell launcher automatically tries
`8502` through `8510` and prints the URL it selected. To force a port:

```bash
MOMO_GUI_PORT=8502 scripts/start-gui.sh
```

## Docker Compose

For repeatable deployment across servers. The host still needs an
NVIDIA driver, NVIDIA Container Toolkit, and Docker Compose v2 with
GPU support.

```bash
git clone https://github.com/jjunsss/MOMO.git
cd MOMO
docker compose up --build
```

Open <http://localhost:8501>.

The first Compose run pulls the Ollama model into a named Docker
volume (several minutes). Whisper `large-v3` downloads on first ASR
use and is cached in another volume. Recordings and outputs are
bind-mounted:

- `videos/` — upload/input staging
- `runs/` — generated transcripts, JSON, Markdown, evidence
- `topic_details.json`, `meeting_profile.md` — runtime defaults

Common overrides:

```bash
MOMO_GUI_PORT=8502 docker compose up --build
MOMO_DOCKER_GPUS='"device=0"' docker compose up --build
MOMO_LLM_MODEL=qwen3.5:9b docker compose up --build
```
