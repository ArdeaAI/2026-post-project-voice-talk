# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. `CLAUDE.md` is a symlink to `AGENTS.md` — edit `AGENTS.md` and both stay in sync.

# 2026 Post Project Voice Talk

## Overview

This is a two-part project for a Chattanooga AI Collective meeting following the 2026 Project Voice conference:

1. **Presentation** — a Reveal.js + Quarto deck on the state of AI voice agents in 2026.
2. **CLI demo** (`voice/`) — a Rich-based Python CLI that runs a few variations of voice agents live during the talk.

Python is managed by `uv` with `pyproject.toml` at the repo root. TypeScript/JS is managed by Bun with `package.json` at the repo root. Both stacks coexist in a single repo because the deck (TS/Reveal.js) and the demo (Python/Rich) ship together.

Reference: Quarto Reveal.js (https://quarto.org/docs/presentations/revealjs/), Reveal.js (https://revealjs.com/).

The `ai/` dir is for planning notes and specs and is gitignored — don't put anything there that needs to ship.

## Repo Layout

- `voice/main.py` — entrypoint for the `voice` CLI script (registered as a `[project.scripts]` entry in `pyproject.toml`, so `uv run voice` works once installed).
- (no Bun TypeScript entrypoint) — Bun's only role here is running `package.json` scripts (`bun start` / `bun run render` / `bun run publish`). If custom JS for the deck is ever needed, add a `slides.js` and reference it via `include-after-body` in `_quarto.yml` rather than coupling it to a `bun run` entry.
- `pyproject.toml` — Python 3.12 project, hatchling build, ruff + pytest dev group. Wheel packages = `["voice"]` (no `__init__.py` by design — see global preferences).
- `package.json` — Bun project, ESM, depends on `reveal.js`. Bun-types provide TS support.
- `tsconfig.json` — strict mode, bundler resolution, `noUncheckedIndexedAccess`, JSX = react-jsx. Don't relax these.
- `ai/` — gitignored scratch dir for plans/specs.

## Commands

Python (CLI demo):
- `uv sync` — install/refresh the venv from `uv.lock`.
- `uv run voice` — run the CLI (uses the `voice = "voice.main:main"` script entry).
- `uv run python -m voice.main` — equivalent direct invocation.
- `uv run pytest` — run tests (none exist yet; `pytest` + `pytest-asyncio` are in the dev group).
- `uv run pytest path/to/test_file.py::test_name` — run a single test.
- `uv run ruff check .` / `uv run ruff format .` — lint / format. Ruff line length is 120 (global default).

TypeScript (presentation):
- `bun install` — install JS deps.
- `bun test` — run tests if any get added (use `bun:test`, not jest/vitest).
- There's no TS entrypoint right now; Bun is used purely as the script runner for the slides commands below.

Slides (Quarto + Reveal.js — `slides.qmd` at repo root):
- `bun start` — live preview at `localhost:[port]` with hot reload (wraps `quarto preview slides.qmd`).
- `bun run render` — produce `slides.html` + `slides_files/` for serving (wraps `quarto render`).
- `bun run publish` — push to GitHub Pages via `quarto publish gh-pages` (one-time setup needed: a `gh-pages` branch and Pages enabled in repo settings).
- `slides.html` and `slides_files/` are build artifacts — the deck source of truth is `slides.qmd` + `_quarto.yml` + `gruvbox.scss` + `references.bib`.

## TypeScript Side

Default to using Bun instead of Node.js.

- Use `bun <file>` instead of `node <file>` or `ts-node <file>`
- Use `bun test` instead of `jest` or `vitest`
- Use `bun build <file.html|file.ts|file.css>` instead of `webpack` or `esbuild`
- Use `bun install` instead of `npm install` or `yarn install` or `pnpm install`
- Use `bun run <script>` instead of `npm run <script>` or `yarn run <script>` or `pnpm run <script>`
- Use `bunx <package> <command>` instead of `npx <package> <command>`
- Bun automatically loads .env, so don't use dotenv.

## APIs

- `Bun.serve()` supports WebSockets, HTTPS, and routes. Don't use `express`.
- `bun:sqlite` for SQLite. Don't use `better-sqlite3`.
- `Bun.redis` for Redis. Don't use `ioredis`.
- `Bun.sql` for Postgres. Don't use `pg` or `postgres.js`.
- `WebSocket` is built-in. Don't use `ws`.
- Prefer `Bun.file` over `node:fs`'s readFile/writeFile
- Bun.$`ls` instead of execa.

## Testing

Use `bun test` to run tests.

```ts#index.test.ts
import { test, expect } from "bun:test";

test("hello world", () => {
  expect(1).toBe(1);
});
```

## Frontend

Use HTML imports with `Bun.serve()`. Don't use `vite`. HTML imports fully support React, CSS, Tailwind.

Server:

```ts#index.ts
import index from "./index.html"

Bun.serve({
  routes: {
    "/": index,
    "/api/users/:id": {
      GET: (req) => {
        return new Response(JSON.stringify({ id: req.params.id }));
      },
    },
  },
  // optional websocket support
  websocket: {
    open: (ws) => {
      ws.send("Hello, world!");
    },
    message: (ws, message) => {
      ws.send(message);
    },
    close: (ws) => {
      // handle close
    }
  },
  development: {
    hmr: true,
    console: true,
  }
})
```

HTML files can import .tsx, .jsx or .js files directly and Bun's bundler will transpile & bundle automatically. `<link>` tags can point to stylesheets and Bun's CSS bundler will bundle.

```html#index.html
<html>
  <body>
    <h1>Hello, world!</h1>
    <script type="module" src="./frontend.tsx"></script>
  </body>
</html>
```

With the following `frontend.tsx`:

```tsx#frontend.tsx
import React from "react";
import { createRoot } from "react-dom/client";

// import .css files directly and it works
import './index.css';

const root = createRoot(document.body);

export default function Frontend() {
  return <h1>Hello, world!</h1>;
}

root.render(<Frontend />);
```

Then, run index.ts

```sh
bun --hot ./index.ts
```

For more information, read the Bun API docs in `node_modules/bun-types/docs/**.mdx`.
