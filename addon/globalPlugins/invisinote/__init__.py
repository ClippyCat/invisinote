import addonHandler
import os
import ui
import api
import subprocess
import globalPluginHandler
from scriptHandler import script

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("invisinote")
	notes = []
	currentNoteIndex = 0
	currentLineIndex = 0
	currentNoteLines = []
	currentWordIndex = 0
	currentCharIndex = 0

	def __init__(self):
		super().__init__()
		defaultPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "notes"))
		self.notesPath = defaultPath
		if not os.path.exists(self.notesPath):
			os.makedirs(self.notesPath)
			ui.message(_("Path created"))

	def _loadNotes(self):
		self.notes = sorted(
			os.path.join(self.notesPath, f)
			for f in os.listdir(self.notesPath)
			if f.endswith(".txt")
		)
		if self.notes:
			self.currentNoteIndex = 0
			self._loadCurrentNoteLines()
			ui.message(_("{} notes.").format(len(self.notes)))
		else:
			ui.message(_("No notes"))

	def _loadCurrentNoteLines(self):
		if self.notes:
			notePath = self.notes[self.currentNoteIndex]
			try:
				with open(notePath, "r", encoding="utf-8") as note:
					self.currentNoteLines = note.readlines()
			except UnicodeDecodeError:
				with open(notePath, "r", encoding="latin-1") as note:
					self.currentNoteLines = note.readlines()
			self.set_current_line(0)
		else:
			self.currentNoteLines = []

	def set_current_line(self, index):
		"""Set current line index and sync word/char positions."""
		self.currentLineIndex = index
		self.currentCharIndex = 0
		self._update_word_index_from_char()

	def _current_line(self):
		if self.currentNoteLines and 0 <= self.currentLineIndex < len(self.currentNoteLines):
			return self.currentNoteLines[self.currentLineIndex].rstrip("\n")
		return ""

	def _words_with_indices(self, line):
		import re
		words = []
		for match in re.finditer(r'\S+', line):
			words.append((match.group(0), match.start(), match.end()))
		return words

	def _update_word_index_from_char(self):
		line = self._current_line()
		words = self._words_with_indices(line)
		idx = self.currentCharIndex
		for i, (_, start, end) in enumerate(words):
			if start <= idx < end:
				self.currentWordIndex = i
				return
		self.currentWordIndex = len(words) - 1 if words else 0

	def _update_char_index_from_word(self):
		line = self._current_line()
		words = self._words_with_indices(line)
		if 0 <= self.currentWordIndex < len(words):
			self.currentCharIndex = words[self.currentWordIndex][1]
		else:
			self.currentCharIndex = 0

	def _get_current_note_content(self):
		if not self.notes:
			return None
		notePath = self.notes[self.currentNoteIndex]
		try:
			with open(notePath, "r", encoding="utf-8") as note:
				return note.read().strip() or None
		except UnicodeDecodeError:
			with open(notePath, "r", encoding="latin-1") as note:
				return note.read().strip() or None

	@script(description=_("Open the path"))
	def script_open_path(self, gesture):
		if os.path.exists(self.notesPath):
			subprocess.Popen(f'explorer "{self.notesPath}"', shell=True)
			ui.message(_("Opened path"))
		else:
			ui.message(_("Path not found"))

	@script(description=_("Read current note"))
	def script_read_note(self, gesture):
		content = self._get_current_note_content()
		ui.message(content if content else _("Empty note"))

	@script(description=_("Copy note"))
	def script_copy_note(self, gesture):
		content = self._get_current_note_content()
		if content:
			api.copyToClip(content)
			ui.message(_("Note copied"))
		else:
			ui.message(_("Empty note"))

	@script(description=_("Load all notes"))
	def script_load_notes(self, gesture):
		self._loadNotes()

	@script(description=_("Move to next note"))
	def script_next_note(self, gesture):
		if self.notes and self.currentNoteIndex < len(self.notes) - 1:
			self.currentNoteIndex += 1
			self._loadCurrentNoteLines()
			noteName = os.path.basename(self.notes[self.currentNoteIndex])
			ui.message(noteName)
		else:
			ui.message(_("No next note"))

	@script(description=_("Move to previous note"))
	def script_previous_note(self, gesture):
		if self.notes and self.currentNoteIndex > 0:
			self.currentNoteIndex -= 1
			self._loadCurrentNoteLines()
			noteName = os.path.basename(self.notes[self.currentNoteIndex])
			ui.message(noteName)
		else:
			ui.message(_("No previous note"))

	@script(description=_("Move to next line"))
	def script_next_line(self, gesture):
		if self.currentNoteLines and self.currentLineIndex < len(self.currentNoteLines) - 1:
			self.set_current_line(self.currentLineIndex + 1)
		ui.message(self._current_line())

	@script(description=_("Move to previous line"))
	def script_previous_line(self, gesture):
		if self.currentNoteLines and self.currentLineIndex > 0:
			self.set_current_line(self.currentLineIndex - 1)
		ui.message(self._current_line())

	@script(description=_("Copy current line"))
	def script_copy_line(self, gesture):
		line = self._current_line()
		if line:
			api.copyToClip(line)
			ui.message(_("Line copied"))
		else:
			ui.message(_("No line to copy"))

	@script(description=_("Move to next character"))
	def script_next_character(self, gesture):
		line = self._current_line()
		if self.currentCharIndex < len(line) - 1:
			self.currentCharIndex += 1
		self._update_word_index_from_char()
		if line:
			ui.message(line[self.currentCharIndex])

	@script(description=_("Move to previous character"))
	def script_previous_character(self, gesture):
		line = self._current_line()
		if self.currentCharIndex > 0:
			self.currentCharIndex -= 1
		self._update_word_index_from_char()
		if line:
			ui.message(line[self.currentCharIndex])

	@script(description=_("Move to next word"))
	def script_next_word(self, gesture):
		line = self._current_line()
		words = self._words_with_indices(line)
		if words and self.currentWordIndex < len(words) - 1:
			self.currentWordIndex += 1
		self._update_char_index_from_word()
		if words:
			ui.message(words[self.currentWordIndex][0])

	@script(description=_("Move to previous word"))
	def script_previous_word(self, gesture):
		line = self._current_line()
		words = self._words_with_indices(line)
		if words and self.currentWordIndex > 0:
			self.currentWordIndex -= 1
		self._update_char_index_from_word()
		if words:
			ui.message(words[self.currentWordIndex][0])

	__gestures = {
		"kb:NVDA+ALT+P": "open_path",
		"kb:NVDA+ALT+N": "load_notes",
		"kb:NVDA+ALT+U": "previous_note",
		"kb:NVDA+ALT+O": "next_note",
		"kb:NVDA+ALT+I": "previous_line",
		"kb:NVDA+ALT+K": "next_line",
		"kb:NVDA+ALT+J": "previous_word",
		"kb:NVDA+ALT+L": "next_word",
		"kb:NVDA+ALT+,": "previous_character",
		"kb:NVDA+ALT+.": "next_character",
		"kb:NVDA+ALT+SHIFT+A": "read_note",
		"kb:NVDA+ALT+A": "copy_note",
		"kb:NVDA+ALT+;": "copy_line",
	}
