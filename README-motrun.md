# Libra Assist — ghidul aplicației

Acesta este ghidul principal pentru pregătirea și rularea aplicației complete.
Documentația tehnică detaliată este separată astfel:

- [Backend](backend/README-motrun.md)
- [Frontend Admin](frontend-admin/README-motrun.md)

## 1. Ce rulează

Aplicația este alcătuită din trei procese:

| Componentă | Rol | Adresă implicită |
|---|---|---|
| Backend FastAPI | RAG, agenți, sesiuni, documente, speech și guardrails | `http://localhost:7799` |
| Frontend Admin | interfața web folosită pentru chat și administrare | `http://localhost:7800` |
| Qdrant | baza vectorială pentru chunks și embeddings | `http://localhost:7833/dashboard` |

Pe Windows, configurația recomandată este:

```text
Browser
   │
   ▼
Frontend Admin în Docker :7800
   │  http://host.docker.internal:7799
   ▼
Backend FastAPI pe Windows :7799
   │
   ├── Qdrant în Docker :7833
   ├── provider LLM
   ├── provider embeddings
   └── Azure Speech / web search, dacă sunt activate
```

Backend-ul rulează local pentru a putea folosi identitatea obținută prin
`az login`. Frontend Admin și Qdrant rulează în Docker.

## 2. Cerințe

Pentru Windows:

- Windows PowerShell;
- Python 3.11 sau mai nou;
- Docker Desktop configurat pentru Linux containers;
- acces la internet pentru instalarea inițială a dependențelor și providerii cloud;
- Azure CLI numai dacă se folosește `AZURE_AI_AUTH=identity`;
- un fișier `.env` configurat.

Verificări utile:

```powershell
py --version
docker version
docker info
az account show
```

`az account show` este necesar numai pentru configurația Azure cu autentificare
prin identitate.

## 3. Configurarea inițială

Din rădăcina repository-ului:

```powershell
Copy-Item .env.example .env
```

Completează `.env` fără să publici cheile în Git.

### Varianta Azure recomandată

```dotenv
LLM_PROVIDER=azure
EMBEDDING_PROVIDER=azure

AZURE_AI_ENDPOINT=https://<resource>.services.ai.azure.com/models
AZURE_AI_AUTH=identity
AZURE_AI_CHAT_DEPLOYMENT=gpt-5-mini
AZURE_AI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

AGENT_MODE=local
AGENT_PERSONA=motrun-onboarding

QDRANT_URL=http://localhost:7833
QDRANT_COLLECTION=libra_rag
```

Apoi:

```powershell
az login
az account show
```

Pentru autentificare cu key:

```dotenv
AZURE_AI_AUTH=key
AZURE_AI_API_KEY=<secret>
```

### Alternative de provider

Chat:

- `azure`
- `openai`
- `anthropic`
- `lmstudio`

Embeddings:

- `azure`
- `openai`
- `lmstudio`

Anthropic nu furnizează embeddings, deci trebuie combinat cu un provider de
embeddings acceptat.

## 4. Pornirea aplicației pe Windows

Comanda principală este:

```powershell
.\scripts\dev-admin.ps1
```

Nu este necesar să pornești manual frontend-ul. Scriptul selectează explicit
`frontend-admin`.

La fiecare pornire, scriptul:

1. creează `.venv` dacă lipsește;
2. instalează sau sincronizează `requirements.txt`;
3. verifică existența `.env`;
4. verifică Azure CLI numai dacă configurația selectată îl cere;
5. verifică portul backend;
6. pornește Docker Desktop dacă daemonul nu rulează;
7. pornește Qdrant;
8. oprește frontend-ul alternativ și pornește `frontend-admin`;
9. rulează ingest-ul incremental pentru corpus;
10. pornește backend-ul FastAPI local cu Uvicorn.

La final, deschide:

- Chat/Admin: <http://localhost:7800>
- Backend Swagger: <http://localhost:7799/docs>
- Qdrant Dashboard: <http://localhost:7833/dashboard>
- Backend health: <http://localhost:7799/health>

Terminalul rămâne ocupat de backend. `Ctrl+C` oprește backend-ul local, dar
containerele Qdrant și Frontend Admin rămân pornite.

## 5. Opțiunile scriptului

```powershell
.\scripts\dev-admin.ps1 -Port 7801
.\scripts\dev-admin.ps1 -Port 7801 -FrontendPort 7802
.\scripts\dev-admin.ps1 -Force
.\scripts\dev-admin.ps1 -SkipDocker
.\scripts\dev-admin.ps1 -NoReload
.\scripts\dev-admin.ps1 -BindAll
```

