# Frontend Admin — cod, UI și flow

`frontend-admin` este interfața principală a aplicației Libra Assist. Este un
frontend server-rendered construit cu FastAPI, Jinja2, JavaScript și CSS. Nu este
un SPA și nu necesită Node.js.

## 1. Tehnologii

| Tehnologie | Rol |
|---|---|
| FastAPI | rute web și proxy către backend |
| Jinja2 | randarea paginilor HTML |
| JavaScript vanilla | chat, cancel, clipboard, sesiuni, recorder și viewer |
| CSS | layout responsive și stări vizuale |
| httpx | comunicare async cu backend-ul |
| python-docx | generare DOCX |
| python-pptx | generare PPTX |
| ReportLab | generare PDF |
| Web MediaRecorder API | captură microfon în browser |

Frontend-ul rulează implicit la:

```text
http://localhost:7800
```

și apelează backend-ul la:

```text
http://localhost:7799
```

În Docker, `BACKEND_URL` devine:

```text
http://host.docker.internal:7799
```

## 2. Structura codului

```text
frontend-admin/
├── app/
│   ├── main.py
│   ├── api_client.py
│   ├── config.py
│   ├── artifacts.py
│   ├── document_export.py
│   ├── forms.py
│   └── service_catalog.py
├── templates/
│   ├── base.html
│   ├── chat.html
│   ├── overview.html
│   ├── knowledge.html
│   ├── search.html
│   ├── ask.html
│   ├── agents.html
│   ├── tools.html
│   └── status.html
└── static/
    └── styles.css
```

### `app/main.py`

Conține:

- rutele paginilor;
- flow-ul `/chat/message`;
- upload și document extraction;
- inferența cererilor naturale pentru audio/document/format;
- generarea artifactelor;
- anularea request-urilor;
- proxy pentru sesiuni și grounding sources.

### `app/api_client.py`

Izolează toate apelurile către backend:

- timeout de 240 secunde;
- transformarea erorilor FastAPI în `BackendError`;
- metode pentru health, config, collection, chunk, ingest, search, ask, sessions,
  speech și agents.

### `app/document_export.py`

Transformă răspunsul final în:

- PDF;
- DOCX;
- PPTX;
- TXT;
- Markdown;
- JSON.

Parserul recunoaște headings, bullet points și liste numerotate pentru a păstra
structura în documentele Office/PDF.

### `app/artifacts.py`

Artifactele generate sunt păstrate în memorie:

- TTL: o oră;
- maximum 100 de fișiere;
- eliminarea automată a celor expirate sau a celui mai vechi.

Aceste fișiere nu sunt persistente după restartul containerului.

## 3. Paginile UI

| Pagină | Funcționalitate |
|---|---|
| Overview | health, provider LLM, embeddings, Qdrant și agenți |
| Knowledge Base | upload, extract, chunk preview, ingest și reset collection |
| Search | semantic search și scoruri |
| Test Answer | testarea controlată a endpoint-ului `/ask` |
| Chat | conversații persistente, RAG, audio și documente |
| Agents | personas locale și agenți Foundry |
| Tools | web fetch, TTS și STT |
| Platform Status | configurație efectivă și status servicii |

## 4. UI-ul Chat

Layout-ul este împărțit în:

```text
┌──────────────────────────────┬─────────────────────────┐
│ Conversation + composer      │ Conversation controls   │
│                              │ Answer settings         │
│ messages                     │                         │
│                              │                         │
│ textarea                     │                         │
│ attach · microphone · send   │                         │
└──────────────────────────────┴─────────────────────────┘
```

Coloana din dreapta este sticky. Conține:

- Saved session;
- New chat;
- Delete session;
- Agent;
- Execution;
- Content formatting;
- Generated file type;
- Deliver as;
- Top K;
- Use RAG;
- Shared memory;
- Fact-check.

## 5. Answer settings și checkbox-uri

Fiecare selector opțional are checkbox propriu:

- checkbox nebifat: valoarea vizibilă nu este impusă;
- schimbarea selectorului: checkbox-ul se bifează automat;
- checkbox bifat: valoarea devine override explicit.

Cele două câmpuri de document sunt separate.

### Generated file type

