import addonHandler
import os
import ui
import api
import subprocess
import wx
import gui
import globalPluginHandler
from scriptHandler import script

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("invisinote")
	notes = []
	currentNoteIndex = 0
	currentLineIndex = 0
	currentNoteLines = []

	def __init__(self):
		super().__init__()
		addonDir = os.path.dirname(__file__)
		rootDir = os.path.abspath(os.path.join(addonDir, ".."))
		
		self.notesFolder = os.path.join(rootDir, "notes")
		
		if not os.path.exists(self.notesFolder):
			os.makedirs(self.notesFolder)
			ui.message(_("Folder created"))

	def _loadNotes(self):
		self.notes = [
			os.path.join(self.notesFolder, f)
			for f in os.listdir(self.notesFolder)
			if f.endswith(".txt")
		]
		if self.notes:
			self.currentNoteIndex = 0  # Reset to the first note
			self._loadCurrentNoteLines()
			ui.message(_("Loaded {} notes.").format(len(self.notes)))
		else:
			ui.message(_("No notes found"))

	def _loadCurrentNoteLines(self):
		if self.notes:
			notePath = self.notes[self.currentNoteIndex]
			with open(notePath, "r", encoding="utf-8") as note:
				self.currentNoteLines = note.readlines()
			self.currentLineIndex = 0  # Reset to the first line
		else:
			self.currentNoteLines = []

	@script(description=_("Open the folder"))
	def script_open_folder(self, gesture):
		if os.path.exists(self.notesFolder):
			subprocess.Popen(f'explorer "{self.notesFolder}"', shell=True)
			ui.message(_("Opened folder"))
		else:
			ui.message(_("Folder not found"))

	@script(description=_("Read current note"))
	def script_read_current_note(self, gesture):
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
			self.currentLineIndex += 1
		ui.message(self.currentNoteLines[self.currentLineIndex].strip())

	@script(description=_("Move to previous line"))
	def script_previous_line(self, gesture):
		if self.currentNoteLines and self.currentLineIndex > 0:
			self.currentLineIndex -= 1
		ui.message(self.currentNoteLines[self.currentLineIndex].strip())

	@script(description=_("Read current line"))
	def script_read_current_line(self, gesture):
		if self.currentNoteLines and 0 <= self.currentLineIndex < len(self.currentNoteLines):
			ui.message(self.currentNoteLines[self.currentLineIndex].strip())
		else:
			ui.message(_("No line to read"))

	@script(description=_("Copy current line"))
	def script_copy_line(self, gesture):
		if self.currentNoteLines and 0 <= self.currentLineIndex < len(self.currentNoteLines):
			api.copyToClip(self.currentNoteLines[self.currentLineIndex].strip())
			ui.message(_("Line copied"))
		else:
			ui.message(_("No line to copy"))

	__gestures = {
		"kb:NVDA+ALT+O": "open_folder",
		"kb:NVDA+ALT+R": "load_notes",
		"kb:NVDA+ALT+E": "read_current_note",
		"kb:NVDA+ALT+L": "next_note",
		"kb:NVDA+ALT+J": "previous_note",
		"kb:NVDA+ALT+I": "previous_line",
		"kb:NVDA+ALT+K": "next_line",
		"kb:NVDA+ALT+U": "read_current_line",
		"kb:NVDA+ALT+A": "copy_note",
		"kb:NVDA+ALT+C": "copy_line",
	}