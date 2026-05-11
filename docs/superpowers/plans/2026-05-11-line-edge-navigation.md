# Line-edge navigation and edge-message context — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `NVDA+ALT+H` (start of line) and `NVDA+ALT+'` (end of line) gestures to invisinote, and append the current note/folder name to the four "no previous / no next" boundary messages.

**Architecture:** All changes are localised to the single `GlobalPlugin` class in `addon/globalPlugins/invisinote/__init__.py`. Two new `@script`-decorated methods are added next to the existing per-character navigation scripts and registered in the `__gestures` dict. Four existing message strings are updated to interpolate the current note/folder name via `.format(...)`. The `script_previous_note` / `script_next_note` paths guard against an empty `self.notes` list so the name lookup never raises `IndexError`.

**Tech Stack:** Python 3.11, NVDA add-on API (`@script`, `ui.message`, `characterProcessing`, `languageHandler`), SCons build (`scons` produces `invisinote-<version>.nvda-addon`), gettext (`_()` wrapping), ruff for lint/format.

**Spec:** `docs/superpowers/specs/2026-05-11-line-edge-navigation-design.md`

**Testing note:** The repo has no automated test harness — NVDA add-ons are exercised through NVDA's speech/gesture pipeline. Each task therefore uses a manual NVDA verification step in place of the usual unit-test cycle. The verification is split across two phases: a "baseline" check before the edit (confirms the *current* behaviour you're about to change) and a "verify" check after the edit (confirms the new behaviour). Each task ends with `ruff` and a commit.

**Setup once before starting any task** (not repeated per task):

1. Have a target invisinote folder configured (the default `addon/globalPlugins/notes/` is fine) containing at least two `.txt` notes, one of which has more than one non-empty line. A second configured folder is needed for the folder-boundary tests in Task 4.
2. Know how to rebuild and reload the add-on:

```powershell
scons
```

Then in NVDA: **Tools → Manage add-ons → Install from file** → pick `invisinote-<version>.nvda-addon` and restart NVDA. You will repeat this rebuild/reload at the verification step of each task.

---

## File Structure

Only one source file changes across this plan:

- **Modify** `addon/globalPlugins/invisinote/__init__.py`
  - Task 1 inserts `script_start_of_line` after line 362 (i.e. immediately after `script_previous_character`) and a `kb:NVDA+ALT+H` entry in the `__gestures` dict.
  - Task 2 inserts `script_end_of_line` after `script_start_of_line` (added in Task 1) and a `kb:NVDA+ALT+'` entry in the `__gestures` dict.
  - Task 3 modifies the `else` branches of `script_previous_note` (line 318) and `script_next_note` (line 309).
  - Task 4 modifies the `else` branches of `script_previous_folder` (line 272) and `script_next_folder` (line 282).

One spec file (`docs/superpowers/specs/2026-05-11-line-edge-navigation-design.md`) is referenced but not modified.

No new files. No test files (no test harness in this repo).

---

### Task 1: Add `script_start_of_line` and bind `NVDA+ALT+H`

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py` (insert method after `script_previous_character` ending on line 362; add binding in `__gestures` dict near line 439)

- [ ] **Step 1: Baseline check — confirm `NVDA+ALT+H` does nothing today**

Build and install the *current* (pre-change) add-on so the baseline reflects what is checked in:

```powershell
scons
```

Install the resulting `invisinote-<version>.nvda-addon` via **NVDA → Tools → Manage add-ons → Install from file** and restart NVDA when prompted.

Open one of the configured notes, move into a line with several characters, and press `NVDA+ALT+H`. Expected: nothing happens — no announcement, the char index does not move. This confirms the gesture is unbound before the edit.

- [ ] **Step 2: Add the script**

In `addon/globalPlugins/invisinote/__init__.py`, immediately after `script_previous_character` (the method ending on line 362), insert:

```python
	@script(description=_("Move to start of line"))
	def script_start_of_line(self, gesture):
		line = self._current_line()
		self.currentCharIndex = 0
		self._update_word_index_from_char()
		if line:
			char = line[self.currentCharIndex]
			ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), char))
```

Note: indentation is a single tab (the file uses tabs — see `pyproject.toml` / `CLAUDE.md`).

- [ ] **Step 3: Bind the gesture**

In the `__gestures` dict at the bottom of the class, add the following entry on its own line, immediately after the `"kb:NVDA+ALT+.": "next_character",` line:

```python
		"kb:NVDA+ALT+H": "start_of_line",
