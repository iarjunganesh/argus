# ARGUS web UI

The browser front end for the ARGUS API: run a demo case or submit an entity, follow the five
agents as they run, then read the report as a case file. Next.js (App Router), TypeScript and
shadcn/ui. The browser calls the API
directly, so the API must list this site's origin in `ARGUS_CORS_ORIGINS`.

Requires Node.js 26 (the version in [`.nvmrc`](.nvmrc)).

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
the recorded outcomes in [`tests/fixtures/demo_scenarios.json`](../tests/fixtures/demo_scenarios.json)
(the tier, the score and its working, each finding's evidence, the sanctions hold), check the
cases queue and the cold-start notice, walk the demo review (Cayman Synth Capital's match,
decision and sign-off, kept across a reload; Jane Synthetic decided without a sign-off; a missing
reason; a browser that blocks storage), all in light, dark and phone layouts, and check every page
and review state with axe (WCAG 2.2 AA rules). The first
run needs a browser: `npm run e2e:browsers`. CI runs them against the API container.

## Where things are

| Path              | What it holds                                                                                                                                                                                                                 |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/app/`        | The pages: `/` (the cases queue and, outside demo mode, the form) and `/assessments/[id]` (progress, then the case file)                                                                                                      |
| `src/components/` | The investigation flow, the case header, the score's working, findings and evidence, the sanctions match panel, the demo review and the role switch, the cases queue, the form; `ui/` holds shadcn/ui components              |
| `src/lib/`        | The API client, the report's wording, the case file's logic (`case.ts`), the cases queue store (`queue.ts`), the demo review's rules (`review.ts`) and store (`review-store.ts`), the progress-stream reducer, the demo cases |
| `e2e/`            | Playwright tests                                                                                                                                                                                                              |

## The demo review

A visitor can play the review a person does after ARGUS recommends. It is labelled on every case:
"Demo review: kept in this browser only and sent nowhere. ARGUS recommends; a person decides."
The header's role switch chooses Analyst or Approver; one browser plays both, and the page says
the demo cannot check that they are two people.

- With a sanctions hold, the analyst first resolves the match in its panel: confirm (true match),
  clear (false positive) or escalate.
- The analyst then decides the case: approve, approve with enhanced due diligence (the only
  approval offered when a rule requires it), decline or escalate. A confirmed match leaves
  decline or escalate.
- A HIGH or CRITICAL decision waits for the approver, who signs off or returns it to the analyst;
  LOW and MEDIUM cases are decided by the analyst alone. Escalating closes the review.
- Every step needs a reason, except a sign-off. The rules (`src/lib/review.ts`) refuse a step out
  of turn or in the wrong role, and replay the stored steps through the same rules, so an edited
  store cannot reach a state they forbid.

The steps (role, choice, reason, time, named after the report's empty `decision_record` slots)
are kept in `localStorage` by report ID, never the entity's name, and dropped a day after the
newest step, as the API drops its reports; a report the API no longer has forgets its review.
The cases queue shows each run's review state. If the browser blocks storage, the review works
for the open page and says it is not kept. Nothing is sent to the API.

The public site runs on Vercel; how it is deployed, and why from this folder only, is in
[`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md) ("The web UI"). `.vercelignore` lists what the
upload leaves out.

The colours in `src/app/globals.css` are checked by `scripts/ci/render_assets.py --check`: every
declared text/background pair must pass WCAG AA in both themes. `tests/test_accessibility.py`
holds the risk colours to the audited palette in `src/argus/accessibility/wcag.py`.
`src/app/icon.svg` is a copy of `assets/brand/logo-mark.svg`, written by the same script.
`src/app/shadcn.css` is the stylesheet of the shadcn package (4.23.0, MIT), copied so the site
does not install that command-line package; add a component with `npx shadcn@4.23.0 add <name>`.
