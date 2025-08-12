import addonHandler
import os
import ui
import api
import subprocess
import globalPluginHandler
from scriptHandler import script
import wx
import re
import json

PATHS_FILENAME = "paths.json"

class NotesPathManager:
	def __init__(self, paths_json_dir, default_notes_folder):
		self.paths_file = os.path.join(paths_json_dir, PATHS_FILENAME)
		self.default_notes_folder = default_notes_folder
		self.paths = []
		self.current_index = 0
		self._load_paths()

	@property
	def current(self):
		return self.paths[self.current_index] if self.paths else None

	def set_paths(self, new_paths):
		self.paths = [p for p in new_paths if p and os.path.isdir(p)]
		self.current_index = 0 if self.paths else 0
		self._save_paths()

	def next_folder(self):
		if self.paths:
			self.current_index = (self.current_index + 1) % len(self.paths)

	def prev_folder(self):
		if self.paths:
			self.current_index = (self.current_index - 1) % len(self.paths)

	def _load_paths(self):
		try:
			if os.path.isfile(self.paths_file):
				with open(self.paths_file, "r", encoding="utf-8") as f:
					data = json.load(f)
					self.paths = [p for p in data if p and os.path.isdir(p)]
					self.current_index = 0 if self.paths else 0
			else:
				self.paths = [self.default_notes_folder]
				self.current_index = 0
		except Exception as e:
			ui.message(_("Error loading paths: {}").format(e))
			self.paths = [self.default_notes_folder]
			self.current_index = 0

	def _save_paths(self):
		try:
			with open(self.paths_file, "w", encoding="utf-8") as f:
				json.dump(self.paths, f, ensure_ascii=False, indent=2)
		except Exception as e:
			ui.message(_("Error saving paths: {}").format(e))

