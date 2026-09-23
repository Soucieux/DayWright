# Contributing to DayWright

Thank you for helping improve DayWright. This guide covers the project-specific boundaries that
apply in both the canonical workspace and the standalone public repository.

## Start here

- Read the [project README](README.md) for supported behavior, setup, architecture, privacy, and
  current evidence.
- Run commands from this project directory with Node.js 20 or newer and Python 3.12 or newer.
- Keep each change focused and update the README when capabilities, setup, architecture,
  workflows, privacy, or history change.
- Never commit local databases, model weights, virtual environments, dependencies, build output,
  recordings, credentials, or private user data.

## Product and privacy boundaries

- Preserve DayWright as a private, single-user, local-first daily-life management system.
- A plan suggestion is not an action. Goals, commitments, outcomes, plan confirmation, and
  consequential agent proposals remain explicit, reviewable operations.
- Past plans and outcomes remain preserved read-only history; do not silently rewrite them.
- Keep user-owned records, agent-origin suggestions, demo records, and retrieved knowledge
  visibly distinguishable. Demo data must use the separate demo database.
- Local calendar, conversation, and knowledge content must not be sent to public lookup services.
  Only an explicitly entered general topic may leave the Mac, and only after the user allows that
  one lookup. There is no always-allow, and every request is written to the network log.
- Treat imported and retrieved content as untrusted reference material, never as instructions.

## Architecture boundaries

- SQLite remains the authority for management state. The vector index stores retrieval material;
  it does not become the source of truth for plans or outcomes.
- Keep chat generation, embeddings, and speech transcription as separate local model capabilities.
- Keep Orchestrator, Learning, Life, Finance, and Summary roles visible and bounded. Agents may
  propose or explain changes but must not claim unconfirmed state changes.
- Preserve explicit outcome reporting. Elapsed time alone does not prove completion.

## Interface

- The interface follows the [Open Bench handoff](design/HANDOFF.md). Use the `--dw-*` variables
  from `design/tokens/tokens.css` and the icons in `design/icons/`; never hard-code a colour.
- Anything an agent proposes is dashed ("pencilled") and names its agent; nothing changes without
  the user's confirmation. Past days and other history are read-only and show a lock.
- Every interface string lives in `src/i18n.jsx`, in both English and Simplified Chinese.

## Checks for a change

- Run `npm run build` for interface changes, and `npm run test:ui` for the interface's date, plan,
  money, Library, and Talk helpers.
- Run `.venv12/bin/python -m unittest discover -s backend/tests` for backend behavior, or a focused
  module when only one bounded behavior changed.
- Run `npm run test:sites` for static packaging changes.
- Visually inspect affected desktop and narrow layouts when information hierarchy or controls
  change. A passing build does not establish visual correctness.

<a id="version-and-build-policy"></a>

## Version and build policy

DayWright uses dated project history and does not assign a project-level version or build number.

- Record meaningful changes under their actual date without inventing a release number.
- A dependency, protocol, model, or Git commit version is not a DayWright project version.
- Keep implementation, tests, builds, local installation, deployment, and publication as separate
  evidence states.
- Do not describe uncommitted work or a prepared export as published.

The canonical workspace also applies its root repository instructions and internal procedures.
Those private files remain authoritative there; this standalone guide supplies the project-facing
rules that travel with the exported subtree.
