# mini-agent

A from-scratch, teaching-scale coding agent: Model boundary + Tool boundary + a bounded
Agent Loop. No streaming, no TUI, no Skills/MCP, no Hooks, no approval system, no pytest
suite -- built and verified by running it against a real task each step of the way.

Built in four incremental batches, each its own commit:

1. `settings.py` + `main.py` skeleton -- project scaffolding, given as-is.
2. `model.py` -- the Model boundary: one non-streaming request, wire format <-> trusted types.
3. `tools.py` -- the Tool boundary: registry, dispatcher, three builtin tools.
4. `agent.py` -- the bounded Agent Loop tying the two boundaries together.

## Setup

```bash
cp .env.example .env   # fill in your course PHI_BASE_URL / PHI_API_KEY / PHI_DEFAULT_MODEL
uv sync
```

## Run

```bash
uv run main.py "read main.py and tell me what this project does"
```

## What this deliberately is not

This is not a trimmed-down copy of `phi` -- it's a much smaller sibling built to prove out
one specific idea: hand-write only the essential wire-boundary and control-loop logic live,
in a few hours, then read the real `phi` reference to see what a production-grade version
adds on top (streaming, cancellation safety, Hooks, typed Events, approval, MCP, sessions, ...)
and why.