```

- [ ] **Step 4: Lint and format**

Run:

```powershell
ruff check addon/globalPlugins/invisinote/__init__.py
ruff format addon/globalPlugins/invisinote/__init__.py
```

Expected: both commands exit 0 with no reported issues. If `ruff format` rewrites the file, re-run `ruff check` to confirm clean.

- [ ] **Step 5: Verify — manual NVDA test**

Rebuild and reinstall the add-on (same procedure as Step 1, then restart NVDA):

```powershell
scons
```

Open a note, place the cursor mid-line (press `NVDA+ALT+.` a few times so the char index is > 0), then press `NVDA+ALT+H`. Expected: NVDA announces the first character of the line (e.g. "H" if the line is "Hello world"). Press `NVDA+ALT+.` once: expected to advance to the second character ("e") — confirms the char index was reset to 0.

Move to an empty line (press `NVDA+ALT+K` until you land on one if your notes contain blank lines, or add a blank line to a note for the test). Press `NVDA+ALT+H`. Expected: silent (no announcement) — confirms the empty-line guard.

- [ ] **Step 6: Commit**

```powershell
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "feat: add NVDA+ALT+H to move to start of line"
```

---

### Task 2: Add `script_end_of_line` and bind `NVDA+ALT+'`

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py` (insert method immediately after `script_start_of_line` added in Task 1; add binding in `__gestures` dict)

- [ ] **Step 1: Baseline check — confirm `NVDA+ALT+'` does nothing today**

The Task 1 build is already installed; no rebuild needed. Open a note, place the cursor mid-line, and press `NVDA+ALT+'`. Expected: nothing happens. This confirms the gesture is unbound before this task's edit.

- [ ] **Step 2: Add the script**

In `addon/globalPlugins/invisinote/__init__.py`, immediately after `script_start_of_line` (the method added in Task 1), insert:

```python
	@script(description=_("Move to end of line"))
	def script_end_of_line(self, gesture):
		line = self._current_line()
		self.currentCharIndex = max(0, len(line) - 1)
		self._update_word_index_from_char()
		if line:
			char = line[self.currentCharIndex]
			ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), char))
```

Indentation is a single tab.

- [ ] **Step 3: Bind the gesture**

In the `__gestures` dict, add the following entry on its own line immediately after the `"kb:NVDA+ALT+H": "start_of_line",` line added in Task 1:

```python
		"kb:NVDA+ALT+'": "end_of_line",
```

- [ ] **Step 4: Lint and format**

Run:

```powershell
ruff check addon/globalPlugins/invisinote/__init__.py
ruff format addon/globalPlugins/invisinote/__init__.py
```

Expected: both commands exit 0.

- [ ] **Step 5: Verify — manual NVDA test**

Rebuild and reinstall:

```powershell
scons
```

Restart NVDA. Open a note, place the cursor at the start of a line (`NVDA+ALT+H`), then press `NVDA+ALT+'`. Expected: NVDA announces the last character of the line (e.g. "d" if the line is "Hello world"). Press `NVDA+ALT+.` once: expected to re-announce the same last character ("d") — `script_next_character` re-emits the char at the current index even when it does not advance, so the clamp in `script_next_character` at line 345 holding `currentCharIndex` at `len(line) - 1` is confirmed by the announcement being identical, not by silence. Press `NVDA+ALT+,` once: expected to step back to the second-to-last character ("l").

Move to an empty line and press `NVDA+ALT+'`. Expected: silent.

- [ ] **Step 6: Commit**

```powershell
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "feat: add NVDA+ALT+' to move to end of line"
```

---

