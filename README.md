# Libra Assist - Motrun Florin

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
=======

# AI Engineering on Azure — Libra Bank Academy

Course materials for **Lucian Gruia's** module (sessions 9–15) of the Libra Bank
Academy, delivered by **Digital Stack** for **Libra Bank**. Seven sessions ×
2.5h = 17.5h, Wed 22 Jul → Thu 30 Jul 2026, on Azure AI Foundry.

The module is one continuous build: students extend the agent they already built
with George (given a banking persona) into a production-grade, Azure-native
solution — grounded, measured, observable, cost-bounded, able to act.

## Repository layout

```
ai-acad-foundry-2026/
├── curriculum-ai-engineering-on-azure.md   ← v1 plan (superseded by docs/curriculum.html; kept for depth)
├── HANDOFF.md                              ← context dump — read this first if you're a new agent
├── resources/                              ← shared assets
│   ├── theme.css                           ← the one stylesheet every page links
│   ├── nav.js                              ← shared page behaviour (section nav, theme toggle)
│   └── ui-kit.md                           ← design system + component reference
├── docs/                                   ← student-facing course material (standalone HTML)
│   ├── curriculum.html                     ← the living curriculum — module homepage
│   ├── session-template.html               ← clone this per session
│   ├── sessions/                           ← one page per session (sNN-<slug>.html)
│   │   ├── s01-foundations.html            ← Session 1 · Foundations
│   │   ├── s02-foundry.html                ← Session 2 · Microsoft Foundry
│   │   └── s03-model-integration.html      ← Session 3 · Model Integration
│   ├── topics/                             ← reference deep-dives (cross-linked from sessions)
│   │   ├── ref-foundry.html                ← Microsoft Foundry, step by step
│   │   ├── ref-cloud-computing.html        ← cloud computing overview
│   │   └── ref-git.html                    ← how git works
│   └── assignments/                        ← homework briefs (aNN.md)
│       └── a1.md                           ← Assignment 1 · run backend, build admin UI
├── code/                                   ← demo code shown live
│   └── backend/                            ← RAG Teaching API (FastAPI + Qdrant, uv, docker compose;
│                                              see its README for run & credentials guides)
└── _raw_inputs/   (git-ignored)            ← private source material (WhatsApp, spreadsheet, logs)
```

## Conventions

- **Docs are plain HTML.** Each session page links `resources/theme.css` and uses
  the classes documented in `resources/ui-kit.md`. Start from `session-template.html`.
- **Palette is locked.** Primary `#2c2d2f · #0de7e7 · #c73a52 · #eeeeee`;
  secondary `#1cb9c8 · #001240 · #ed6a5a · #292f36 · #e4c02e`. Reference tokens,
  never hardcode hexes. See the UI kit.
- **Demos live in `code/`.** Python against Azure AI Foundry (`azure-ai-projects`,
  `azure-ai-inference`), keyless auth (`DefaultAzureCredential`). Models in play:
  `gpt-5.1` + `text-embedding-3-small`. Never commit endpoints or keys.
- **`_raw_inputs/` is git-ignored** and stays local.

## Getting oriented

1. Read `curriculum-ai-engineering-on-azure.md` — what's being taught and why.
2. Read `HANDOFF.md` — where we are, decisions locked, and open blockers.
3. Read `resources/ui-kit.md` — how to make anything look right.
