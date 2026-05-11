import re
import os
import ui
import api
import wx
import gui
import subprocess
import globalVars
import globalPluginHandler
import characterProcessing
import languageHandler
import scriptHandler
from scriptHandler import script


class SettingsDialog(wx.Dialog):
	def __init__(self, parent, paths, file_types):
		super().__init__(parent, title=_("Invisinote settings"))
		self._paths = list(paths)
		self._file_types = list(file_types)
		main_sizer = wx.BoxSizer(wx.VERTICAL)

		paths_box = wx.StaticBoxSizer(wx.StaticBox(self, label=_("Folders")), wx.VERTICAL)
		self._paths_listbox = wx.ListBox(self, choices=self._paths)
		paths_box.Add(self._paths_listbox, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
		paths_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
		add_folder_btn = wx.Button(self, label=_("Add folder"))
		remove_folder_btn = wx.Button(self, label=_("Remove folder"))
		paths_btn_sizer.Add(add_folder_btn, flag=wx.RIGHT, border=5)
		paths_btn_sizer.Add(remove_folder_btn)
		paths_box.Add(paths_btn_sizer, flag=wx.ALL, border=5)
		main_sizer.Add(paths_box, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

		types_box = wx.StaticBoxSizer(wx.StaticBox(self, label=_("File types")), wx.VERTICAL)
		self._types_listbox = wx.ListBox(self, choices=self._file_types)
		types_box.Add(self._types_listbox, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
		types_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
		add_type_btn = wx.Button(self, label=_("Add type"))
		remove_type_btn = wx.Button(self, label=_("Remove type"))
		types_btn_sizer.Add(add_type_btn, flag=wx.RIGHT, border=5)
		types_btn_sizer.Add(remove_type_btn)
		types_box.Add(types_btn_sizer, flag=wx.ALL, border=5)
		main_sizer.Add(types_box, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

		main_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALL, border=5)
		self.SetSizer(main_sizer)
		self.Fit()
		add_folder_btn.Bind(wx.EVT_BUTTON, self._on_add_folder)
		remove_folder_btn.Bind(wx.EVT_BUTTON, self._on_remove_folder)
		add_type_btn.Bind(wx.EVT_BUTTON, self._on_add_type)
		remove_type_btn.Bind(wx.EVT_BUTTON, self._on_remove_type)

	def _on_add_folder(self, event):
		dlg = wx.DirDialog(self, _("Choose a folder"))
		if dlg.ShowModal() == wx.ID_OK:
			path = dlg.GetPath()
			if path not in self._paths:
				self._paths.append(path)
				self._paths_listbox.Append(path)
				self._paths_listbox.SetSelection(len(self._paths) - 1)
		dlg.Destroy()

	def _on_remove_folder(self, event):
		idx = self._paths_listbox.GetSelection()
		if idx != wx.NOT_FOUND:
			path = self._paths[idx]
			dlg = wx.MessageDialog(
				self,
				_("Remove folder: {}?").format(path),
				_("Confirm removal"),
				wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
			)
			if dlg.ShowModal() == wx.ID_YES:
				self._paths.pop(idx)
				self._paths_listbox.Delete(idx)
				if self._paths:
					self._paths_listbox.SetSelection(min(idx, len(self._paths) - 1))
			dlg.Destroy()

	def _on_add_type(self, event):
		dlg = wx.TextEntryDialog(self, _("Enter file extension (e.g. md):"), _("Add file type"))
		if dlg.ShowModal() == wx.ID_OK:
			ext = dlg.GetValue().strip().lstrip(".")
			if ext and ext not in self._file_types:
				self._file_types.append(ext)
				self._types_listbox.Append(ext)
				self._types_listbox.SetSelection(len(self._file_types) - 1)
		dlg.Destroy()

	def _on_remove_type(self, event):
		idx = self._types_listbox.GetSelection()
		if idx != wx.NOT_FOUND:
			ext = self._file_types[idx]
			dlg = wx.MessageDialog(
				self,
				_("Remove file type: {}?").format(ext),
				_("Confirm removal"),
				wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
			)
			if dlg.ShowModal() == wx.ID_YES:
				self._file_types.pop(idx)
				self._types_listbox.Delete(idx)
				if self._file_types:
					self._types_listbox.SetSelection(min(idx, len(self._file_types) - 1))
			dlg.Destroy()

	def get_paths(self):
		return list(self._paths)

	def get_file_types(self):
		return list(self._file_types)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("invisinote")

	def __init__(self):
		super().__init__()
		self.notes = []
		self.currentNoteIndex = 0
		self.currentLineIndex = 0
		self.currentNoteLines = []
		self.currentWordIndex = 0
		self.currentCharIndex = 0
		self.selectionStart = None
		self.selectionEnd = None
		self.paths = []
		self.currentPathIndex = 0
		self.notesPath = ""
		nvdaConfigPath = globalVars.appArgs.configPath
		scratchpadDir = os.path.join(nvdaConfigPath, "scratchpad")
		moduleDir = os.path.dirname(os.path.abspath(__file__))
		if os.path.normcase(moduleDir).startswith(os.path.normcase(scratchpadDir) + os.sep):
			self.configFolder = os.path.join(scratchpadDir, "invisinote")
		else:
			self.configFolder = os.path.join(nvdaConfigPath, "invisinote")
		os.makedirs(self.configFolder, exist_ok=True)
		self.pathsFile = os.path.join(self.configFolder, "paths.txt")
		self.fileTypes = []
		self.fileTypesFile = os.path.join(self.configFolder, "filetypes.txt")
		self._load_paths()
		self._load_file_types()

	def _load_paths(self):
		defaultPath = os.path.join(self.configFolder, "notes")
		if not os.path.exists(self.pathsFile):
			with open(self.pathsFile, "w", encoding="utf-8") as f:
				f.write(defaultPath + "\n")
		with open(self.pathsFile, "r", encoding="utf-8") as f:
			self.paths = [line.strip() for line in f if line.strip()]
		if not self.paths:
			self.paths = [defaultPath]
		for path in self.paths:
			os.makedirs(path, exist_ok=True)
		self.currentPathIndex = 0
		self.notesPath = self.paths[0]

	def _load_file_types(self):
		if not os.path.exists(self.fileTypesFile):
			with open(self.fileTypesFile, "w", encoding="utf-8") as f:
				f.write("txt\n")
		with open(self.fileTypesFile, "r", encoding="utf-8") as f:
			self.fileTypes = [line.strip().lstrip(".") for line in f if line.strip()]
		if not self.fileTypes:
			self.fileTypes = ["txt"]

	def _read_note_file(self, path):
		try:
			with open(path, "r", encoding="utf-8") as f:
				return f.read()
		except UnicodeDecodeError:
			with open(path, "r", encoding="latin-1") as f:
				return f.read()

	def _load_notes(self):
		if not os.path.isdir(self.notesPath):
			return _("Folder not found")
		self.notes = sorted(
			os.path.join(self.notesPath, f)
			for f in os.listdir(self.notesPath)
			if any(f.endswith("." + ext) for ext in self.fileTypes)
		)
		if self.notes:
			self.currentNoteIndex = 0
			self._load_current_note_lines()
			return _("{} notes.").format(len(self.notes))
		self.currentNoteIndex = 0
		self.currentNoteLines = []
		self.currentLineIndex = 0
		self.currentWordIndex = 0
		self.currentCharIndex = 0
		self.selectionStart = None
		self.selectionEnd = None
		return _("No notes")

	def _load_current_note_lines(self):
		self.selectionStart = None
		self.selectionEnd = None
		if self.notes:
			content = self._read_note_file(self.notes[self.currentNoteIndex])
			self.currentNoteLines = content.splitlines(keepends=True)
			self._set_current_line(0)
		else:
			self.currentNoteLines = []

	def _set_current_line(self, index):
		self.currentLineIndex = index
		self.currentCharIndex = 0
		self.currentWordIndex = 0

	def _current_line(self):
		if self.currentNoteLines and 0 <= self.currentLineIndex < len(self.currentNoteLines):
			return self.currentNoteLines[self.currentLineIndex].rstrip("\n")
		return ""

	def _words_with_indices(self, line):
		return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", line)]

	def _update_word_index_from_char(self):
		line = self._current_line()
		words = self._words_with_indices(line)
		idx = self.currentCharIndex
		for i, (_, start, end) in enumerate(words):
			if start <= idx < end:
				self.currentWordIndex = i
				return
		self.currentWordIndex = len(words) - 1 if words else 0

	def _get_current_note_content(self):
		if not self.currentNoteLines:
			return None
		return "".join(self.currentNoteLines).strip() or None

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
			return self.currentNoteLines[startLine].rstrip("\n")[startChar : endChar + 1]
		parts = [self.currentNoteLines[startLine][startChar:]]
		for i in range(startLine + 1, endLine):
			parts.append(self.currentNoteLines[i])
		parts.append(self.currentNoteLines[endLine].rstrip("\n")[: endChar + 1])
		return "".join(parts)

	@script(description=_("Open the path"))
	def script_open_path(self, gesture):
		subprocess.Popen(f'explorer "{self.notesPath}"', shell=True)
		ui.message(_("Opened path"))

	@script(description=_("Edit paths"))
	def script_edit_paths(self, gesture):
		wx.CallAfter(self._show_paths_dialog)

	def _show_paths_dialog(self):
		dlg = SettingsDialog(gui.mainFrame, self.paths, self.fileTypes)
		if dlg.ShowModal() == wx.ID_OK:
			self.paths = dlg.get_paths() or [os.path.join(self.configFolder, "notes")]
			self.currentPathIndex = min(self.currentPathIndex, len(self.paths) - 1)
			self.notesPath = self.paths[self.currentPathIndex]
			with open(self.pathsFile, "w", encoding="utf-8") as f:
				f.write("\n".join(self.paths) + "\n")
			self.fileTypes = dlg.get_file_types() or ["txt"]
			with open(self.fileTypesFile, "w", encoding="utf-8") as f:
				f.write("\n".join(self.fileTypes) + "\n")
		dlg.Destroy()

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
		ui.message(self._load_notes())

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

	@script(description=_("Move to next line"))
	def script_next_line(self, gesture):
		if self.currentNoteLines and self.currentLineIndex < len(self.currentNoteLines) - 1:
			self._set_current_line(self.currentLineIndex + 1)
		ui.message(self._current_line())

	@script(description=_("Move to previous line"))
	def script_previous_line(self, gesture):
		if self.currentNoteLines and self.currentLineIndex > 0:
			self._set_current_line(self.currentLineIndex - 1)
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
		# clamp in case a prior selection script set charIndex past end
		self.currentCharIndex = min(self.currentCharIndex, max(0, len(line) - 1))
		if self.currentCharIndex < len(line) - 1:
			self.currentCharIndex += 1
		self._update_word_index_from_char()
		if line:
			char = line[self.currentCharIndex]
			ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), char))

	@script(description=_("Move to previous character"))
	def script_previous_character(self, gesture):
		line = self._current_line()
		self.currentCharIndex = min(self.currentCharIndex, max(0, len(line) - 1))
		if self.currentCharIndex > 0:
			self.currentCharIndex -= 1
		self._update_word_index_from_char()
		if line:
			char = line[self.currentCharIndex]
			ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), char))

	@script(description=_("Move to start of line"))
	def script_start_of_line(self, gesture):
		line = self._current_line()
		self.currentCharIndex = 0
		self._update_word_index_from_char()
		if line:
			char = line[self.currentCharIndex]
			ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), char))

	@script(description=_("Move to end of line"))
	def script_end_of_line(self, gesture):
		line = self._current_line()
		self.currentCharIndex = max(0, len(line) - 1)
		self._update_word_index_from_char()
		if line:
			char = line[self.currentCharIndex]
			ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), char))

	@script(description=_("Move to next word"))
	def script_next_word(self, gesture):
		words = self._words_with_indices(self._current_line())
		if not words:
			return
		next_idx = next((i for i, (_, start, _) in enumerate(words) if start > self.currentCharIndex), None)
		if next_idx is not None:
			self.currentWordIndex = next_idx
		self.currentCharIndex = words[self.currentWordIndex][1]
		ui.message(words[self.currentWordIndex][0])

	@script(description=_("Move to previous word"))
	def script_previous_word(self, gesture):
		words = self._words_with_indices(self._current_line())
		if not words:
			return
		prev_idx = next(
			(i for i in range(len(words) - 1, -1, -1) if words[i][1] < self.currentCharIndex), None
		)
		if prev_idx is not None:
			self.currentWordIndex = prev_idx
		self.currentCharIndex = words[self.currentWordIndex][1]
		ui.message(words[self.currentWordIndex][0])

	@script(description=_("Set selection start"))
	def script_set_selection_start(self, gesture):
		if not self.currentNoteLines:
			ui.message(_("No notes"))
			return
		self.selectionStart = (self.currentLineIndex, self.currentCharIndex)
		line = self._current_line()
		if line and self.currentCharIndex < len(line):
			char = characterProcessing.processSpeechSymbol(
				languageHandler.getLanguage(), line[self.currentCharIndex]
			)
		else:
			char = _("blank")
		ui.message(_("selection start: ") + char)

	@script(description=_("Set selection end, twice to copy"))
	def script_set_selection_end(self, gesture):
		if not self.currentNoteLines:
			ui.message(_("No notes"))
			return
		if scriptHandler.getLastScriptRepeatCount() == 0:
			self.selectionEnd = (self.currentLineIndex, self.currentCharIndex)
			line = self._current_line()
			if line and self.currentCharIndex < len(line):
				char = characterProcessing.processSpeechSymbol(
					languageHandler.getLanguage(), line[self.currentCharIndex]
				)
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

	@script(description=_("Clear selection markers"))
	def script_clear_markers(self, gesture):
		self.selectionStart = None
		self.selectionEnd = None
		ui.message(_("selection cleared"))

	__gestures = {
		"kb:NVDA+ALT+P": "open_path",
		"kb:NVDA+ALT+SHIFT+P": "edit_paths",
		"kb:NVDA+ALT+[": "previous_folder",
		"kb:NVDA+ALT+]": "next_folder",
		"kb:NVDA+ALT+N": "load_notes",
		"kb:NVDA+ALT+U": "previous_note",
		"kb:NVDA+ALT+O": "next_note",
		"kb:NVDA+ALT+I": "previous_line",
		"kb:NVDA+ALT+K": "next_line",
		"kb:NVDA+ALT+J": "previous_word",
		"kb:NVDA+ALT+L": "next_word",
		"kb:NVDA+ALT+,": "previous_character",
		"kb:NVDA+ALT+.": "next_character",
		"kb:NVDA+ALT+H": "start_of_line",
		"kb:NVDA+ALT+'": "end_of_line",
		"kb:NVDA+ALT+SHIFT+A": "read_note",
		"kb:NVDA+ALT+A": "copy_note",
		"kb:NVDA+ALT+;": "copy_line",
		"kb:NVDA+ALT+F9": "set_selection_start",
		"kb:NVDA+ALT+F10": "set_selection_end",
		"kb:NVDA+ALT+BACKSPACE": "clear_markers",
	}
