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

	def __init__(self):
		super().__init__()
		addonDir = os.path.dirname(__file__)
		rootDir = os.path.abspath(os.path.join(addonDir, ".."))
		
		self.notesPath = os.path.join(rootDir, "notes")
		
		if not os.path.exists(self.notesPath):
			os.makedirs(self.notesPath)
			ui.message(_("Path created"))

	def _loadNotes(self):
		self.notes = [
			os.path.join(self.notesPath, f)
			for f in os.listdir(self.notesPath)
			if f.endswith(".txt")
		]
		if self.notes:
			self.currentNoteIndex = 0
			self._loadCurrentNoteLines()
			ui.message(_("Loaded {} notes.").format(len(self.notes)))
		else:
			ui.message(_("No notes found"))

	def _loadCurrentNoteLines(self):
		if self.notes:
			notePath = self.notes[self.currentNoteIndex]
			with open(notePath, "r", encoding="utf-8") as note:
				self.currentNoteLines = note.readlines()
			self.set_current_line(0)
		else:
			self.currentNoteLines = []

	def set_current_line(self, index):
		self.currentLineIndex = index
		self.currentWordIndex = 0

	@script(description=_("Open the path"))
	def script_open_path(self, gesture):
		if os.path.exists(self.notesPath):
			subprocess.Popen(f'explorer "{self.notesPath}"', shell=True)
			ui.message(_("Opened path"))
		else:
			ui.message(_("Path not found"))

	@script(description=_("Read current note"))
	def script_read_note(self, gesture):
		if self.notes:
			notePath = self.notes[self.currentNoteIndex]
			with open(notePath, "r", encoding="utf-8") as note:
				content = note.read()
			if content:
				ui.message(content.strip())
			else:
				ui.message(_("Empty note"))
		else:
			ui.message(_("No notes available"))

	@script(description=_("Copy note"))
	def script_copy_note(self, gesture):
		if self.notes:
			notePath = self.notes[self.currentNoteIndex]
			with open(notePath, "r", encoding="utf-8") as note:
				content = note.read()
			if content:
				api.copyToClip(content.strip())
				ui.message(_("Note copied"))
			else:
				ui.message(_("Empty note"))
		else:
			ui.message(_("No notes available"))

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
		ui.message(self.currentNoteLines[self.currentLineIndex].strip())

	@script(description=_("Move to previous line"))
	def script_previous_line(self, gesture):
		if self.currentNoteLines and self.currentLineIndex > 0:
			self.set_current_line(self.currentLineIndex - 1)
		ui.message(self.currentNoteLines[self.currentLineIndex].strip())

	@script(description=_("Copy current line"))
	def script_copy_line(self, gesture):
		if self.currentNoteLines and 0 <= self.currentLineIndex < len(self.currentNoteLines):
			api.copyToClip(self.currentNoteLines[self.currentLineIndex].strip())
			ui.message(_("Line copied"))
		else:
			ui.message(_("No line to copy"))

	@script(description=_("Move to next word"))
	def script_next_word(self, gesture):
		if self.currentNoteLines and 0 <= self.currentLineIndex < len(self.currentNoteLines):
			words = self.currentNoteLines[self.currentLineIndex].strip().split()
			if words and self.currentWordIndex < len(words) - 1:
				self.currentWordIndex += 1
			ui.message(words[self.currentWordIndex])

	@script(description=_("Move to previous word"))
	def script_previous_word(self, gesture):
		if self.currentNoteLines and 0 <= self.currentLineIndex < len(self.currentNoteLines):
			words = self.currentNoteLines[self.currentLineIndex].strip().split()
			if words and self.currentWordIndex > 0:
				self.currentWordIndex -= 1
			ui.message(words[self.currentWordIndex])

	__gestures = {
		"kb:NVDA+ALT+P": "open_path",
		"kb:NVDA+ALT+N": "load_notes",
		"kb:NVDA+ALT+U": "previous_note",
		"kb:NVDA+ALT+O": "next_note",
		"kb:NVDA+ALT+I": "previous_line",
		"kb:NVDA+ALT+K": "next_line",
		"kb:NVDA+ALT+J": "previous_word",
		"kb:NVDA+ALT+L": "next_word",
		"kb:NVDA+ALT+SHIFT+A": "read_note",
		"kb:NVDA+ALT+A": "copy_note",
		"kb:NVDA+ALT+C": "copy_line",
	}