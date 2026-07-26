# Libra Assist

Libra Assist is a teaching RAG application. The backend
chunks and embeds documents, stores vectors in Qdrant, retrieves relevant context,
and generates answers. The admin frontend exposes the complete workflow.

## Architecture

```text
Browser :7800
    │
    ▼
Admin frontend (local FastAPI)
    │
    ▼
RAG API :7799 (Docker)
    │
    ▼
Qdrant :7833 (Docker)
```

## First-Time Setup

Requirements:

- Python 3.11 or newer
- Linux: Docker Engine with Docker Compose
- Windows: Docker Desktop running with Linux containers

Linux:

```bash
./scripts/linux/setup.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\setup.ps1
```

Python virtual environments are operating-system specific. If the same project
folder is moved between Linux and Windows, remove `.venv` and run the setup script
for the current operating system.

- Add the Azure values to `.credentials`.

### Credentials format

Create a file named exactly `.credentials` in the main `ai-foundry` folder.

```ini
SECRET_AZURE_AI_ENDPOINT=<your-endpoint>
SECRET_AZURE_AI_AUTH=key
SECRET_AZURE_AI_API_KEY=<your-key>
SECRET_AZURE_AI_CHAT_DEPLOYMENT=gpt-5-mini
SECRET_AZURE_AI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```


## Run the Complete Application

Linux:

```bash
./scripts/linux/start-all.sh
```

Windows PowerShell:

```powershell
.\scripts\windows\start-all.ps1
```

This starts the backend and Qdrant in Docker, then runs the admin frontend locally.


## Run Services Separately

### Linux

Open two terminals.

Terminal 1 — backend and Qdrant:

```bash
./scripts/linux/start-backend.sh
```

Terminal 2 — admin frontend:

```bash
./scripts/linux/start-frontend.sh
```

### Windows

Open two PowerShell terminals.

Terminal 1 — backend and Qdrant:

```powershell
.\scripts\windows\start-backend.ps1
```

Terminal 2 — admin frontend:

```powershell
.\scripts\windows\start-frontend.ps1
```

## Service URLs

| Service | URL |
|---|---|
| Admin frontend | <http://localhost:7800> |
| Backend Swagger | <http://localhost:7799/docs> |
| Backend health | <http://localhost:7799/health> |
| Qdrant dashboard | <http://localhost:7833/dashboard> |


| Purpose | Linux | Windows |
|---|---|---|
| Setup | `scripts/linux/setup.sh` | `scripts/windows/setup.ps1` |
| Backend + Qdrant | `scripts/linux/start-backend.sh` | `scripts/windows/start-backend.ps1` |
| Admin frontend | `scripts/linux/start-frontend.sh` | `scripts/windows/start-frontend.ps1` |
| Complete application | `scripts/linux/start-all.sh` | `scripts/windows/start-all.ps1` |
| Legacy Docker helper | `scripts/linux/docker-utils.sh` | `scripts/windows/docker-utils.ps1` |

### Docker legacy helper

`docker-utils.sh` on Linux and `docker-utils.ps1` on Windows handle old
`rag-api` and `rag-qdrant` containers that used fixed names and could conflict
with the current Compose-managed container names.

The helper is sourced and used automatically by:

- the platform-specific `start-backend` script, before starting the backend;
- the platform-specific `start-all` script, before starting the complete application.

For each legacy container, the function checks its Docker Compose project and
service labels. It removes the container only when it belongs to the old
`backend` project and matches the expected `api` or `qdrant` service. If the name
belongs to another project, startup stops with an error instead of deleting it.

The helper does not remove Docker volumes, so existing Qdrant data remains
available. It also does nothing when no legacy containers exist. In normal use,
do not run a `docker-utils` script directly; use the `start-backend` or
`start-all` script for your operating system.