- PDF `.pdf`
- Word `.docx`
- PowerPoint `.pptx`
- Plain text `.txt`
- Markdown `.md`
- JSON `.json`

Selectarea tipului de fișier:

- bifează automat câmpul;
- selectează automat `Deliver as: Generated document`;
- poate fi modificată ulterior printr-o alegere explicită în `Deliver as`.

### Content formatting

- Plain text
- Markdown
- Bullet list
- Table
- JSON
- Executive summary
- Technical report

Acesta controlează structura conținutului, nu extensia fișierului.

Exemple:

```text
PDF + Bullet list
PPTX + Plain text
DOCX + Technical report
TXT + Bullet list
Markdown file + Markdown formatting
```

## 6. Prioritatea promptului față de UI

Instrucțiunea scrisă în chat are prioritate față de selectoare.

```text
Prompt explicit
    >
setare UI bifată
    >
default plain/conversation/backend
```

Exemple:

- UI: PDF + bullet points; prompt: „PPTX în plain text”  
  rezultat: PPTX + plain text;
- UI: DOCX; prompt: „răspunde vocal și generează PDF”  
  rezultat: audio + PDF;
- fără checkbox-uri; prompt: „generează document plain text cu bullet points”  
  rezultat: TXT + bullet points;
- fără checkbox-uri și fără instrucțiune de format  
  rezultat: răspuns plain în conversație.

Inferența naturală este implementată în `infer_document_request()` și normalizează
diacriticele înainte de potrivirea intent-ului.

## 7. Flow-ul unui mesaj

```text
Browser submit
   │
   ├── salvează mesajul user în UI
   ├── capturează history
   ├── generează generation_id
   ├── golește textarea și file input
   └── schimbă Send în Stop generating
   │
   ▼
POST /chat/message
   │
   ├── rezolvă checkbox-uri și priorități
   ├── interpretează document/audio/format din prompt
   ├── extrage documentul atașat
   └── apelează backend POST /ask
   │
   ▼
Backend answer + sources + usage + memory
   │
   ├── TTS, dacă este cerut
   ├── generează document, dacă este cerut
   └── salvează artifactele în memoria frontend-ului
   │
   ▼
UI render answer + history + sources + downloads
```

## 8. Stop generating

La trimitere:

- butonul `Send message` devine `Stop generating`;
- browserul păstrează un `AbortController`;
- frontend-ul trimite un `generation_id` backend-ului.

La stop:

1. este apelat endpoint-ul backend de cancel;
2. task-ul frontend este anulat;
3. request-ul browserului este abortat;
4. răspunsul incomplet nu este adăugat în conversație;
5. backend-ul nu persistă turn-ul după commit boundary.

## 9. Copy și Edit

Pentru fiecare mesaj:

- `Copy` scrie conținutul în clipboard; nu modifică textarea;
- `Edit` copiază conținutul în composer și mută focusul;
- mesajul original rămâne în history.

Textarea este golită imediat după submit.

## 10. Sesiuni și history

Frontend-ul păstrează:

- ultimele mesaje vizibile în `localStorage`;
- ID-ul sesiunii active în `localStorage`.

Backend-ul rămâne sursa persistentă pentru:

- sesiuni;
- mesaje;
- summaries;
- metadata;
- sources;
- usage;
- guardrail;
- shared-memory information.

UI-ul poate:

- crea un chat nou;
- încărca o sesiune salvată;
- șterge sesiunea curentă;
- afișa history după refresh.

## 11. Upload și document analysis

Composer-ul acceptă:

- PDF;
- DOC/DOCX;
- PPT/PPTX;
- TXT/Markdown;
- CSV/JSON/XML/YAML/HTML;
- RTF/log;
- fișiere de cod uzuale.

Fișierele legacy `.doc` și `.ppt` trebuie convertite în formatele moderne pentru
extragere completă.

Documentul atașat este:

1. citit de frontend;
2. trimis backend-ului pentru extract;
3. persistat în `uploads/` pentru sesiune, dacă este cazul;
4. injectat în prompt ca date neîncrezute;
5. folosit și pentru extragerea întrebărilor individuale.

Un document cu întrebări nu este tratat ca sursă factuală RAG.

## 12. Microfon, STT și TTS

Microfon:

