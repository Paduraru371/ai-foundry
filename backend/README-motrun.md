# Backend Libra Assist

Backend-ul este o aplicație FastAPI care implementează RAG, agenți locali sau
Azure Foundry, memorie persistentă, analiză de documente, speech, fact-check,
guardrails și evaluarea rezultatelor.

## 1. Tehnologii

| Tehnologie | Utilizare |
|---|---|
| Python + FastAPI | API, validare și orchestrarea flow-urilor |
| Pydantic Settings | încărcarea configurației din `.env` |
| Qdrant | stocarea și căutarea vectorilor |
| SQLite | cache embeddings și sesiuni persistente |
| Azure AI Inference | chat și embeddings Azure |
| OpenAI / Anthropic / LM Studio | provideri alternativi |
| Azure AI Foundry Agent Service | execuție hosted opțională |
| Azure Speech | speech-to-text și text-to-speech |
| python-docx / python-pptx / pypdf | extragerea documentelor Office/PDF |
| httpx | apeluri HTTP și fact-check |
| pytest | teste unitare și de integrare |

Entry point:

```text
backend/main.py → backend.api.routers.*
```

`backend/main.py` asamblează aplicația, CORS și routerele. Logica este împărțită
pe domenii, nu concentrată în entry point.

## 2. Structura codului

```text
backend/
├── agents/
│   ├── local_agent.py
│   ├── foundry_agent.py
│   ├── persona.py
│   └── personas/
├── api/
│   ├── dependencies.py
│   └── routers/
├── core/
│   ├── config.py
│   ├── embeddings.py
│   ├── embedding_cache.py
│   ├── llm.py
│   └── token_usage.py
├── evaluation/
│   └── crosscheck.py
├── ingestion/
├── memory/
├── retrieval/
├── schemas/
├── services/
└── main.py
```

## 3. Routerele API

| Router | Responsabilitate |
|---|---|
| `ops.py` | `/health`, `/config` |
| `rag.py` | chunking, ingest, collection, search și surse |
| `generation.py` | `/ask` și anularea generării |
| `sessions.py` | sesiuni, mesaje și history |
| `documents.py` | extragerea textului din upload-uri |
| `agents.py` | personas locale și agenți Foundry |
| `tools.py` | speech, transcriere și web fetch |
| `azure.py` | status și integrare Azure |

Documentația interactivă este disponibilă la:

```text
http://localhost:7799/docs
```

## 4. Ingestion și chunking

Flow:

```text
Markdown/document
   │
   ▼
chunking
   │
   ▼
embeddings cu cache
   │
   ▼
upsert cu IDs stabile în Qdrant
```

Strategii:

- `static`: segmente de dimensiune fixă;
- `dynamic`: respectă limite naturale și dimensiunea țintă;
- `heading`: păstrează ierarhia Markdown și titlul;
- `sentence`: grupează un număr configurabil de propoziții;
- `semantic`: rupe textul când similaritatea propozițiilor scade sub prag.

La ingest se calculează un fingerprint din:

- hash-ul textului;
- titlul documentului;
- parametrii de chunking;
- providerul și modelul embeddings.

Dacă fingerprint-ul și numărul de chunks corespund indexului existent,
documentul primește status `unchanged`. Nu este rechunked și nu se fac apeluri
noi de embeddings.

Scriptul `scripts/ingest_corpus.py` menține și un manifest incremental. Fișierele
`data/README.md` și `data/questions.md` nu sunt indexate. Sursa veche `questions`
este eliminată din Qdrant.

## 5. Cache-ul embeddings

Cache-ul este implementat în:

```text
backend/core/embedding_cache.py
runtime/embedding_cache.sqlite3
```

Cheia logică este:

```text
provider + model + SHA-256(text)
```

Consecințe:

- texte duplicate sunt embedded o singură dată;
- cache-ul supraviețuiește restartului;
- schimbarea modelului nu reutilizează vectori incompatibili;
- dimensiunea cache-ului este limitată prin configurație.

## 6. Retrieval

Flow-ul de retrieval este:

```text
query
  │
  ├── embedding
  ├── search candidate pool în Qdrant
  ├── score threshold
  ├── scor hibrid cosine + lexical coverage
  ├── deduplicare Jaccard
  ├── diversitate și limită per sursă
  └── reranking LLM pentru /ask
```

Scorul determinist folosește implicit:

```text
75% cosine normalizat + 25% acoperire lexicală
```

Lexical coverage ajută pentru:

- taxe și sume;
- ani și versiuni;
- nume de produs;
- termeni de policy.

Reranker-ul LLM:

- primește candidate pool-ul deja filtrat;
- returnează indicii pasajelor relevante;
- poate returna `[]`;
- nu completează artificial Top K cu pasaje respinse;
- folosește ordinea deterministă dacă răspunsul său este invalid sau providerul
  este indisponibil.

## 7. Generarea răspunsului

Endpoint-ul principal este `POST /ask`.

Flow:

1. validează request-ul;
2. pregătește sesiunea, history și shared memory;
3. încarcă persona locală sau agentul hosted;
4. extrage întrebările din documentul atașat, dacă există;
5. rulează retrieval și reranking;
6. oprește flow-ul înainte de answer LLM dacă nu există context relevant;
7. construiește promptul final;
8. execută modelul;
9. aplică guardrails;
10. rulează fact-check dacă a fost cerut;
11. persistă turn-ul numai dacă nu a fost anulat;
12. returnează answer, sources, usage, memory și metadata.

Formate de conținut:

- `plain`
- `markdown`
- `bullet_list`
- `table`
- `json`
- `executive_summary`
- `technical_report`

Tipuri de livrare cunoscute de backend:

- `conversation`
- `speech`
- `document`
- `speech_document`

Generarea efectivă a fișierului și audio-ului este realizată în Frontend Admin
după ce backend-ul produce conținutul final.

## 8. Personas

O persona este definită prin:

```text
backend/agents/personas/<name>.json
backend/agents/personas/<name>.md   # policy opțional
```

JSON-ul conține:

- instructions;
- reguli de stil;
- temperatură și max tokens;
- cerința de citări;
- comportamentul pentru suport insuficient;
- reasoning effort;
- lista de tools.

Fișierul Markdown adiacent conține politica operațională. Cache-ul personas este
bazat pe `mtime`, deci modificările sunt încărcate la următorul request fără
restart.

Pentru `motrun-onboarding`, policy-ul descrie:

- relevanță strictă produs/client/canal/perioadă;
- `SUPPORTED`, `PARTIAL`, `CONFLICT`, `HANDOFF`;
- răspuns util și parțial înaintea unui handoff inutil;
- refuz numai pentru decizii individuale KYC/AML/PEP/sancțiuni/risc sau lipsă
  materială de suport;
- reguli anti-halucinație;
- citări numerice;
- handoff către personalul băncii fără contacte inventate.

## 9. Guardrails și refusal management

Persona Motrun folosește două niveluri.

### Nivel determinist

- verifică indicii citărilor `[n]`;
- respinge indici mai mari decât numărul pasajelor;
- permite un handoff controlat fără citări;
- marchează un răspuns factual fără citări ca `review_required`, fără să îl
  înlocuiască imediat;
- înlocuiește răspunsul numai pentru citări inexistente sau lipsă totală de
  context relevant.

### Audit semantic LLM

Evaluatorul verifică:

- entailment pentru fiecare afirmație;
- relevanța exactă;
- produs, client, canal, dată, taxă, termen și excepții;
- over-refusal și under-refusal;
- decizii reglementate.

Auditul permite:

- parafrazare fidelă;
- sinteză între pasaje compatibile;
- răspuns parțial cu o calificare scurtă;
- corectarea citărilor prin `rewrite`;
- incertitudine minoră exprimată clar, fără handoff.

Acțiuni:

- `pass`
- `rewrite`
- `handoff`
- `regulated_refusal`
- `safety_refusal`

O rescriere este acceptată numai dacă păstrează citări valide. Configurația
implicită este:

```dotenv
GROUNDING_GUARDRAIL_FAIL_CLOSED=false
```

Dacă auditorul este indisponibil sau întoarce un format invalid, răspunsul
original este păstrat și metadata indică `auditor_unavailable` sau
`auditor_invalid_output`. Handoff-ul este rezervat lipsei materiale de suport,
unei citări către un pasaj inexistent sau unei decizii individuale reglementate.

Pentru un deployment care preferă blocarea în caz de eroare:

```dotenv
GROUNDING_GUARDRAIL_FAIL_CLOSED=true
```

## 10. Sesiuni și memorie

Persistență:

```text
runtime/sessions.sqlite3
```