| Opțiune | Efect |
|---|---|
| `-Port 7801` | rulează backend-ul pe alt port |
| `-FrontendPort 7802` | publică Frontend Admin pe alt port în browser |
| `-Force` | oprește un proces Python/Uvicorn rămas pe port |
| `-SkipDocker` | nu pornește Qdrant și frontend-ul; util dacă rulează deja |
| `-NoReload` | dezactivează autoreload pentru backend |
| `-BindAll` | ascultă pe `0.0.0.0`, util pentru acces din rețea/Linux Docker |

Dacă schimbi portul backend prin `-Port`, scriptul transmite automat noul port
containerului Frontend Admin. `-FrontendPort` schimbă portul deschis în browser;
portul intern al containerului rămâne `7800`.

## 5.1. Predarea și rularea pe alt calculator Windows

Pentru un calculator nou, predă tot codul care există efectiv în working tree,
inclusiv fișierele noi. Dacă proiectul este transferat prin Git, modificările
trebuie comise și împinse înainte; un clone nu include fișiere necomise.

Nu publica `.env` în repository. Trimite-l separat, printr-un canal securizat,
sau trimite `.env.example` și valorile secrete printr-un secret manager.

Pe calculatorul destinatar trebuie instalate Python 3.11+, Docker Desktop cu
Linux containers și, numai pentru `AZURE_AI_AUTH=identity`, Azure CLI. Prima
rulare necesită internet pentru pachetele Python, imaginile Docker și serviciile
cloud. Cu autentificare prin identitate, destinatarul rulează întâi:

```powershell
az login
```

Din rădăcina proiectului, comanda portabilă (inclusiv când execution policy
blochează scripturile locale) este:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-admin.ps1
```

Dacă porturile implicite sunt ocupate:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-admin.ps1 `
  -Port 7801 -FrontendPort 7802
```

Portul Qdrant `7833` trebuie să fie disponibil. Scriptul verifică Docker CLI,
Docker Compose v2 și daemonul Linux, încearcă să pornească Docker Desktop,
creează mediul Python, instalează dependențele, pornește containerele, face
ingest incremental și pornește API-ul.

## 6. Oprirea componentelor

Backend:

```text
Ctrl+C
```

Frontend Admin:

```powershell
docker compose -f docker/frontend/compose-admin.yml `
  -f docker/frontend/compose-admin.host-api.yml down
```

Qdrant:

```powershell
docker compose -f docker/backend/compose.yml `
  -f docker/backend/compose.host-api.yml down