class NotesPathDialog(wx.Dialog):
	def __init__(self, parent, current_paths):
		super().__init__(parent, title=_("Edit Notes Paths"))
		vbox = wx.BoxSizer(wx.VERTICAL)
		self.text_ctrl = wx.TextCtrl(self, value="\n".join(current_paths), style=wx.TE_MULTILINE|wx.TE_DONTWRAP, size=(400, 200))
		vbox.Add(self.text_ctrl, flag=wx.EXPAND|wx.ALL, border=10)

		btn_sizer = wx.StdDialogButtonSizer()
		self.save_btn = wx.Button(self, wx.ID_OK, label=_("Save"))
		self.cancel_btn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
		btn_sizer.AddButton(self.save_btn)
		btn_sizer.AddButton(self.cancel_btn)
		btn_sizer.Realize()
		vbox.Add(btn_sizer, flag=wx.ALIGN_CENTER|wx.ALL, border=10)

		self.SetSizer(vbox)
		self.Fit()

	def get_paths(self):
		return [p.strip() for p in self.text_ctrl.GetValue().splitlines() if p.strip()]

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("invisinote")

	def __init__(self):
		super().__init__()
		addonDir = os.path.dirname(__file__)
		rootDir = os.path.abspath(os.path.join(addonDir, ".."))
		defaultPath = os.path.join(rootDir, "notes")
		if not os.path.exists(defaultPath):
			os.makedirs(defaultPath)
			ui.message(_("Path created"))
		self.notesPathManager = NotesPathManager(rootDir, defaultPath)
		self._reset_state()
		self._loadNotes()

	def _reset_state(self):
		self.notes = []
		self.currentNoteIndex = 0
		self.currentLineIndex = 0
		self.currentNoteLines = []
		self.currentWordIndex = 0
		self.currentCharIndex = 0

	def _update_notesPath(self):
		self.notesPath = self.notesPathManager.current if self.notesPathManager.current else ""

	def _loadNotes(self):
		self._update_notesPath()
		path = self.notesPath
		self.notes = []
		if not path or not os.path.exists(path):
			ui.message(_("Invalid path"))
			self.currentNoteLines = []
			return
		files = sorted(
			[f for f in os.listdir(path) if f.endswith(".txt")],
			key=lambda f: f.lower()
		)
		self.notes = [os.path.join(path, f) for f in files]
		if self.notes:
			self.currentNoteIndex = 0
			self._loadCurrentNoteLines()
			ui.message(_("{} notes from: {}").format(len(self.notes), path))
		else:
			self.currentNoteLines = []
			ui.message(_("No notes found in: {}").format(path))

	def _loadCurrentNoteLines(self):
		self.currentNoteLines = []
		if self.notes:
			notePath = self.notes[self.currentNoteIndex]
			try:
				with open(notePath, "r", encoding="utf-8") as note:
					self.currentNoteLines = note.readlines()
			except Exception as e:
				self.currentNoteLines = []
				ui.message(_("Failed to load note: {}").format(str(e)))
			self.set_current_line(0)

	def set_current_line(self, index):
		self.currentLineIndex = max(0, min(index, len(self.currentNoteLines) - 1 if self.currentNoteLines else 0))
		self.currentCharIndex = 0
		self.currentWordIndex = 0

	def _current_line(self):
		if self.currentNoteLines and 0 <= self.currentLineIndex < len(self.currentNoteLines):
			return self.currentNoteLines[self.currentLineIndex].rstrip("\n")
		return ""

	def _words_with_indices(self, line):
		return [(m.group(0), m.start(), m.end()) for m in re.finditer(r'\S+', line)] if line else []

	def _update_word_index_from_char(self):
		line = self._current_line()
		words = self._words_with_indices(line)
		idx = self.currentCharIndex
		for i, (_, start, end) in enumerate(words):
			if start <= idx < end:
				self.currentWordIndex = i
				return
		self.currentWordIndex = max(0, len(words) - 1) if words else 0

	def _update_char_index_from_word(self):
		line = self._current_line()
		words = self._words_with_indices(line)
		self.currentCharIndex = words[self.currentWordIndex][1] if 0 <= self.currentWordIndex < len(words) else 0

	@script(description=_("Open the path"))
	def script_open_path(self, gesture):
		path = self.notesPath
		if os.path.exists(path):
			subprocess.Popen(f'explorer "{path}"', shell=True)
			ui.message(_("Opened path"))
		else:
			ui.message(_("Path not found"))

	@script(description=_("Read current note"))
	def script_read_note(self, gesture):
		if self.notes:
			notePath = self.notes[self.currentNoteIndex]
			try:
				with open(notePath, "r", encoding="utf-8") as note:
					content = note.read()
				ui.message(content.strip() if content else _("Empty note"))
			except Exception as e:
				ui.message(_("Error reading note: {}").format(e))
		else:
			ui.message(_("No notes available"))

	@script(description=_("Copy note"))
	def script_copy_note(self, gesture):
		if self.notes:
			notePath = self.notes[self.currentNoteIndex]
			try:
				with open(notePath, "r", encoding="utf-8") as note:
					content = note.read()
				if content:
					api.copyToClip(content.strip())
					ui.message(_("Note copied"))
				else:
					ui.message(_("Empty note"))
			except Exception as e:
				ui.message(_("Error copying note: {}").format(e))
		else:
			ui.message(_("No notes available"))

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
		if line:
			ui.message(line[self.currentCharIndex])

	@script(description=_("Move to previous character"))
	def script_previous_character(self, gesture):
		line = self._current_line()
		if self.currentCharIndex > 0:
			self.currentCharIndex -= 1
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

	@script(description=_("Edit paths"))
	def script_edit_paths(self, gesture):
		def show_dialog():
			try:
				parent = wx.GetApp().GetTopWindow()
				dlg = NotesPathDialog(parent, self.notesPathManager.paths)
				if dlg.ShowModal() == wx.ID_OK:
					paths = dlg.get_paths()
					self.notesPathManager.set_paths(paths)
					self._reset_state()
					self._loadNotes()
					ui.message(_("Notes path(s) updated"))
				else:
					ui.message(_("Canceled"))
				dlg.Destroy()
			except Exception as e:
				ui.message(_("Error editing paths: ") + str(e))
		wx.CallAfter(show_dialog)

	@script(description=_("Switch to previous notes folder"))
	def script_prev_folder(self, gesture):
		self.notesPathManager.prev_folder()
		self._reset_state()
		self._loadNotes()

	@script(description=_("Switch to next notes folder"))
	def script_next_folder(self, gesture):
		self.notesPathManager.next_folder()
		self._reset_state()
		self._loadNotes()

	__gestures = {
		"kb:NVDA+ALT+P": "open_path",
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
		"kb:NVDA+ALT+SHIFT+P": "edit_paths",
		"kb:NVDA+ALT+[": "prev_folder",
		"kb:NVDA+ALT+]": "next_folder",
	}