La un turn nou se folosesc:

1. summary-ul sesiunii curente;
2. summaries relevante din alte sesiuni;
3. history recent în limita mesajelor și tokenilor;
4. mesajul curent;
5. documentul atașat;
6. instrucțiunea de format.

Mesajele vechi sunt comprimate semantic cu LLM. Dacă modelul eșuează, se
salvează un fallback determinist.

Shared memory:

- citește un număr limitat de sesiuni recente;
- compară query-ul cu titlu + summary;
- combină similarity semantic, lexical match și recency;
- injectează numai sesiunile care trec pragul;
- tratează memoria ca date neîncrezute, nu ca instrucțiuni.

## 11. Anularea generării

Frontend-ul trimite un `generation_id`. Endpoint-ul de cancel marchează request-ul
ca anulat. Backend-ul verifică starea la limitele importante:

- înainte și după retrieval;
- înainte și după model;
- înainte și după guardrail/fact-check;
- înainte de persistare.

Persistarea este commit boundary: un răspuns anulat nu intră în sesiune.

## 12. Documente, speech și fact-check

Extragere acceptată:

- PDF;
- DOCX;
- PPTX;
- text, Markdown, CSV, JSON, HTML și cod.

Limitele sunt controlate prin `MAX_UPLOAD_BYTES` și `MAX_DOCUMENT_CHARS`.

Speech:

- STT pentru întrebări dictate;
- TTS pentru răspunsuri;
- markerii `[1]`, `[2]` sunt eliminați numai din textul trimis către TTS.

Fact-check:

- caută pe web prin providerul configurat;
- citește un număr limitat de pagini;
- este separat de sursele interne RAG;
- metadata și usage sunt întoarse în răspuns.

## 13. Grounding sources

Sursele din corpus sunt allowlisted. Backend-ul expune:

- conținut pentru viewer-ul din browser;
- download Markdown original.

`README.md` și `questions.md` nu pot fi deschise ca surse RAG. Path traversal nu
este permis deoarece sursa este rezolvată prin allowlist.

## 14. Usage și cost

Răspunsul API conține usage pe faze:

- answer;
- rerank;
- grounding guardrail;
- fact-check;
- memory compaction.

Pentru Azure GPT-5-mini se calculează estimări configurabile pentru:

- input;
- cached input;
- output.

Aceste valori sunt estimări operaționale, nu factură Azure.

## 15. Evaluarea rezultatelor

`backend/evaluation/crosscheck.py` implementează:

- Hit@K;
- MRR;
- semantic answer/evidence check;
- LLM-as-judge pentru relevance, groundedness, completeness și refusal.

Dataset:

```text
evals/onboarding_retrieval.json
```

Rulare:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_results.py
```

Cu answer embeddings și judge LLM:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_results.py --answers --llm-judge
```

## 16. Configurație backend

Setările sunt încărcate din `.env` de `backend/core/config.py`.

| Grup | Variabile principale |
|---|---|
| Server | `API_PORT` |
| Qdrant | `QDRANT_URL`, `QDRANT_COLLECTION` |
| Chunking | `CHUNK_STRATEGY`, `CHUNK_SIZE`, `CHUNK_OVERLAP` |
| Retrieval | `TOP_K`, `RETRIEVAL_SCORE_THRESHOLD`, `RETRIEVAL_VECTOR_WEIGHT` |
| Guardrails | `GROUNDING_GUARDRAIL_*` |
| Memory | `HISTORY_*`, `SESSION_*`, `SHARED_MEMORY_*` |
| Embeddings | `EMBEDDING_PROVIDER`, `EMBEDDING_CACHE_*` |
| Agent | `AGENT_MODE`, `AGENT_PERSONA`, `FOUNDRY_AGENT_ID` |
| Azure | `AZURE_AI_*`, `AZURE_SEARCH_*` |
| Speech | `AZURE_SPEECH_*` |
| Web | `SEARCH_PROVIDER`, `SEARCH_API_KEY`, `FACT_CHECK_PAGES` |

Configurația efectivă, cu secrete mascate, este disponibilă la:

```text
GET /config
```

## 17. Rulare și teste

Din rădăcina proiectului:

```powershell
.\scripts\dev-admin.ps1
```

Doar backend, dacă Docker/Qdrant sunt deja pornite:

```powershell
.\scripts\dev-admin.ps1 -SkipDocker
```

Teste:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```
