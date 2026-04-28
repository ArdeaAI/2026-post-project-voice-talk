# The State of AI Voice Agents in 2026

Talk + live demos for the **Chattanooga AI Collective**, recapping what shipped in the voice-AI space around the 2026 Project Voice conference.

The talk goes from **less technical → more technical**:

1. The voice landscape — no-code → API → libraries
2. Live demo: Sesame AI phone app (closed beta)
3. Live demo: the `voice/` CLI in this repo (you can run it too)
4. Paper discussion: Sesame's *[Crossing the Uncanny Valley of Conversational Voice](https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice)*

> **Slides**: hosted at GitHub Pages (URL added after first publish). Live preview locally with `bun start`.

---

## If you're an attendee

You don't need to do anything to follow along — but if you want to **run the demos on your own laptop while the talk is happening**, here's how.

### 1. Clone and install

```bash
git clone https://github.com/Sinjhin/2026-post-project-voice-talk
cd 2026-post-project-voice-talk

# Python side (the demo CLI)
uv sync

# JS/TS side (the slides + Bun helpers)
bun install
```

You'll need:

- [**uv**](https://github.com/astral-sh/uv) — Python 3.12 venv + dependency manager
- [**Bun**](https://bun.sh) — runs the slide-preview helpers
- [**Quarto**](https://quarto.org/docs/get-started/) — renders the slides (only if you want to view them locally)
- A laptop with a microphone and speakers, or headphones — the local pipeline reads/writes audio

Apple silicon recommended for the open-source models. Anything M-series will work; the **Moshi** demo benefits from a beefier chip with at least ~16 GB free RAM for the bf16 weights.

### 2. Run the CLI demos

```bash
uv run voice
```

You'll get a Rich-based menu. Use **↑↓** to select, **⏎** to launch, **Esc** to come back to the menu.

Four demos:

| # | Demo | What it does |
|---|---|---|
| 1 | **Local pipeline** | [Pipecat](https://github.com/pipecat-ai/pipecat) orchestrating [Moonshine v2](https://github.com/moonshine-ai/moonshine) STT + [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) TTS + a small local LLM. All Apache 2.0 / permissive, all on your laptop, no cloud. |
| 2 | **Moshi (end-to-end)** | [Kyutai Moshi](https://github.com/kyutai-labs/moshi) — speech-native model that skips the STT+LLM+TTS pipeline. The "this is the future" demo. |
| 3 | **API comparison** | Same prompt through OpenAI Realtime API vs. the local pipeline. Hear the latency and quality side-by-side. Needs `OPENAI_API_KEY`. |
| 4 | **Emotion demo** | [Hume EVI 3](https://www.hume.ai) showing explicit emotion control. Needs `HUME_API_KEY`. |

> The CLI is being built out alongside the slides. If a demo says "not implemented yet," the speaker hasn't shipped it. Pull again before the talk.

### 3. View the slides locally (optional)

```bash
bun start          # live preview at localhost:[port], hot-reload on save
bun run render     # build slides.html + slides_files/ for static serving
```

Slides are written in [Quarto](https://quarto.org/docs/presentations/revealjs/) targeting Reveal.js, with a custom Gruvbox dark theme.

---

## API keys

A handful of demos hit hosted APIs. Set whichever you want to use in a `.env` at the repo root (Bun loads it automatically; the Python side loads it explicitly):

```sh
OPENAI_API_KEY=sk-...
HUME_API_KEY=...
```

Demos that don't need a key (local pipeline, Moshi) work offline. The API-comparison demo will skip its OpenAI half if no key is set.

---

## Repo layout

```
slides.qmd          ← deck source (Quarto + Reveal.js)
_quarto.yml         ← deck config
gruvbox.scss        ← custom dark theme
references.bib      ← bibliography for the paper section
assets/audio/       ← per-tool voice samples played from slides
assets/img/         ← screenshots, diagrams
voice/              ← Python CLI (the live demo, run with `uv run voice`)
pyproject.toml      ← Python deps via uv
package.json        ← `bun start` / `bun run render` / `bun run publish` helpers
```

---

## Talk reference links

- **Sesame paper** — *Crossing the Uncanny Valley of Conversational Voice* — [sesame.com/research/crossing_the_uncanny_valley_of_voice](https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice)
- **Sesame CSM code** — [github.com/SesameAILabs/csm](https://github.com/SesameAILabs/csm) (Apache 2.0)
- **Project Voice 2026** — [projectvoice.ai](https://www.projectvoice.ai)
- **Chattanooga AI Collective** — meetup group hosting the talk

---

## License

Code is MIT (see [`LICENSE`](./LICENSE)). Talk content (slide text, narration) is CC BY 4.0 — feel free to reuse with attribution.

The third-party models the demos use have their own licenses; check before shipping anything to production.

---

## Speaker

**John Gardner** ([@Sinjhin](https://github.com/Sinjhin)) — Chattanooga AI Collective.
