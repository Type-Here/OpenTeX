# OpenTeX — Frontend

React + Vite single-page application for the OpenTeX collaborative LaTeX environment.

## Tech stack

| Library | Version | Purpose |
|---------|---------|---------|
| React | 19 | UI framework |
| Vite | 8 | Build tool and dev server |
| Axios | 1.x | HTTP client (JWT Bearer token injected automatically) |
| @uiw/react-codemirror | 4.x | Code editor with LaTeX syntax highlighting |
| codemirror-lang-latex | 0.4.x | LaTeX language extension for CodeMirror |

## Start (recommended — via Docker Compose)

```bash
docker compose up --build -d
# frontend available at http://localhost:5173
```

The Vite dev server runs inside the `frontend` container with hot-module reload enabled.

## Start standalone

```bash
cd frontend
npm install
npm run dev
# available at http://localhost:5173
```

Requires the backend running at `http://localhost:8000`.

## Pages

| Page | Route (logical) | Description |
|------|----------------|-------------|
| `LoginPage` | `/` (unauthenticated) | Sign-in and registration form |
| `DashboardPage` | `/` (authenticated) | "My Projects" and "Shared with me" |
| `ProjectDetailPage` | project detail | Metadata, collaborators, editor link |
| `EditorPage` | editor | Multi-pane LaTeX editor (file sidebar + CodeMirror + PDF preview) |
| `StatsPage` | stats | Aggregation statistics dashboard (admin only) |
| `BenchmarksPage` | benchmarks | Index benchmark results (admin only) |

## Structure

```
src/
├── api/          # Axios API clients (auth, projects, files, permissions, stats, users)
├── components/   # Shared UI components (ProjectCard, ProjectFormModal, PermissionsPanel, ConfirmDialog)
├── context/      # AuthContext — global auth state with localStorage persistence
├── pages/        # One file per page (see table above)
└── styles/       # CSS modules and global styles
```

## Available scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run lint` | Run ESLint |