### Task 3: Add note name to "no previous note" / "no next note" messages

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py` — the `else` branches of `script_next_note` (line 309) and `script_previous_note` (line 318)

- [ ] **Step 1: Baseline check — confirm the bare message today**

Build and install (the Task 2 build already has this baseline behaviour for these messages — no rebuild needed if it's still installed). In a folder containing at least two notes, press `NVDA+ALT+N` to load notes, then press `NVDA+ALT+U` (previous note) repeatedly until you hit the first note and press it once more. Expected: NVDA announces exactly `"No previous note"` — no name appended. Press `NVDA+ALT+O` (next note) repeatedly past the last note. Expected: exactly `"No next note"`.

- [ ] **Step 2: Modify `script_next_note`**

The current method (around line 302–309) reads:

```python
	@script(description=_("Move to next note"))
	def script_next_note(self, gesture):
		if self.notes and self.currentNoteIndex < len(self.notes) - 1:
			self.currentNoteIndex += 1
			self._load_current_note_lines()
			ui.message(os.path.basename(self.notes[self.currentNoteIndex]))
		else:
			ui.message(_("No next note"))
```

Replace the `else` branch so that, when there is a current note, its filename is appended:

```python
	@script(description=_("Move to next note"))
	def script_next_note(self, gesture):
		if self.notes and self.currentNoteIndex < len(self.notes) - 1:
			self.currentNoteIndex += 1
			self._load_current_note_lines()
			ui.message(os.path.basename(self.notes[self.currentNoteIndex]))
		elif self.notes:
			ui.message(_("No next note, {}").format(os.path.basename(self.notes[self.currentNoteIndex])))
		else:
			ui.message(_("No next note"))
```

- [ ] **Step 3: Modify `script_previous_note`**

The current method (around line 311–318) reads:

```python
	@script(description=_("Move to previous note"))
	def script_previous_note(self, gesture):
		if self.notes and self.currentNoteIndex > 0:
			self.currentNoteIndex -= 1
			self._load_current_note_lines()
			ui.message(os.path.basename(self.notes[self.currentNoteIndex]))
		else:
			ui.message(_("No previous note"))
```

Replace the `else` branch the same way:

```python
	@script(description=_("Move to previous note"))
	def script_previous_note(self, gesture):
		if self.notes and self.currentNoteIndex > 0:
			self.currentNoteIndex -= 1
			self._load_current_note_lines()
			ui.message(os.path.basename(self.notes[self.currentNoteIndex]))
		elif self.notes:
			ui.message(_("No previous note, {}").format(os.path.basename(self.notes[self.currentNoteIndex])))
		else:
			ui.message(_("No previous note"))
```

- [ ] **Step 4: Lint and format**

Run:

```powershell
ruff check addon/globalPlugins/invisinote/__init__.py
ruff format addon/globalPlugins/invisinote/__init__.py
```

Expected: both commands exit 0.

- [ ] **Step 5: Verify — manual NVDA test**

Rebuild and reinstall:

```powershell
scons
```

Restart NVDA. In a folder containing at least two notes:

1. Press `NVDA+ALT+N` to load notes. NVDA announces the count.
2. Press `NVDA+ALT+U` repeatedly until you reach the first note (NVDA announces each filename you land on). Press `NVDA+ALT+U` once more. Expected: `"No previous note, <first-note-filename>"` (e.g. `"No previous note, alpha.txt"`).
3. Press `NVDA+ALT+O` repeatedly until you reach the last note. Press `NVDA+ALT+O` once more. Expected: `"No next note, <last-note-filename>"`.

Then test the empty-folder fallback. Temporarily configure (via `NVDA+ALT+SHIFT+P`) an empty folder, or remove all notes from a configured folder. Switch to that folder (`NVDA+ALT+[` / `NVDA+ALT+]`), press `NVDA+ALT+N`. Expected: `"No notes"`. Press `NVDA+ALT+U`. Expected: bare `"No previous note"` with no comma and no name (this confirms the `else` fallback fires when `self.notes` is empty and no `IndexError` is raised). Press `NVDA+ALT+O`. Expected: bare `"No next note"`.

- [ ] **Step 6: Commit**

```powershell
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "feat: append current note name to edge messages"
```

---

### Task 4: Add folder name to "no previous folder" / "no next folder" messages

**Files:**
- Modify: `addon/globalPlugins/invisinote/__init__.py` — the `else` branches of `script_previous_folder` (line 272) and `script_next_folder` (line 282)

- [ ] **Step 1: Baseline check — confirm the bare message today**

Ensure at least two folders are configured (use `NVDA+ALT+SHIFT+P` to add a second one if needed). Press `NVDA+ALT+[` repeatedly until at the first folder, then press once more. Expected: NVDA announces exactly `"No previous folder"`. Press `NVDA+ALT+]` past the last folder. Expected: exactly `"No next folder"`.

- [ ] **Step 2: Modify `script_previous_folder`**

The current method (around line 264–272) reads:

```python
	@script(description=_("Move to previous folder"))
	def script_previous_folder(self, gesture):
		if self.currentPathIndex > 0:
			self.currentPathIndex -= 1
			self.notesPath = self.paths[self.currentPathIndex]
			folder = os.path.basename(self.notesPath.rstrip("/\\")) or self.notesPath
			ui.message(folder + " " + self._load_notes())
		else:
			ui.message(_("No previous folder"))
