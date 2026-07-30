# Libra Assist Admin Console

Server-rendered administration frontend built with FastAPI, Jinja2 and CSS.
It calls the RAG backend at `http://localhost:7799`.

## Features

| Page | Purpose |
|---|---|
| Overview | Display Qdrant and every supported LLM and embedding model |
| Knowledge Base | Upload PDF/DOCX/PPTX/text, preview chunks, ingest documents, inspect and reset the collection |
| Search | Run semantic searches and inspect similarity scores |
| Chat | Multi-turn chat with per-message uploads and conversation/speech/document delivery |
| Test Answer | Select agent/RAG/fact-check/output format, attach a document, and inspect answer/token cost |
| Agents | Inspect personas, prompts and Foundry deployments |
| Tools | Test web extraction, text-to-speech and transcription |
| Platform Status | Inspect backend health, Azure resources and masked configuration |

Unavailable services, missing provider configuration and API errors are displayed.

## Run the Frontend

From the repository root, use the command for your operating system. The
scripts build and run the FastAPI admin frontend with Docker.

Linux:

```bash
./scripts/dev-admin.sh
```

Windows PowerShell:

```powershell
.\scripts\dev-admin.ps1
```

Open <http://localhost:7800>.

The backend must be running on <http://localhost:7799>.

Uploaded files are processed in memory by the backend. Modern Office formats
(`.docx`, `.pptx`) are supported; legacy `.doc`/`.ppt` files must first be saved
in their modern format. The Test Answer page reports provider token usage,
preflight input estimates, the configured output ceiling, and an estimated
Azure GPT-5-mini input/output cost. Pricing values are configurable in `.env`.

The Chat page stores the visible conversation in browser `localStorage` and sends
the latest turns back to `/ask` as bounded history. Optional Answer settings have
an explicit checkbox; changing a value enables its checkbox. Unchecked settings
do not override the backend defaults, and natural-language delivery/format
instructions in the message take priority over checked controls. Each answer can
stay in the conversation, become playable WAV speech, or be downloaded as PDF,
DOCX, PPTX, TXT, Markdown or JSON. While an answer is running, **Stop generating** cancels the
browser request and tells the backend to discard the generation before it is
persisted. **New chat** cancels any active generation and opens an empty backend
session while retaining completed sessions in the selector.
Generated files/audio are kept in a bounded in-memory store for one hour.