1. browserul solicită permisiune;
2. MediaRecorder capturează audio;
3. frontend-ul trimite fișierul către `/chat/transcribe`;
4. backend-ul folosește Azure Speech-to-Text;
5. textul este inserat în composer.

TTS:

- este activat prin selector sau prompt natural;
- răspunsul este sintetizat în WAV;
- markerii de citare numerică nu sunt citiți;
- audio pornește automat când browserul permite autoplay;
- se poate combina cu un document în același răspuns.

## 13. Grounding sources

Sub răspuns sunt afișate sursele selectate de retrieval.

La click:

- se deschide un dialog în interiorul chatului;
- conținutul este încărcat de la backend;
- documentul poate fi citit fără navigare în afara paginii.

Download-ul sursei poate fi convertit de frontend în:

- Markdown;
- TXT;
- PDF;
- DOCX.

Sursa este identificată prin allowlist-ul backend, nu printr-un path furnizat
direct de browser.

## 14. Documente generate

### PDF

ReportLab produce pagini A4, headings și bullet points.

### DOCX

python-docx păstrează headings, `List Bullet` și `List Number`.

### PPTX

python-pptx produce:

- title slide;
- metadata;
- content slides;
- continuarea automată după opt elemente;
- headings și bullets.

### TXT, Markdown și JSON

- TXT: text și metadata lizibile;
- Markdown: titlu și conținut Markdown;
- JSON: answer plus metadata serializată.

## 15. Rendering-ul mesajelor

Un mesaj assistant poate afișa:

- conținut;
- agent și model;
- token usage și cost estimat;
- fact-check;
- grounding guardrail;
- current/shared memory;
- grounding sources;
- butoane Copy/Edit;
- audio player;
- download pentru unul sau mai multe artifacte.

Statusul guardrail este informativ și reflectă politica permisivă:

- `passed`: răspunsul a trecut sau auditorul indisponibil a fost tratat
  `fail open`;
- `review_required`: lipsește o citare și răspunsul intră în audit/rescriere,
  fără handoff automat;
- `rewrite`: auditorul a corectat conținutul sau citările;
- `handoff` / `regulated_refusal`: lipsește suport material sau cererea implică
  o decizie individuală reglementată.

Parafrazarea și sinteza între surse compatibile sunt acceptate. UI-ul nu
transformă un simplu warning într-un refuz și păstrează motivul tehnic în
metadata mesajului.

Mesajele de stare sunt afișate în zona dialogului:

- Ready to answer;
- analysing/generating;
- stopped;
- error;
- document/audio ready.

## 16. CSS și responsive UI

Stilurile sunt în `static/styles.css`.

Elemente principale:

- `.chat-workspace`: grid conversație + controls;
- `.chat-control-column`: coloană sticky;
- `.chat-panel`: zona principală;
- `.chat-messages`: scroll pentru history;
- `.chat-composer`: textarea și acțiuni;
- `.chat-optional-setting`: selector cu checkbox;
- `.chat-guardrail`: status guardrail;
- `.chat-source-dialog`: viewer modal;
- media query pentru layout pe o singură coloană.

Starea `applied` evidențiază setările bifate. Starea `delivery-active`
evidențiază tipul de fișier când livrarea include document.

## 17. Configurație

Frontend-ul citește:

```dotenv
BACKEND_URL=http://localhost:7799
```

Timeout-ul HTTP este 240 secunde pentru a permite:

- agenți Foundry;
- document analysis;
- fact-check;
- guardrail semantic;
- generare mai lungă.

În `docker/frontend/compose-admin.host-api.yml`:

```yaml
BACKEND_URL: http://host.docker.internal:7799
```

## 18. Rulare

Din rădăcina proiectului, pe Windows:

```powershell
.\scripts\dev-admin.ps1
```

Pe Linux/macOS:

```bash
./scripts/dev-admin.sh
```

Nu porni `frontend/` pentru această aplicație; interfața funcțională descrisă aici
este `frontend-admin`.

## 19. Teste relevante

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider `
  tests/test_admin_exports.py tests/test_app_structure.py
```

Testele verifică:

- existența controalelor UI;
- checkbox-urile Answer settings;
- prioritatea promptului;
- PDF/DOCX/PPTX;
- bullet formatting;
- speech și dual delivery;
- artifacts;
- viewer și download sources;
- cancel.