```

Replace the `else` branch so it computes the current folder name (matching the existing expression on line 269) and appends it:

```python
	@script(description=_("Move to previous folder"))
	def script_previous_folder(self, gesture):
		if self.currentPathIndex > 0:
			self.currentPathIndex -= 1
			self.notesPath = self.paths[self.currentPathIndex]
			folder = os.path.basename(self.notesPath.rstrip("/\\")) or self.notesPath
			ui.message(folder + " " + self._load_notes())
		else:
			folder = os.path.basename(self.notesPath.rstrip("/\\")) or self.notesPath
			ui.message(_("No previous folder, {}").format(folder))
```

- [ ] **Step 3: Modify `script_next_folder`**

The current method (around line 274–282) reads:

```python
	@script(description=_("Move to next folder"))
	def script_next_folder(self, gesture):
		if self.currentPathIndex < len(self.paths) - 1:
			self.currentPathIndex += 1
			self.notesPath = self.paths[self.currentPathIndex]
			folder = os.path.basename(self.notesPath.rstrip("/\\")) or self.notesPath
			ui.message(folder + " " + self._load_notes())
		else:
			ui.message(_("No next folder"))
```

Replace the `else` branch the same way:

```python
	@script(description=_("Move to next folder"))
	def script_next_folder(self, gesture):
		if self.currentPathIndex < len(self.paths) - 1:
			self.currentPathIndex += 1
			self.notesPath = self.paths[self.currentPathIndex]
			folder = os.path.basename(self.notesPath.rstrip("/\\")) or self.notesPath
			ui.message(folder + " " + self._load_notes())
		else:
			folder = os.path.basename(self.notesPath.rstrip("/\\")) or self.notesPath
			ui.message(_("No next folder, {}").format(folder))
```

- [ ] **Step 4: Lint and format**

Run:

```powershell
ruff check addon/globalPlugins/invisinote/__init__.py
ruff format addon/globalPlugins/invisinote/__init__.py
```

Expected: both commands exit 0.

- [ ] **Step 5: Verify — manual NVDA test**

Rebuild and reinstall:

```powershell
scons
```

Restart NVDA. With at least two folders configured:

1. Press `NVDA+ALT+[` repeatedly until at the first folder. Press `NVDA+ALT+[` once more. Expected: `"No previous folder, <first-folder-basename>"` (e.g. `"No previous folder, notes"`).
2. Press `NVDA+ALT+]` repeatedly until at the last folder. Press `NVDA+ALT+]` once more. Expected: `"No next folder, <last-folder-basename>"`.

- [ ] **Step 6: Commit**

```powershell
git add addon/globalPlugins/invisinote/__init__.py
git commit -m "feat: append current folder name to edge messages"
```

---

## After all tasks: housekeeping

- [ ] **Run the full pre-commit suite once:**

```powershell
pre-commit run --all
```

Expected: all hooks pass. If any hook reports issues, fix them and amend the relevant commit (per CLAUDE.md, prefer a new commit; do not rewrite history that's been pushed).

- [ ] **Sanity check the gesture dict for duplicates:**

Open `addon/globalPlugins/invisinote/__init__.py`, locate the `__gestures` dict, and visually confirm no key appears twice. The new entries `"kb:NVDA+ALT+H"` and `"kb:NVDA+ALT+'"` should each appear exactly once.

- [ ] **Note for future work (do NOT do as part of this plan):** `addon/locale/` contains a `zh_TW` catalog. The four new/changed strings (`Move to start of line`, `Move to end of line`, `No previous note, {}`, `No next note, {}`, `No previous folder, {}`, `No next folder, {}`) will need translating in a follow-up. They are picked up automatically by `scons pot` because they are wrapped in `_()`. Out of scope for this plan.