```

Comanda `down` nu șterge automat volumul persistent Qdrant. Nu folosi
`down -v` decât dacă intenționezi să ștergi indexul.

## 7. Scripturile importante

| Script | Utilizare |
|---|---|
| `scripts/dev-admin.ps1` | pornește aplicația recomandată pe Windows |
| `scripts/dev-admin.sh` | echivalent Linux/macOS pentru Frontend Admin |
| `scripts/dev.ps1` | runner generic; poate selecta `frontend` sau `frontend-admin` |
| `scripts/ingest_corpus.py` | indexează incremental fișierele din `data/` |
| `scripts/evaluate_results.py` | evaluează retrieval-ul și răspunsurile |
| `scripts/deploy_agent.py` | publică o persona în Azure Foundry Agent Service |
| `scripts/azure/*.ps1` | provisionare, inspectare și configurare Azure |

Ingest manual prin codul backend:

```powershell
.\.venv\Scripts\python.exe scripts\ingest_corpus.py --direct
```

Preview fără modificări:

```powershell
.\.venv\Scripts\python.exe scripts\ingest_corpus.py --dry-run
```

`data/README.md` și `data/questions.md` sunt excluse din corpus. Ingest-ul:

- sare peste documentele neschimbate;
- reindexează documentele modificate;
- elimină sursele șterse;
- curăță sursa exclusă `questions`;
- salvează manifestul în `runtime/corpus_ingest_manifest.json`.

## 8. Setările generale

### Qdrant și chunking

```dotenv
QDRANT_URL=http://localhost:7833
QDRANT_COLLECTION=libra_rag
CHUNK_STRATEGY=dynamic
CHUNK_SIZE=500
CHUNK_OVERLAP=80
SEMANTIC_THRESHOLD=0.75
```

Strategii disponibile: `static`, `dynamic`, `heading`, `sentence`, `semantic`.
Corpusul standard este încărcat de script cu strategia `heading`.

### Retrieval

```dotenv
TOP_K=4
RETRIEVAL_SCORE_THRESHOLD=0.30
RETRIEVAL_CANDIDATE_POOL=10
RETRIEVAL_VECTOR_WEIGHT=0.75
RETRIEVAL_DUPLICATE_THRESHOLD=0.82
```

Retrieval-ul combină similarity embeddings, potrivire lexicală, threshold,
deduplicare, diversitate și reranking LLM.

### Cache embeddings

```dotenv
EMBEDDING_CACHE_ENABLED=true
EMBEDDING_CACHE_PATH=runtime/embedding_cache.sqlite3
EMBEDDING_CACHE_MAX_ENTRIES=20000
```

Cheia cache-ului include providerul, modelul și hash-ul textului.

### Memorie și sesiuni

```dotenv
SESSION_DB_PATH=runtime/sessions.sqlite3
HISTORY_MAX_MESSAGES=16
HISTORY_MAX_TOKENS=10000
SESSION_SUMMARY_MAX_CHARS=4000
SESSION_COMPACTION_BATCH_MESSAGES=4
SHARED_MEMORY_SESSION_LIMIT=4
SHARED_MEMORY_MIN_SCORE=0.18
```

Sesiunile, mesajele, summary-urile și metadata răspunsurilor sunt persistate în
SQLite.

### Guardrails

```dotenv
GROUNDING_GUARDRAIL_LLM_ENABLED=true
GROUNDING_GUARDRAIL_FAIL_CLOSED=false
GROUNDING_GUARDRAIL_MAX_TOKENS=900
```

Persona `motrun-onboarding` folosește validare deterministă a citărilor și un
audit LLM de groundedness/refusal într-un mod permisiv. O citare lipsă trimite
răspunsul la review/rescriere, nu îl înlocuiește imediat cu handoff. Parafrazarea,
sinteza între pasaje compatibile și răspunsurile parțiale utile sunt permise.

Implicit este activ `fail open`: dacă auditul semantic nu poate rula, răspunsul
este păstrat și situația apare în metadata. Citările cu indici inexistenți,
invențiile materiale și deciziile individuale KYC/AML/risc rămân blocate.
Pentru un mediu care cere control maxim se poate seta:

```dotenv
GROUNDING_GUARDRAIL_FAIL_CLOSED=true
```

### Documente și speech

```dotenv
MAX_UPLOAD_BYTES=20971520
MAX_DOCUMENT_CHARS=120000
AZURE_SPEECH_VOICE=en-US-AvaMultilingualNeural
AZURE_SPEECH_LANGUAGE=en-US
```

Frontend-ul poate genera PDF, DOCX, PPTX, TXT, Markdown și JSON. Poate livra
răspunsul în conversație, audio, document sau audio plus document.

## 9. Flow-ul principal al unei întrebări

```text
Mesaj + setări + document opțional
        │
        ▼
Frontend Admin interpretează cererea naturală
        │
        ├── promptul scris are prioritate față de selectoare
        └── extrage documentul atașat
        │
        ▼
Backend pregătește history + summary + shared memory
        │
        ▼
Embedding query → Qdrant → threshold → rerank → diversity → LLM rerank
        │
        ▼
Persona + context + instrucțiuni de format → LLM
        │
        ▼
Citări + guardrail semantic + fact-check opțional
        │
        ▼
Persistare sesiune și metadata
        │
        ▼
Frontend: text / audio / document / surse deschise și descărcabile
```

## 10. Teste și evaluare

Suita locală:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Golden retrieval evaluation:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_results.py
```

Evaluare completă cu embeddings și LLM judge:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_results.py --answers --llm-judge `
  --output runtime\evaluation-full.json
```

Ultima comandă implică mai multe apeluri de model și cost suplimentar.

## 11. Probleme frecvente

### Docker pipe / Qdrant image

Mesaj:

```text
failed to connect to dockerDesktopLinuxEngine
```

Înseamnă că Docker Desktop sau Linux engine nu este pregătit. Rulează din nou
`dev-admin.ps1`; scriptul încearcă să pornească Docker Desktop și așteaptă
maximum două minute. Dacă eroarea persistă, deschide Docker Desktop și verifică
manual statusul engine-ului.

### Portul 7799 este ocupat

```powershell
.\scripts\dev-admin.ps1 -Force
```

Sau:

```powershell
.\scripts\dev-admin.ps1 -Port 7801
```

### Azure identity

Dacă este configurat `AZURE_AI_AUTH=identity`:

```powershell
az login
az account show
```

### Qdrant este gol

```powershell
.\.venv\Scripts\python.exe scripts\ingest_corpus.py --direct
```

### Frontend-ul nu vede backend-ul

Verifică:

```powershell
Invoke-RestMethod http://localhost:7799/health
docker logs rag-frontend-admin
```

În configurația recomandată, containerul folosește
`http://host.docker.internal:7799`.
