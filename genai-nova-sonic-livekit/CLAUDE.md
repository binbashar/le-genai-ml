# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Minimal POC for real-time voice interaction with Amazon Nova Sonic 2 using WebRTC via LiveKit. Default language is Brazilian Portuguese (pt-BR) with the `leo` native voice.

**Architecture:**
```
Browser (Chrome)  <--WebRTC-->  LiveKit Server  <--Room-->  Python Agent  <--Bedrock-->  Nova Sonic 2
```

**Model ID:** `amazon.nova-2-sonic-v1:0`

## Build & Run Commands

Uses [just](https://github.com/casey/just) as task runner. Run `just --list` to see all recipes.

```bash
just install-livekit          # One-time: install LiveKit via Homebrew
just install                  # Install Python deps with uv
just patch-voices             # Enable native pt-BR voices (leo, carolina)
just profile=YOUR_PROFILE start   # Start everything, opens browser automatically
just stop                     # Kill all processes
```

## Code Quality

**Always run Black 23.3.0 before committing or pushing:**
```bash
uvx --python 3.12 black==23.3.0 genai-nova-sonic-livekit/
```

The repo CI runs `black==23.3.0 --check` on all Python files. Using a different Black version produces incompatible formatting. Ensure your code passes before pushing.

## Key Files

- `agent.py` — LiveKit agent bridging audio to Nova Sonic 2 via `livekit-plugins-aws`
- `justfile` — Task runner with all automation recipes
- `web/index.html` — Vanilla JS frontend (no build step)
- `pyproject.toml` — Dependencies managed with `uv`
