# Selection Markers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the live-select model (anchor + six Shift+arrow scripts) with two explicit markers modeled on NVDA+F9/F10, eliminating an entire class of selection edge cases.

**Architecture:** Two new instance variables (`selectionStart`, `selectionEnd`) hold `(line, char)` tuples; three new scripts (`set_selection_start`, `set_selection_end`, `clear_markers`) plus double-press detection on the end-marker key drive set/copy/clear. Old live-select scripts and helpers are removed. Auto-clear is centralized in `_load_current_note_lines`, which is reached by every note/folder transition.

**Tech Stack:** Python 3.11, NVDA Add-on API (`globalPluginHandler`, `scriptHandler`, `ui`, `api`, `characterProcessing`, `languageHandler`), SCons build, gettext translations, ruff lint.

---

## Spec Reference

Design spec: `docs/superpowers/specs/2026-05-11-selection-markers-design.md`. Re-read it if a task feels under-specified — every decision in this plan traces back there.

## File Structure

This redesign touches a single source file. The codebase deliberately keeps all add-on logic in one module.

- **Modified:** `addon/globalPlugins/invisinote/__init__.py` — all behavior changes.
- **Regenerated:** `addon/locale/messages.pot` — new translation msgids.

No new files. No directory restructure.

## Preflight (handle uncommitted changes)

The working tree currently has uncommitted improvements to the live-select scripts (boundary announcement and asymmetry fixes from earlier in the session). These touch the very code that Task 5 deletes. Before starting Task 1, do one of the following:

- **Preserve as historical baseline (recommended):**
  ```bash
  git add addon/globalPlugins/invisinote/__init__.py
  git commit -m "fix: live-select boundary announcements and asymmetry"
  ```
- **Discard:**
  ```bash
  git restore addon/globalPlugins/invisinote/__init__.py
  ```

Either choice is valid — Task 5 deletes the affected code regardless. Committing preserves the work in history.

---

## Task 1: Scaffolding + set-start marker

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py`

- [ ] **Step 1: Add `scriptHandler` import**

Locate the imports block at the top of the file. Add `import scriptHandler` alongside the existing imports (after `import characterProcessing` and `import languageHandler`). Final imports section:

```python
import re
import os
import ui
import api
import wx
import gui
import subprocess
import globalPluginHandler
import characterProcessing
import languageHandler
import scriptHandler
from scriptHandler import script
```

- [ ] **Step 2: Initialize marker state in `__init__`**

Find the `__init__` method of `GlobalPlugin`. Locate the existing line `self.selectionAnchor = None` and add the two new state vars on the lines directly below it:

```python
self.selectionAnchor = None
self.selectionStart = None
self.selectionEnd = None
```

- [ ] **Step 3: Add `_selection_text` helper method**

Add this method to `GlobalPlugin` next to the existing selection helpers (e.g., directly after `_selection_extending`):

```python
def _selection_text(self):
    if self.selectionStart is None or self.selectionEnd is None:
        return None
    if self.selectionStart <= self.selectionEnd:
        startLine, startChar = self.selectionStart
        endLine, endChar = self.selectionEnd
    else:
        startLine, startChar = self.selectionEnd
        endLine, endChar = self.selectionStart
    if startLine == endLine:
        return self.currentNoteLines[startLine].rstrip("\n")[startChar:endChar + 1]
    parts = [self.currentNoteLines[startLine][startChar:]]
    for i in range(startLine + 1, endLine):
        parts.append(self.currentNoteLines[i])
    parts.append(self.currentNoteLines[endLine].rstrip("\n")[:endChar + 1])
    return "".join(parts)
```

Note the `endChar + 1` slices — this is the inclusive-range semantic from the spec.

- [ ] **Step 4: Add `script_set_selection_start` method**

Add this script method to `GlobalPlugin`, grouped with the other selection scripts (e.g., directly before the existing `script_select_previous_line`):

```python
@script(description=_("Set selection start"))
def script_set_selection_start(self, gesture):
    if not self.currentNoteLines:
        ui.message(_("No notes"))
        return
    self.selectionStart = (self.currentLineIndex, self.currentCharIndex)
    line = self._current_line()
    if line and self.currentCharIndex < len(line):
        char = characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), line[self.currentCharIndex])
    else:
        char = _("blank")
    ui.message(_("selection start: ") + char)
```

- [ ] **Step 5: Bind NVDA+ALT+F9 in the `__gestures` dict**

Add this entry to `__gestures` at the bottom of the class (place it near the existing selection gestures):

```python
"kb:NVDA+ALT+F9": "set_selection_start",
```

- [ ] **Step 6: Lint**

Run: `ruff check addon/globalPlugins/invisinote/__init__.py`
Expected: no errors. (If `ruff` is not installed: `pip install ruff` first.)

- [ ] **Step 7: Commit**

```bash
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "feat: add selection start marker (NVDA+ALT+F9)"
```

---

## Task 2: Set-end marker + copy via double-press

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py`

