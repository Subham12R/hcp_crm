# HCP Interaction CRM Frontend

React, TypeScript, Vite, Tailwind CSS, and Redux client for the HCP Interaction CRM.

## Run locally

Prerequisites: Node.js, npm, and the backend running at `http://127.0.0.1:8000`.

```powershell
npm ci
npm run dev
```

Open <http://localhost:5173>. The client calls `http://127.0.0.1:8000/api` by default.

To use another API address, set `VITE_API_BASE_URL` before starting Vite:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api"
npm run dev
```

## Commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the development server. |
| `npm run build` | Type-check and create the production build in `dist/`. |
| `npm run lint` | Run ESLint. |
| `npm run preview` | Serve the production build locally. |

For the full stack, use the root [Docker Compose setup](../README.md#run-with-docker). It builds this frontend and serves it at <http://localhost:8080>.
