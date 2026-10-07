# Contributing to DayWright

Thank you for helping improve DayWright. This guide covers the project-specific boundaries that
apply in both the canonical workspace and the standalone public repository.

## Start here

- Read the [project README](README.md) for supported behavior, setup, architecture, privacy, and
  current evidence.
- Run commands from this project directory with Node.js 20 or newer and Python 3.12 or newer. The
  desktop app also needs Rust (stable) and Xcode's command-line tools.
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
- DayWright works offline but for one lookup: a website saved to the Library is fetched when a
  learning task is made from it and once more as that task starts, keeping only its title, its own
  description and its headings. Nothing else may go online: no search, upload, or remote model, and
  the Library holds only what the user writes, imports, connects or saves.
- Treat imported and retrieved content as untrusted reference material, never as instructions.

## Architecture boundaries

- SQLite remains the authority for management state. The vector index stores retrieval material;
  it does not become the source of truth for plans or outcomes.
- Keep chat generation, embeddings, and speech transcription as separate local model capabilities.
- Keep Orchestrator, Learning, Life, Work, Project, and Summary roles visible and bounded. Agents may
  propose or explain changes but must not claim unconfirmed state changes.
- Preserve explicit outcome reporting. Elapsed time alone does not prove completion.
- The desktop app's service answers only its own window, through the secret each launch creates,
  and the window loads nothing but its start screen and that service; other web addresses open in
  the browser. The app stops its service when it quits.

## Interface

- The interface follows the [Open Bench handoff](design/HANDOFF.md). Use the `--dw-*` variables
  from `design/tokens/tokens.css` and the icons in `design/icons/`; never hard-code a colour.
- Anything an agent proposes is dashed ("pencilled") and names its agent; nothing changes without
  the user's confirmation. Past days and other history are read-only and show a lock.
- Every interface string lives in `src/i18n.jsx`, in both English and Simplified Chinese.
- Use the shared controls: `src/ui/MenuSelect.jsx` for every dropdown, never a native `<select>` or
  time input, and the `dw-button` classes for every action, with `dw-icon-only` for an icon alone.

## Checks for a change

- Run `npm run build` for interface changes, and `npm run test:ui` for the interface helpers under
  `tests/`.
- Run `.venv12/bin/python -m unittest discover -s backend/tests` for backend behavior, or a focused
  module when only one bounded behavior changed.
- Begin every backend test module with `from backend.tests import isolation`, before anything from
  `backend.app`. It runs the tests on a temporary database and fails any test that reaches
  `backend/data/`, where local records live.
- Run `npm run test:sites` for static packaging changes.
- Run `npm run desktop` for changes to `src-tauri/`, the desktop service, or its build, then open the
  built app: it shows the start screen, then Today, and leaves no DayWright or model process after
  Quit.
- Visually inspect affected desktop and narrow layouts when information hierarchy or controls
  change. A passing build does not establish visual correctness.

<a id="version-and-build-policy"></a>

## Version and build policy

DayWright uses marketing versions and integer build numbers, starting at v1.0 build 10 on
2026-10-02; earlier records stay dated.

- A version reads `v<major>.<minor>`, with the minor running from 0 to 9: v1.9 is followed by
  v2.0, never v1.10. The build is major × 10 + minor, so v1.0 is build 10 and v1.1 is build 11.
- Every change except a documentation-only one advances both in the same working batch.
  Documentation-only corrections are recorded by date without a new number.
- The numbers live in `package.json` (`version`, such as `1.1.0`, which the Mac app reads),
  `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json` (`bundle > macOS > bundleVersion`, the
  build), and the service's version in `backend/app/main.py`. The README's release badge, its
  change history, and its current-release line name the same version and build.
- Never relabel a built or delivered app as a newer release; build the new number instead.
- A dependency, protocol, model, or Git commit version is not a DayWright project version.
- Keep implementation, tests, builds, local installation, deployment, and publication as separate
  evidence states.
- Do not describe uncommitted work or a prepared export as published.

The canonical workspace also applies its root repository instructions and internal procedures.
Those private files remain authoritative there; this standalone guide supplies the project-facing
rules that travel with the exported subtree.