- [ ] **Step 1: Add `script_set_selection_end` method**

Add this script method immediately after `script_set_selection_start`:

```python
@script(description=_("Set selection end, double-press to copy"))
def script_set_selection_end(self, gesture):
    if not self.currentNoteLines:
        ui.message(_("No notes"))
        return
    if scriptHandler.getLastScriptRepeatCount() == 0:
        self.selectionEnd = (self.currentLineIndex, self.currentCharIndex)
        line = self._current_line()
        if line and self.currentCharIndex < len(line):
            char = characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), line[self.currentCharIndex])
        else:
            char = _("blank")
        ui.message(_("selection end: ") + char)
    else:
        text = self._selection_text()
        if text is None:
            ui.message(_("no selection"))
        else:
            api.copyToClip(text)
            ui.message(_("selection copied"))
```

- [ ] **Step 2: Bind NVDA+ALT+F10**

Add to `__gestures`:

```python
"kb:NVDA+ALT+F10": "set_selection_end",
```

- [ ] **Step 3: Lint**

Run: `ruff check addon/globalPlugins/invisinote/__init__.py`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "feat: add selection end marker with double-press copy (NVDA+ALT+F10)"
```

---

## Task 3: Clear-markers gesture

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py`

- [ ] **Step 1: Add `script_clear_markers` method**

Add this script method immediately after `script_set_selection_end`:

```python
@script(description=_("Clear selection markers"))
def script_clear_markers(self, gesture):
    self.selectionStart = None
    self.selectionEnd = None
    ui.message(_("selection cleared"))
```

- [ ] **Step 2: Bind NVDA+BACKSPACE**

Add to `__gestures`:

```python
"kb:NVDA+BACKSPACE": "clear_markers",
```

- [ ] **Step 3: Lint**

Run: `ruff check addon/globalPlugins/invisinote/__init__.py`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "feat: add clear selection markers gesture (NVDA+BACKSPACE)"
```

---

## Task 4: Auto-clear markers on note/folder switch

The hook lives in `_load_current_note_lines` (reached by note nav, folder nav, and reload) and in `_load_notes`' no-notes branch. Add marker resets to both places, keeping `selectionAnchor` resets in place for now (Task 6 removes them).

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py`

- [ ] **Step 1: Update `_load_current_note_lines`**

Find the method. The current first line of the body is `self.selectionAnchor = None`. Add the two marker resets directly after:

Before:
```python
def _load_current_note_lines(self):
    self.selectionAnchor = None
    if self.notes:
```

After:
```python
def _load_current_note_lines(self):
    self.selectionAnchor = None
    self.selectionStart = None
    self.selectionEnd = None
    if self.notes:
```

- [ ] **Step 2: Update `_load_notes` no-notes branch**

Find the no-notes branch of `_load_notes`. It currently resets state with `self.selectionAnchor = None` as the last reset before `return _("No notes")`. Add the marker resets:

Before:
```python
self.currentNoteIndex = 0
self.currentNoteLines = []
self.currentLineIndex = 0
self.currentWordIndex = 0
self.currentCharIndex = 0
self.selectionAnchor = None
return _("No notes")
```

After:
```python
self.currentNoteIndex = 0
self.currentNoteLines = []
self.currentLineIndex = 0
self.currentWordIndex = 0
self.currentCharIndex = 0
self.selectionAnchor = None
self.selectionStart = None
self.selectionEnd = None
return _("No notes")
```

- [ ] **Step 3: Lint**

Run: `ruff check addon/globalPlugins/invisinote/__init__.py`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "feat: auto-clear selection markers on note/folder switch"
```

---

## Task 5: Remove old live-select scripts and helpers

After this task, the live-select model is gone. All eight Shift+arrow / Shift+`;` / Alt+BACKSPACE bindings are unbound; the helpers that supported them are deleted.

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py`

- [ ] **Step 1: Remove the eight old gesture bindings**

In the `__gestures` dict at the bottom of the class, remove these eight entries:

```python
"kb:NVDA+ALT+SHIFT+I": "select_previous_line",
"kb:NVDA+ALT+SHIFT+K": "select_next_line",
"kb:NVDA+ALT+SHIFT+J": "select_previous_word",
"kb:NVDA+ALT+SHIFT+L": "select_next_word",
"kb:NVDA+ALT+SHIFT+,": "select_previous_character",
"kb:NVDA+ALT+SHIFT+.": "select_next_character",
"kb:NVDA+ALT+SHIFT+;": "copy_selection",
"kb:NVDA+ALT+BACKSPACE": "clear_selection",
```

