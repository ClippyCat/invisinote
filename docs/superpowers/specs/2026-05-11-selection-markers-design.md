# Selection markers design

## Context

Invisinote currently has a live-select model: an `selectionAnchor` plus the cursor extend or shrink a selection via six Shift+arrow scripts (line/word/char × forward/back). This model has produced multiple bugs (wrong line announced on unselect, asymmetric shrink-by-two, silent boundaries) because tracking a moving anchor across operations has too many edge cases.

This design replaces the live-select model with two explicit markers, modeled on NVDA's NVDA+F9/F10 virtual marker convention.

## Goals

- Eliminate the live-select edge cases.
- Reuse the existing line/word/char navigation gestures; remove the six Shift+arrow variants.
- Match NVDA convention so users familiar with NVDA+F9/F10 don't have to learn a new model.

## User-facing behavior

### Gestures

| Gesture | Action |
|---|---|
| NVDA+ALT+F9 | Set selection start at cursor |
| NVDA+ALT+F10 (single press) | Set selection end at cursor |
| NVDA+ALT+F10 (double press) | Copy from start to end |
| NVDA+BACKSPACE | Clear both markers |

NVDA+ALT+F9 has no double-press behavior — pressing twice just re-sets the start marker at the cursor's current position both times.

### Announcements

| Trigger | Announcement |
|---|---|
| Set start | `selection start: <char at cursor>` (or `selection start: blank` on an empty line) |
| Set end (single F10) | `selection end: <char at cursor>` (or `selection end: blank`) |
| Copy success (double F10) | `selection copied` |
| Copy with either marker missing | `no selection` |
| Clear | `selection cleared` |

Setting a marker that's already set silently overwrites the prior position — no "moved" announcement, just the normal set-marker announcement.

### Auto-clear

Markers clear silently when the user:

- Switches folders (NVDA+ALT+`[` / NVDA+ALT+`]`)
- Switches notes (NVDA+ALT+U / NVDA+ALT+O)
- Reloads notes (NVDA+ALT+N)

Markers **persist** across regular line/word/char navigation. The current code clears `selectionAnchor` on every navigation; that behavior is removed.

### Range semantics

Copy uses `min(start, end)` through `max(start, end)` in document order — the user can place the markers in either order and the copy still works. The character at the end marker is **included** in the copied text (inclusive range, not the half-open `[start, end)` typical of text editors). Marking start on 'h' and end on 'o' of "hello" copies all five characters.

## State

Two new instance variables on `GlobalPlugin`:

```python
self.selectionStart  # Optional[tuple[int, int]] — (line_idx, char_idx) or None
self.selectionEnd    # same shape
```

`selectionAnchor` is removed entirely.

## Implementation changes

All edits in `addon/globalPlugins/invisinote/__init__.py`.

### Removed

State:

- `self.selectionAnchor` (and every write to it across the navigation scripts)

Helpers:

- `_start_selection_if_needed`
- `_selection_extending`
- `_abs_offset`
- `_get_selected_text`

Scripts:

- `script_select_previous_line`, `script_select_next_line`
- `script_select_previous_word`, `script_select_next_word`
- `script_select_previous_character`, `script_select_next_character`
- `script_copy_selection`
- `script_clear_selection`

Gesture map: the eight corresponding entries in `__gestures`.

Navigation scripts (`script_next_line`, `script_previous_line`, `script_next_word`, `script_previous_word`, `script_next_character`, `script_previous_character`) keep their cursor-move logic but drop the `self.selectionAnchor = None` line at the top — markers don't move with the cursor.

### Added

State init in `__init__`:

```python
self.selectionStart = None
self.selectionEnd = None
```

Helper method:

- `_selection_text()` — returns the inclusive text between `min(selectionStart, selectionEnd)` and `max(selectionStart, selectionEnd)`, or `None` if either marker is unset. Logic mirrors the removed `_get_selected_text` but with marker tuples and inclusive end-character handling.

Scripts:

- `script_set_selection_start` — records `(currentLineIndex, currentCharIndex)` into `selectionStart`, announces `selection start: <char>` (or `: blank` if the line is empty).
- `script_set_selection_end` — uses `scriptHandler.getLastScriptRepeatCount()` to distinguish presses:
  - Count 0 (single press): records `(currentLineIndex, currentCharIndex)` into `selectionEnd`, announces `selection end: <char>`.
  - Count > 0 (double or further press): treats as copy. Computes selection text via `_selection_text()`; if `None`, announces `no selection`; otherwise calls `api.copyToClip(text)` and announces `selection copied`.
- `script_clear_markers` — sets both `selectionStart` and `selectionEnd` to `None`, announces `selection cleared`. Always announces, even if both were already `None`.

Gesture bindings added to `__gestures`:

```python
"kb:NVDA+ALT+F9": "set_selection_start",
"kb:NVDA+ALT+F10": "set_selection_end",
"kb:NVDA+BACKSPACE": "clear_markers",
```

Import added at top of file: `import scriptHandler`.

### Auto-clear plumbing

`_load_current_note_lines` currently sets `self.selectionAnchor = None` at the top. Replace with:

```python
self.selectionStart = None
self.selectionEnd = None
```

That path is reached transitively by note navigation (`script_next_note`, `script_previous_note`), folder switching (`script_previous_folder`, `script_next_folder` → `_load_notes` → `_load_current_note_lines`), reload (`script_load_notes` → `_load_notes` → `_load_current_note_lines`), and initial load on plugin construction. One change covers every auto-clear case.

### Translation strings

New `_()`-wrapped strings introduced in source:

- `"selection start: "` (concatenated with the character)
- `"selection end: "`
- `"selection copied"`
- `"selection cleared"`
- `"no selection"`

Existing `_("blank")` is reused for the empty-line case.

After implementation, run `scons pot` to regenerate `addon/locale/messages.pot`. Existing `zh_TW` translations remain valid for unchanged strings; new strings fall back to English until translated and recompiled.

## Testing

No automated test framework exists in this repo. Manual test plan in NVDA after building with `scons`:

1. Open a note with multi-character content. Press NVDA+ALT+F9. Confirm `selection start: <char>` is announced for the character at the cursor.
2. Navigate forward a few characters with NVDA+ALT+`.`. Press NVDA+ALT+F10. Confirm `selection end: <char>`.
3. Press NVDA+ALT+F10 again quickly (double-press). Confirm `selection copied` is announced and the clipboard contains the inclusive range — both the start and end characters are present.
4. Press NVDA+BACKSPACE. Confirm `selection cleared`.
5. With no start set, press NVDA+ALT+F10 twice quickly. Confirm `no selection`; clipboard unchanged.
6. Set both markers, then press NVDA+ALT+O to switch notes. Press NVDA+ALT+F10 twice. Confirm `no selection` — markers auto-cleared.
7. Set start at line 5, navigate to line 3, set end. Double-press F10. Confirm copy auto-normalizes to line 3 → line 5 content.
8. Navigate to an empty line. Press NVDA+ALT+F9. Confirm `selection start: blank`.
9. Set start, navigate freely with line/word/char gestures, set end. Confirm markers don't drift with the cursor — copied text reflects the originally marked positions.

## Out of scope

- Per-note marker persistence (decided against during brainstorming).
- Visual or screen-reader indicator of marker position outside the announcement at set-time.
- A query gesture ("where is the start marker?") — not requested.
- A read-selection-aloud gesture — not requested.
- Adjusting existing copy_note / copy_line behavior — those are independent of the selection feature.
