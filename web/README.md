# ARGUS web UI

The browser front end for the ARGUS API: submit an entity, follow the five agents as they run,
then read the report. Next.js (App Router), TypeScript and shadcn/ui. The browser calls the API
directly, so the API must list this site's origin in `ARGUS_CORS_ORIGINS`.

Requires Node.js 24 (the version in [`.nvmrc`](.nvmrc)).

## Run it locally

Start the API from the repository root, allowing this site's origin:

```sh
# PowerShell: $env:ARGUS_CORS_ORIGINS = "http://127.0.0.1:3000,http://localhost:3000"
export ARGUS_CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
uv run uvicorn argus.api.main:app --host 127.0.0.1 --port 8000
```

Then, in `web/`:

```sh
npm ci
npm run dev        # http://localhost:3000
```

`NEXT_PUBLIC_API_URL` sets where the API is (default `http://127.0.0.1:8000`).
`NEXT_PUBLIC_ARGUS_DEMO_ONLY=true` replaces the form with a notice and offers only the synthetic
demo cases, matching an API run with `ARGUS_DEMO_ONLY=true` (as deployed). Both are read at build
time.

## Checks

```sh
npm run lint
npm run format:check
npm run typecheck
npm test               # unit tests (vitest) for src/lib
npm run build
npm run test:e2e       # Playwright: needs `npm run build` and the API running as above
```

The end-to-end tests run the six demo scenarios through the site and compare each report with
the recorded outcomes in [`tests/fixtures/demo_scenarios.json`](../tests/fixtures/demo_scenarios.json),
in light, dark and phone layouts, and check every page with axe (WCAG 2.2 AA rules). The first
run needs a browser: `npm run e2e:browsers`. CI runs them against the API container.

## Where things are

| Path              | What it holds                                                                     |
| ----------------- | --------------------------------------------------------------------------------- |
| `src/app/`        | The pages: `/` (new assessment) and `/assessments/[id]` (progress, then report)   |
| `src/components/` | The investigation flow, the report, the form; `ui/` holds shadcn/ui components    |
| `src/lib/`        | The API client, the report's wording, the progress-stream reducer, the demo cases |
| `e2e/`            | Playwright tests                                                                  |

The colours in `src/app/globals.css` are checked by `scripts/ci/render_assets.py --check`: every
declared text/background pair must pass WCAG AA in both themes. `tests/test_accessibility.py`
holds the risk colours to the audited palette in `src/argus/accessibility/wcag.py`.
`src/app/icon.svg` is a copy of `assets/brand/logo-mark.svg`, written by the same script.
