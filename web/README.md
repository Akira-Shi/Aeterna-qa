# AETERNA-QA web frontend (P8)

Vite + React + TypeScript, plain CSS. Talks to the local FastAPI backend through a dev proxy (`/api` to `127.0.0.1:8000`).

## Run on Windows

1. API, in one terminal:
   ```
   cd aeterna_qa
   python -m api
   ```
2. Frontend, in a second terminal:
   ```
   cd web
   npm install
   npm run dev
   ```
3. Open http://localhost:5173.

`npm run build` type-checks and builds to `web/dist`.

## Screenshots

With the API and `npm run dev` running: `npx playwright install chromium` once, then
`node screenshots.mjs <path-to-csv>` (real API) and `node mocks.mjs <path-to-csv>` (mid-run and planner-unavailable states). Output goes to `web/screenshots/`.

## Notes

- Design tokens in `src/tokens.css` are copied from the Explain report so the app and the downloaded report match.
- The API must not change for this app; it only uses the endpoints in `aeterna_qa/api/main.py`.
