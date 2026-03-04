# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Invisinote is an NVDA screen reader add-on (Python) that lets users virtually browse plain-text notes from configured folders without leaving the current application. All navigation happens in-memory via keyboard gestures.

## Build

Dependencies: Python 3.11, `scons`, `markdown`, `pre-commit`, `gettext` (system package on Linux).

```bash
# Install Python deps
pip install scons markdown pre-commit

# Build the .nvda-addon package
scons

# Build the .pot translation template
scons pot
```

The output is `invisinote-<version>.nvda-addon` (a ZIP file) in the repo root.

## Lint

```bash
# Run all pre-commit checks (includes ruff via pyproject.toml)
pre-commit run --all

# Lint only (ruff must be installed separately)
ruff check .
ruff format .
```

Code style: tabs for indentation, max line length 110. The `_`, `ngettext`, `pgettext`, `npgettext` builtins are available for translations — never import them.

## Architecture

The entire add-on logic lives in a single file: `addon/globalPlugins/invisinote/__init__.py`.

- **`GlobalPlugin`** — the NVDA global plugin class. Maintains all navigation state (current folder, note index, line/word/char position, selection anchor) as instance variables. Loads paths from `addon/globalPlugins/paths.txt` and file types from `addon/globalPlugins/filetypes.txt` at startup.
- **`SettingsDialog`** — a `wx.Dialog` for configuring watched folders and file extensions. Opened via `NVDA+ALT+SHIFT+P`.
- Scripts are plain methods prefixed `script_` and decorated with `@script(description=_(...))`. They are bound to gestures in the `__gestures` dict at the bottom of the class.
- Navigation state reset rules: moving to a new note resets all sub-note state; moving lines resets char/word index; selection anchor is cleared on any non-selection movement.

**Key files:**
- `buildVars.py` — version, author, supported NVDA versions, add-on metadata. Update `addon_version` here when releasing.
- `manifest.ini.tpl` / `manifest-translated.ini.tpl` — NVDA manifest templates filled by SCons from `buildVars.py`.
- `addon/locale/` — gettext `.po`/`.mo` translation files per language (e.g. `zh_TW`).
- `addon/doc/` — documentation markdown converted to HTML at build time.
- `sconstruct` — SCons build script (Python); handles manifest generation, gettext compilation, markdown→HTML, and ZIP packaging.

## Translations

All user-visible strings must be wrapped in `_()`. To add a new language, create `addon/locale/<lang>/LC_MESSAGES/nvda.po` and compile with `scons` (SCons runs `msgfmt` automatically).

## User constrain
Do not rewrite git history.