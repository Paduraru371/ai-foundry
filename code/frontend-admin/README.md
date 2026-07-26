# Libra Assist Admin Console

Server-rendered administration frontend built with FastAPI, Jinja2 and CSS.
It calls the RAG backend at `http://localhost:7799`.

## Features

| Page | Purpose |
|---|---|
| Overview | Display Qdrant and every supported LLM and embedding model |
| Knowledge Base | Preview chunks, ingest documents, inspect and reset the collection |
| Search | Run semantic searches and inspect similarity scores |
| Test Answer | Compare answers with or without RAG and inspect the final prompt |

Unavailable services, missing provider configuration and API errors are displayed.

## Run the Frontend

From the `ai-foundry` directory, with the  virtual environment already set
up, use the command for your operating system.

Linux:

```bash
./scripts/linux/start-frontend.sh
```

Windows PowerShell:

```powershell
.\scripts\windows\start-frontend.ps1
```

Open <http://localhost:7800>.

The backend must be running on <http://localhost:7799>.

