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
			self._paths.pop(idx)
			self._paths_listbox.Delete(idx)
			if self._paths:
				self._paths_listbox.SetSelection(min(idx, len(self._paths) - 1))

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
			self._file_types.pop(idx)
			self._types_listbox.Delete(idx)
			if self._file_types:
				self._types_listbox.SetSelection(min(idx, len(self._file_types) - 1))

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
		self.selectionAnchor = None
		self.paths = []
		self.currentPathIndex = 0
		self.notesPath = ""
		self.pathsFile = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "paths.txt"))
		self.fileTypes = []
		self.fileTypesFile = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "filetypes.txt"))
		self._load_paths()
		self._load_file_types()

	def _load_paths(self):
		defaultPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "notes"))
		if not os.path.exists(self.pathsFile):
			with open(self.pathsFile, "w", encoding="utf-8") as f:
				f.write(defaultPath + "\n")
		with open(self.pathsFile, "r", encoding="utf-8") as f:
			self.paths = [line.strip() for line in f if line.strip()]
		if not self.paths:
			self.paths = [defaultPath]
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
		return _("No notes")

	def _load_current_note_lines(self):
		self.selectionAnchor = None
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
		return [(m.group(0), m.start(), m.end()) for m in re.finditer(r'\S+', line)]

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

	def _start_selection_if_needed(self):
		if self.selectionAnchor is None:
			self.selectionAnchor = (self.currentLineIndex, self.currentCharIndex)

	def _get_selected_text(self):
		if self.selectionAnchor is None:
			return None
		anchorLine, anchorChar = self.selectionAnchor
		curLine, curChar = self.currentLineIndex, self.currentCharIndex
		if (anchorLine, anchorChar) <= (curLine, curChar):
			startLine, startChar = anchorLine, anchorChar
			endLine, endChar = curLine, curChar
		else:
			startLine, startChar = curLine, curChar
			endLine, endChar = anchorLine, anchorChar
		if startLine == endLine:
			return self.currentNoteLines[startLine].rstrip("\n")[startChar:endChar]
		parts = [self.currentNoteLines[startLine][startChar:]]
		for i in range(startLine + 1, endLine):
			parts.append(self.currentNoteLines[i])
		parts.append(self.currentNoteLines[endLine].rstrip("\n")[:endChar])
		return "".join(parts)

	def _abs_offset(self, line_idx, char_idx):
		return sum(len(self.currentNoteLines[i]) for i in range(line_idx)) + char_idx

	def _selection_extending(self, old_line, old_char):
		aL, aC = self.selectionAnchor
		nL, nC = self.currentLineIndex, self.currentCharIndex
		anchor_off = self._abs_offset(aL, aC)
		old_off = self._abs_offset(old_line, old_char)
		new_off = self._abs_offset(nL, nC)
		return abs(new_off - anchor_off) >= abs(old_off - anchor_off)

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
			self.paths = dlg.get_paths() or [os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "notes"))]
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
			ui.message(_("No previous folder"))

	@script(description=_("Move to next folder"))
	def script_next_folder(self, gesture):
		if self.currentPathIndex < len(self.paths) - 1:
			self.currentPathIndex += 1
			self.notesPath = self.paths[self.currentPathIndex]
			folder = os.path.basename(self.notesPath.rstrip("/\\")) or self.notesPath
			ui.message(folder + " " + self._load_notes())
		else:
			ui.message(_("No next folder"))

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
		else:
			ui.message(_("No next note"))

	@script(description=_("Move to previous note"))
	def script_previous_note(self, gesture):
		if self.notes and self.currentNoteIndex > 0:
			self.currentNoteIndex -= 1
			self._load_current_note_lines()
			ui.message(os.path.basename(self.notes[self.currentNoteIndex]))
		else:
			ui.message(_("No previous note"))

	@script(description=_("Move to next line"))
	def script_next_line(self, gesture):
		self.selectionAnchor = None
		if self.currentNoteLines and self.currentLineIndex < len(self.currentNoteLines) - 1:
			self._set_current_line(self.currentLineIndex + 1)
		ui.message(self._current_line())

	@script(description=_("Move to previous line"))
	def script_previous_line(self, gesture):
		self.selectionAnchor = None
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
		self.selectionAnchor = None
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
		self.selectionAnchor = None
		line = self._current_line()
		self.currentCharIndex = min(self.currentCharIndex, max(0, len(line) - 1))
		if self.currentCharIndex > 0:
			self.currentCharIndex -= 1
		self._update_word_index_from_char()
		if line:
			char = line[self.currentCharIndex]
			ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), char))

	@script(description=_("Move to next word"))
	def script_next_word(self, gesture):
		self.selectionAnchor = None
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
		self.selectionAnchor = None
		words = self._words_with_indices(self._current_line())
		if not words:
			return
		prev_idx = next((i for i in range(len(words) - 1, -1, -1) if words[i][1] < self.currentCharIndex), None)
		if prev_idx is not None:
			self.currentWordIndex = prev_idx
		self.currentCharIndex = words[self.currentWordIndex][1]
		ui.message(words[self.currentWordIndex][0])

	@script(description=_("Select to next line"))
	def script_select_next_line(self, gesture):
		if not self.currentNoteLines:
			return
		old_line = self.currentLineIndex
		old_char = self.currentCharIndex
		first_press = self.selectionAnchor is None
		if first_press:
			# anchor at start of current line, extend to its end — selects only this line
			self.selectionAnchor = (self.currentLineIndex, 0)
			self.currentCharIndex = len(self._current_line())
		else:
			if self.currentLineIndex >= len(self.currentNoteLines) - 1:
				return
			self._set_current_line(self.currentLineIndex + 1)
			self.currentCharIndex = len(self._current_line())
		if not first_press and self.currentLineIndex == old_line and self.currentCharIndex == old_char:
			return
		suffix = _("selected") if self._selection_extending(old_line, old_char) else _("unselected")
		delta = self._current_line()
		ui.message((delta or _("blank")) + " " + suffix)

	@script(description=_("Select to previous line"))
	def script_select_previous_line(self, gesture):
		if not self.currentNoteLines:
			return
		old_line = self.currentLineIndex
		old_char = self.currentCharIndex
		first_press = self.selectionAnchor is None
		if first_press:
			# anchor at end of current line, extend to its start — selects only this line
			self.selectionAnchor = (self.currentLineIndex, len(self._current_line()))
			self.currentCharIndex = 0
		else:
			if self.currentLineIndex <= 0:
				return
			self._set_current_line(self.currentLineIndex - 1)
		if not first_press and self.currentLineIndex == old_line and self.currentCharIndex == old_char:
			return
		suffix = _("selected") if self._selection_extending(old_line, old_char) else _("unselected")
		delta = self._current_line()
		ui.message((delta or _("blank")) + " " + suffix)

	@script(description=_("Select to next word"))
	def script_select_next_word(self, gesture):
		old_line = self.currentLineIndex
		old_char = self.currentCharIndex
		self._start_selection_if_needed()
		words = self._words_with_indices(self._current_line())
		if not words:
			return
		next_idx = next((i for i, (_, start, _) in enumerate(words) if start > self.currentCharIndex), None)
		if next_idx is not None:
			self.currentWordIndex = next_idx
			self.currentCharIndex = words[self.currentWordIndex][1]
		else:
			# already at last word — advance to its end so it can be included in the selection
			self.currentCharIndex = words[-1][2]
		if self.currentCharIndex == old_char:
			return
		suffix = _("selected") if self._selection_extending(old_line, old_char) else _("unselected")
		line = self._current_line()
		delta = line[min(old_char, self.currentCharIndex):max(old_char, self.currentCharIndex)].strip()
		ui.message((delta or _("blank")) + " " + suffix)

	@script(description=_("Select to previous word"))
	def script_select_previous_word(self, gesture):
		old_line = self.currentLineIndex
		old_char = self.currentCharIndex
		self._start_selection_if_needed()
		words = self._words_with_indices(self._current_line())
		if not words:
			return
		prev_idx = next((i for i in range(len(words) - 1, -1, -1) if words[i][1] < self.currentCharIndex), None)
		if prev_idx is not None:
			self.currentWordIndex = prev_idx
		self.currentCharIndex = words[self.currentWordIndex][1]
		if self.currentCharIndex == old_char:
			return
		suffix = _("selected") if self._selection_extending(old_line, old_char) else _("unselected")
		line = self._current_line()
		delta = line[min(old_char, self.currentCharIndex):max(old_char, self.currentCharIndex)].strip()
		ui.message((delta or _("blank")) + " " + suffix)

	@script(description=_("Select to next character"))
	def script_select_next_character(self, gesture):
		old_line = self.currentLineIndex
		old_char = self.currentCharIndex
		self._start_selection_if_needed()
		line = self._current_line()
		# allow charIndex to reach len(line) so the last char is selectable
		if self.currentCharIndex < len(line):
			self.currentCharIndex += 1
		if self.currentCharIndex == old_char:
			return
		self._update_word_index_from_char()
		suffix = _("selected") if self._selection_extending(old_line, old_char) else _("unselected")
		delta_char = line[min(old_char, self.currentCharIndex - 1)]
		ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), delta_char) + " " + suffix)

	@script(description=_("Select to previous character"))
	def script_select_previous_character(self, gesture):
		old_line = self.currentLineIndex
		old_char = self.currentCharIndex
		self._start_selection_if_needed()
		line = self._current_line()
		if self.currentCharIndex > 0:
			self.currentCharIndex -= 1
		if self.currentCharIndex == old_char:
			return
		self._update_word_index_from_char()
		suffix = _("selected") if self._selection_extending(old_line, old_char) else _("unselected")
		delta_char = line[min(old_char, self.currentCharIndex)]
		ui.message(characterProcessing.processSpeechSymbol(languageHandler.getLanguage(), delta_char) + " " + suffix)

	@script(description=_("Copy selection"))
	def script_copy_selection(self, gesture):
		text = self._get_selected_text()
		if text:
			api.copyToClip(text)
			ui.message(_("Selection copied"))
		else:
			ui.message(_("No selection"))

	@script(description=_("Clear selection"))
	def script_clear_selection(self, gesture):
		self.selectionAnchor = None
		ui.message(_("Selection cleared"))

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
		"kb:NVDA+ALT+SHIFT+A": "read_note",
		"kb:NVDA+ALT+A": "copy_note",
		"kb:NVDA+ALT+;": "copy_line",
		"kb:NVDA+ALT+SHIFT+I": "select_previous_line",
		"kb:NVDA+ALT+SHIFT+K": "select_next_line",
		"kb:NVDA+ALT+SHIFT+J": "select_previous_word",
		"kb:NVDA+ALT+SHIFT+L": "select_next_word",
		"kb:NVDA+ALT+SHIFT+,": "select_previous_character",
		"kb:NVDA+ALT+SHIFT+.": "select_next_character",
		"kb:NVDA+ALT+SHIFT+;": "copy_selection",
		"kb:NVDA+ALT+BACKSPACE": "clear_selection",
	}
