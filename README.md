# mini-agent

A from-scratch, teaching-scale coding agent: Model boundary + Tool boundary + a bounded
Agent Loop. No streaming, no TUI, no Skills/MCP, no Hooks, no approval system, no pytest
suite -- you build it and verify it works by running it against a real task.

## What's here

- `settings.py`, `main.py` -- given as-is. Environment config and CLI argument parsing
  aren't the lesson.
- `model.py`, `tools.py`, `agent.py` -- your job. Every type, function signature, and
  docstring is already there; every function body is a `TODO` comment plus
  `raise NotImplementedError`. Fill them in, in that order:

  1. `model.py` -- convert one real, non-streaming model request into trusted internal
     types (`ToolCall`, `ModelResponse`), with everything the wire format can throw at
     you turned into a clear `ModelError`.
  2. `tools.py` -- a `ToolRegistry` and a `dispatch()` that cleanly tells apart an
     unknown tool, invalid arguments, and a handler that blew up -- plus three real
     tools (`read_file`, `list_files`, `edit_file`).
  3. `agent.py` -- the bounded loop that ties the two together.

`main.py` already calls into all three. Until you've implemented them, running it just
tells you exactly that:

```bash
uv run main.py "say hi"
# ... NotImplementedError
```

That error moving from `agent.py` to `tools.py` to gone is your actual progress bar.

## Setup

```bash
cp .env.example .env   # fill in your course PHI_BASE_URL / PHI_API_KEY / PHI_DEFAULT_MODEL
uv sync
```

## Verifying your work

There's no test suite here on purpose. As you finish each file, run the matching
check script -- `uv run scripts/check_model.py` after `model.py`, `uv run
scripts/check_tools.py` after `tools.py` -- to check that one piece in isolation
before wiring it into the full loop. These are given as-is, same as `main.py`.

Once `agent.py` is done, run it against a real task and watch what happens:

```bash
uv run main.py "read main.py and tell me what this project does"
```

If it reads the file and gives you a sensible answer, that step works. If it hangs,
crashes, or gives back nonsense, that's your signal to go look at what actually
happened, not a red X in a test report.

## About the `reference` branch

This repository has a `reference` branch with a complete, working implementation --
built the same way you're about to build yours, one piece at a time, each step verified
against the real course proxy.

**Don't read it before you've made your own attempt.** It's there for after: once
you've got your own `model.py`/`tools.py`/`agent.py` working (or you're genuinely stuck
and have tried for a while), diff your files against it. That comparison -- what did I
do differently, and does the difference matter -- is worth far more than typing out
someone else's answer would be. Copying it in before you've tried just means you'll be
reading real Phi's source later without ever having felt the problems it's solving.

## What this deliberately is not

This is not a trimmed-down copy of `phi` -- it's a much smaller sibling built to prove
out one specific idea: hand-write only the essential wire-boundary and control-loop
logic yourself, in a few hours, then read the real `phi` reference to see what a
production-grade version adds on top (streaming, cancellation safety, Hooks, typed
Events, approval, MCP, sessions, ...) and why.
