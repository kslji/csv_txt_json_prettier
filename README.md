# Format Prettify API — JSON / CSV / Text Beautifier

A production-ready backend service that formats messy **JSON**, **CSV**,
and plain **Text** into clean, readable output — like a "Prettier" for
data files. **Pure code logic only — no AI/LLM is used anywhere.**
Everything is built on Python's standard library (`json`, `csv`, `textwrap`).

## What each formatter does (all pure stdlib, no AI)

| Format | Library | What it does |
|---|---|---|
| **JSON** | `json` | Validates syntax (with exact line/column on error), pretty-prints with configurable indent, optional key sorting, optional minify mode, reports structural stats (depth, key count, size) |
| **CSV** | `csv` | Auto-detects delimiter (`,` `\t` `;` `\|`) via `csv.Sniffer` + fallback heuristic, validates row/column consistency, renders as an **aligned monospace table**, a **Markdown table**, or **clean normalized CSV**, and returns a JSON preview of the first rows |
| **Text** | `textwrap`, `re` | Normalizes line endings, expands tabs, trims trailing whitespace, collapses excess blank lines, optional word-wrap to a target width |

There's also a **`/format/auto`** endpoint that detects which of the three
formats you gave it (from filename, then content sniffing) and applies the
right formatter automatically.

## Project structure

```
app/
  main.py                    # FastAPI app, CORS, error handlers
  config.py                  # env-based settings
  models.py                  # Pydantic response schema
  api/routes.py               # /format/json, /csv, /text, /auto, /health
  services/
    json_formatter.py          # json.loads/dumps + stats + error location
    csv_formatter.py            # csv.Sniffer + 3 output renderers
    text_formatter.py           # normalization + textwrap
    format_detector.py          # filename/content-based auto-detection
  utils/
    constants.py                # size limits, defaults
    validators.py                # size/encoding validation
tests/
  test_api.py                   # 17 pytest cases
Dockerfile
docker-compose.yml
requirements.txt
```

## Running locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive Swagger UI.

Run tests:
```bash
pytest -v
```

## Running with Docker

```bash
docker compose up --build
```

## API Reference

All endpoints accept **either** a file upload (`file`) **or** raw pasted
text (`raw_text` form field) — send whichever fits your frontend UI.

### `GET /api/v1/health`
Uptime check.

### `POST /api/v1/format/json`
| Field | Type | Default | Notes |
|---|---|---|---|
| `file` / `raw_text` | file / text | — | one required |
| `indent` | int | 2 | 0–8 spaces |
| `sort_keys` | bool | false | |
| `minify` | bool | false | collapses to single-line compact JSON |

```bash
curl -X POST http://localhost:8000/api/v1/format/json \
  -F 'raw_text={"b":2,"a":1}' -F "sort_keys=true"
```
Response includes `formatted_content`, `is_valid`, and on failure an
`error` object with `line`/`column`/`position` pointing at the exact
syntax problem.

### `POST /api/v1/format/csv`
| Field | Type | Default | Notes |
|---|---|---|---|
| `file` / `raw_text` | file / text | — | one required |
| `output_style` | string | `aligned` | `aligned` \| `markdown` \| `clean_csv` |
| `delimiter` | string | auto-detected | override if sniffing guesses wrong |
| `has_header` | bool | true | controls `preview_records` generation |

```bash
curl -X POST http://localhost:8000/api/v1/format/csv \
  -F "file=@data.csv" -F "output_style=markdown"
```
Response includes `stats.delimiter_detected`, `stats.mismatched_rows`
(row-count validation), `stats.duplicate_headers`, and up to 20
`preview_records` as JSON objects for easy table rendering in a frontend.

### `POST /api/v1/format/text`
| Field | Type | Default | Notes |
|---|---|---|---|
| `file` / `raw_text` | file / text | — | one required |
| `wrap_width` | int \| null | null | word-wrap to N characters |
| `max_consecutive_blank_lines` | int | 1 | collapse extra blank lines |
| `strip_trailing_whitespace` | bool | true | |
| `expand_tabs` | bool | true | |
| `tab_size` | int | 4 | |

### `POST /api/v1/format/auto`
Same `file`/`raw_text` input, no formatting options — detects the type and
applies sensible defaults. Response includes `detected_format`.

**Error response shape (all endpoints):**
```json
{ "error": "Input exceeds the 5MB size limit.", "code": "input_too_large" }
```
Common codes: `no_input_provided`, `empty_input`, `input_too_large`,
`invalid_encoding`, `invalid_output_style`, `rate_limit_exceeded`.

## Frontend integration example (JavaScript / fetch)

```javascript
async function formatJson(rawText, options = {}) {
  const formData = new FormData();
  formData.append("raw_text", rawText);
  if (options.sortKeys) formData.append("sort_keys", "true");
  if (options.minify) formData.append("minify", "true");

  const response = await fetch("https://your-api-domain.com/api/v1/format/json", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.error || "Formatting failed");
  }
  return response.json(); // { is_valid, formatted_content, error, stats }
}
```

File-upload variant (works the same for CSV/text/auto endpoints):
```javascript
async function formatFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("https://your-api-domain.com/api/v1/format/auto", {
    method: "POST",
    body: formData,
  });
  return response.json();
}
```

Render `formatted_content` in a `<pre>` or a code editor component
(e.g. CodeMirror/Monaco) with the matching language mode for syntax
highlighting.

## Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `FMT_CORS_ORIGINS` | `*` | Comma-separated allowed frontend origins |
| `FMT_RATE_LIMIT` | `60/minute` | Per-IP rate limit |
| `FMT_MAX_INPUT_MB` | `5` | Max input size |
| `FMT_ENVIRONMENT` | `production` | Informational |

## Production deployment notes

- **CORS**: set `FMT_CORS_ORIGINS` to your real frontend domain(s) before launch.
- **Rate limiting**: in-memory per-IP via `slowapi`. For multi-instance deployments, point it at Redis (`storage_uri`) so limits are shared across replicas.
- **Stateless**: no database, no disk writes — input is processed entirely in memory, so scale horizontally by adding replicas behind a load balancer.
- **TLS**: terminate HTTPS at a reverse proxy / managed load balancer in front of this service.
- **Size limits**: `FMT_MAX_INPUT_MB` guards against oversized pastes/uploads; tune per your expected file sizes.
- **Global-ready**: all three formatters operate on raw bytes/UTF-8 text and structural syntax (JSON/CSV grammar, whitespace) — there's no language-specific logic, so this works identically for any language's content.