- [ ] **Step 2: Delete the eight old scripts**

Delete the entire method body (including `@script(...)` decorator) for each of these eight scripts:

- `script_select_next_line`
- `script_select_previous_line`
- `script_select_next_word`
- `script_select_previous_word`
- `script_select_next_character`
- `script_select_previous_character`
- `script_copy_selection`
- `script_clear_selection`

- [ ] **Step 3: Delete the four now-unused helpers**

Delete these methods from `GlobalPlugin`:

- `_start_selection_if_needed`
- `_selection_extending`
- `_abs_offset`
- `_get_selected_text`

- [ ] **Step 4: Lint**

Run: `ruff check addon/globalPlugins/invisinote/__init__.py`
Expected: no errors. If ruff flags any newly-unused imports (it should not — all imports remain in use by other scripts), remove them.

- [ ] **Step 5: Commit**

```bash
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "refactor: remove old live-select scripts and helpers"
```

---

## Task 6: Remove `selectionAnchor`

With the live-select scripts gone, `selectionAnchor` is dead state. Remove it from `__init__`, the auto-clear hook, and all six navigation scripts that reset it.

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py`

- [ ] **Step 1: Remove `selectionAnchor` from `__init__`**

In the `__init__` method of `GlobalPlugin`, delete the line:

```python
self.selectionAnchor = None
```

(Leave the new `self.selectionStart = None` and `self.selectionEnd = None` lines that follow it.)

- [ ] **Step 2: Remove `selectionAnchor = None` from `_load_current_note_lines`**

Delete the line `self.selectionAnchor = None` from `_load_current_note_lines`. The two marker resets added in Task 4 remain.

- [ ] **Step 3: Remove `selectionAnchor = None` from `_load_notes` no-notes branch**

Delete the line `self.selectionAnchor = None` from the no-notes branch of `_load_notes`. The two marker resets remain.

- [ ] **Step 4: Remove `selectionAnchor = None` from navigation scripts**

In each of the six navigation scripts below, delete the `self.selectionAnchor = None` line at the top of the method body:

- `script_next_line`
- `script_previous_line`
- `script_next_word`
- `script_previous_word`
- `script_next_character`
- `script_previous_character`

- [ ] **Step 5: Verify no remaining references**

Search the file for `selectionAnchor`. Expected: no matches. If any remain, remove them.

Run: `ruff check addon/globalPlugins/invisinote/__init__.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "refactor: remove obsolete selectionAnchor state"
```

---

## Task 7: Regenerate translation template

**Files:**
- Modify: `addon/locale/messages.pot` (auto-generated)

- [ ] **Step 1: Regenerate the `.pot` file**

Run: `scons pot`
Expected: the build prints actions for `addon/locale/messages.pot`; the file is updated on disk.

(If SCons or gettext are not installed, see the project's CLAUDE.md "Build" section for setup.)

- [ ] **Step 2: Verify new msgids appear in the template**

Open `addon/locale/messages.pot` and confirm these msgids are present (search for each string):

- `msgid "selection start: "`
- `msgid "selection end: "`
- `msgid "selection copied"`
- `msgid "selection cleared"`
- `msgid "no selection"`

Also confirm the old select-script msgids (`"Select to next line"`, `"Select to previous word"`, etc.) are **gone**.

- [ ] **Step 3: Commit**

```bash
git add addon/locale/messages.pot
git commit -m "i18n: regenerate translation template for selection markers"
```

(Note: existing `addon/locale/<lang>/LC_MESSAGES/nvda.po` translation files are not updated by this task. New strings will fall back to English in translated locales until those `.po` files are updated separately.)

---

## Task 8: Manual verification in NVDA

No automated test framework exists in this repo. This task runs the manual test plan from the design spec against a real NVDA installation.

**Files:** none (testing only)

- [ ] **Step 1: Build the addon**

Run: `scons`
Expected: `invisinote-<version>.nvda-addon` is created in the repo root.

- [ ] **Step 2: Install the build in NVDA**

In NVDA: Tools → Manage add-ons → Install from file → select the `.nvda-addon` from step 1. Restart NVDA when prompted.

- [ ] **Step 3: Test "set start" announces the cursor character**

Open a note with multi-character content (use `NVDA+ALT+N` to load, `NVDA+ALT+O` to navigate to a note). Position the cursor on a known character with `NVDA+ALT+,` / `NVDA+ALT+.`. Press `NVDA+ALT+F9`.
Expected: announces `selection start: <that character>`.

- [ ] **Step 4: Test "set end" announces the cursor character**

After step 3, navigate forward a few characters with `NVDA+ALT+.`. Press `NVDA+ALT+F10` (single press).
Expected: announces `selection end: <that character>`.

- [ ] **Step 5: Test double-press copies inclusively**

After step 4, immediately press `NVDA+ALT+F10` again (the second press completing the double-press).
Expected: announces `selection copied`. Open Notepad or any text field, press Ctrl+V. The pasted text includes **both** the start and end characters.

- [ ] **Step 6: Test clear-markers**

Press `NVDA+BACKSPACE`.
Expected: announces `selection cleared`. Pressing `NVDA+ALT+F10` twice afterward announces `no selection` (clipboard untouched).

- [ ] **Step 7: Test "no selection" when only one marker is set**

Clear markers (`NVDA+BACKSPACE`). Press `NVDA+ALT+F9` (start only). Press `NVDA+ALT+F10` twice quickly.
Expected: the first F10 press sets end and announces; the second triggers copy. Since both markers are now set, this actually copies. To test "no selection," do: clear markers, then press `NVDA+ALT+F10` twice quickly *without* ever pressing F9. The first press sets end; the second tries to copy with no start → announces `no selection`.

- [ ] **Step 8: Test auto-clear on note switch**

Set both markers in note A. Press `NVDA+ALT+O` to navigate to a different note. Press `NVDA+ALT+F10` twice.
Expected: announces `no selection` — markers were cleared by the note switch.

- [ ] **Step 9: Test reverse-order markers auto-normalize**

In a note with at least 5 lines, navigate to line 5, press `NVDA+ALT+F9` (start). Navigate up to line 3 with `NVDA+ALT+I`, press `NVDA+ALT+F10` (end at line 3). Double-press F10 to copy.
Expected: announces `selection copied`. Pasted text covers from line 3 through line 5 in document order.

- [ ] **Step 10: Test empty-line marker**

Navigate to an empty line in a note (or temporarily edit one to be empty). Press `NVDA+ALT+F9`.
Expected: announces `selection start: blank`.

- [ ] **Step 11: Test markers don't drift during navigation**

Set start at a known character. Navigate freely with line/word/char gestures. Note that the announced character on each move is the cursor position, not the marker. Eventually press `NVDA+ALT+F10` at a new location, then double-press F10.
Expected: the copied text reflects the original start position, not wherever the cursor wandered.

- [ ] **Step 12: Test no double-press behavior on F9**

Press `NVDA+ALT+F9` twice rapidly.
Expected: announces `selection start: <char>` both times. No copy occurs. Pressing F9 only re-sets start.

- [ ] **Step 13: If any test fails**

Note which step failed and the actual vs. expected behavior. Return to the relevant task in this plan and revise.

---

## Self-Review

**Spec coverage:**

- Gestures table (spec §"Gestures"): Task 1 binds F9, Task 2 binds F10 with double-press, Task 3 binds BACKSPACE. ✓
- Announcements table (spec §"Announcements"): Task 1 announces set-start; Task 2 announces set-end and copy variants; Task 3 announces clear. ✓
- Overwrite semantics (spec): set-marker scripts unconditionally write — verified in Tasks 1, 2. ✓
- Auto-clear (spec §"Auto-clear"): Task 4 hooks `_load_current_note_lines` and the no-notes branch. ✓
- Inclusive range (spec §"Range semantics"): `_selection_text` uses `endChar + 1` slicing in Task 1, Step 3. ✓
- State (spec §"State"): Task 1 adds both new state vars; Task 6 removes `selectionAnchor`. ✓
- Removals (spec §"Removed"): Task 5 deletes 8 scripts + 4 helpers + 8 gesture bindings; Task 6 removes the variable and all writes. ✓
- Translation strings (spec §"Translation strings"): Task 7 regenerates `.pot`; verification step lists each new msgid. ✓
- Manual test plan (spec §"Testing"): all 9 spec scenarios mapped to Task 8 steps 3–11 (plus extra coverage for double-F9 and only-end-set). ✓

**Placeholders:** none.

**Type/name consistency:** `selectionStart` / `selectionEnd` (camelCase, matching `selectionAnchor` style); `_selection_text` (snake_case, matching `_get_selected_text` style); `script_set_selection_start` / `script_set_selection_end` / `script_clear_markers` (consistent naming, all bound in `__gestures`). All match across tasks.

No fixes needed.

---

## Out of Scope (from spec)

These are not addressed by this plan:

- Per-note marker persistence.
- Visual or screen-reader indicator outside the at-set-time announcement.
- A query gesture ("where is the start marker?").
- A read-selection-aloud gesture.
- Changes to existing `copy_note` / `copy_line` behavior.
