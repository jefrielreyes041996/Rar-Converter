# -*- coding: utf-8 -*-
"""
Gichu RAR Converter
- Scans immediate subfolders in a selected source directory.
- Finds a GhiChu file (with or without an extension) inside each folder.
- Uses the first word of the first non-empty line as the archive name.
- Creates genuine .RAR archives using WinRAR's rar.exe.
- Keeps all original folders untouched.
"""
from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Rar-Converter"

def find_rar_exe():
    candidates = [
        shutil.which("rar.exe"),
        shutil.which("rar"),
        r"C:\Program Files\WinRAR\rar.exe",
        r"C:\Program Files (x86)\WinRAR\rar.exe",
        r"C:\WinRAR\rar.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return ""

def safe_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\\\|?*\x00-\x1f]', "_", value).strip(" .")
    return value or "Unknown_Username"

def read_username(ghichu: Path) -> str:
    raw = ghichu.read_bytes()
    text = None
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("Could not decode GhiChu file")
    for line in text.splitlines():
        line = line.strip().lstrip("\ufeff")
        if line:
            return line.split()[0]
    raise ValueError("GhiChu file is empty")

def find_ghichu(folder: Path):
    matches = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for filename in files:
            p = Path(root) / filename
            if p.name.lower() == "ghichu" or p.stem.lower() == "ghichu":
                matches.append(p)
    if not matches:
        return None
    matches.sort(key=lambda p: (len(p.relative_to(folder).parts), str(p).lower()))
    return matches[0], len(matches)

def unique_archive_path(output_dir: Path, username: str) -> Path:
    base = safe_filename(username)
    candidate = output_dir / f"{base}.rar"
    index = 2
    while candidate.exists():
        candidate = output_dir / f"{base}_{index}.rar"
        index += 1
    return candidate

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("850x650")
        self.root.minsize(760, 570)
        self.events = queue.Queue()
        self.worker = None
        self.cancel_requested = False
        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.rar_var = tk.StringVar(value=find_rar_exe())
        self.status_var = tk.StringVar(value="Choose a source folder to begin.")
        self.progress_var = tk.DoubleVar(value=0)
        self._build()
        self.root.after(100, self._poll_events)

    def _build(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Gichu RAR Converter", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Extract account usernames from GhiChu files and create RAR archives.",
                  foreground="#666").pack(anchor="w", pady=(2, 16))

        paths = ttk.LabelFrame(outer, text="Folders and RAR engine", padding=12)
        paths.pack(fill="x")
        self._path_row(paths, "Source folder", self.source_var, self.choose_source)
        self._path_row(paths, "Output folder", self.output_var, self.choose_output)
        self._path_row(paths, "WinRAR rar.exe", self.rar_var, self.choose_rar)

        note = ttk.Label(outer,
            text="Original folders are always kept. Existing archive names are never overwritten; duplicates get _2, _3, etc.",
            foreground="#287a43", wraplength=790)
        note.pack(anchor="w", pady=12)

        summary = ttk.Frame(outer)
        summary.pack(fill="x", pady=(0, 8))
        self.total_label = ttk.Label(summary, text="Folders: 0")
        self.total_label.pack(side="left")
        self.ready_label = ttk.Label(summary, text="Ready: 0")
        self.ready_label.pack(side="left", padx=18)
        self.skip_label = ttk.Label(summary, text="Skipped: 0")
        self.skip_label.pack(side="left")
        self.progress = ttk.Progressbar(outer, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", pady=(0, 10))

        self.tree = ttk.Treeview(outer, columns=("username", "status"), show="headings", height=11)
        self.tree.heading("username", text="Detected username")
        self.tree.heading("status", text="Status / details")
        self.tree.column("username", width=230, anchor="w")
        self.tree.column("status", width=540, anchor="w")
        self.tree.pack(fill="both", expand=True)

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(12, 0))
        self.start_btn = ttk.Button(bottom, text="Scan folders", command=self.scan)
        self.start_btn.pack(side="left")
        self.convert_btn = ttk.Button(bottom, text="Start RAR conversion", command=self.start_conversion, state="disabled")
        self.convert_btn.pack(side="left", padx=8)
        ttk.Button(bottom, text="Clear list", command=self.clear_list).pack(side="left")
        ttk.Label(bottom, textvariable=self.status_var).pack(side="right")

    def _path_row(self, parent, label, var, command):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, width=17).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse...", command=command).pack(side="left")

    def choose_source(self):
        path = filedialog.askdirectory(title="Select parent folder containing account folders")
        if path:
            self.source_var.set(path)
            if not self.output_var.get():
                self.output_var.set(str(Path(path) / "RAR_Output"))

    def choose_output(self):
        path = filedialog.askdirectory(title="Select output folder for RAR files")
        if path:
            self.output_var.set(path)

    def choose_rar(self):
        path = filedialog.askopenfilename(title="Locate WinRAR rar.exe", filetypes=[("rar.exe", "rar.exe"), ("Executable", "*.exe")])
        if path:
            self.rar_var.set(path)

    def clear_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.total_label.config(text="Folders: 0")
        self.ready_label.config(text="Ready: 0")
        self.skip_label.config(text="Skipped: 0")
        self.progress_var.set(0)
        self.convert_btn.config(state="disabled")
        self.status_var.set("List cleared.")
        self.jobs = []

    def scan(self):
        source = Path(self.source_var.get().strip())
        if not source.is_dir():
            messagebox.showerror(APP_TITLE, "Please select a valid source folder.")
            return
        self.clear_list()
        self.jobs = []
        skipped = 0
        folders = sorted((p for p in source.iterdir() if p.is_dir()), key=lambda p: p.name.lower())
        for folder in folders:
            try:
                result = find_ghichu(folder)
                if not result:
                    self.tree.insert("", "end", values=("—", f"SKIPPED — No GhiChu file in {folder.name}"))
                    skipped += 1
                    continue
                ghichu, count = result
                username = read_username(ghichu)
                self.jobs.append((folder, username))
                detail = f"Ready — source folder: {folder.name}"
                if count > 1:
                    detail += f" (found {count} GhiChu files; using the closest one)"
                self.tree.insert("", "end", values=(username, detail))
            except Exception as exc:
                self.tree.insert("", "end", values=("—", f"ERROR — {folder.name}: {exc}"))
                skipped += 1
        self.total_label.config(text=f"Folders: {len(folders)}")
        self.ready_label.config(text=f"Ready: {len(self.jobs)}")
        self.skip_label.config(text=f"Skipped: {skipped}")
        self.status_var.set(f"Scan complete: {len(self.jobs)} ready, {skipped} skipped.")
        if self.jobs:
            self.convert_btn.config(state="normal")

    def start_conversion(self):
        if not getattr(self, "jobs", None):
            messagebox.showinfo(APP_TITLE, "Scan the source folder first.")
            return
        rar = Path(self.rar_var.get().strip())
        if not rar.is_file():
            messagebox.showerror(APP_TITLE,
                "WinRAR's rar.exe was not found. Install WinRAR, then browse to rar.exe (usually in C:\\\\Program Files\\\\WinRAR).")
            return
        output = Path(self.output_var.get().strip())
        if not self.output_var.get().strip():
            messagebox.showerror(APP_TITLE, "Please select an output folder.")
            return
        output.mkdir(parents=True, exist_ok=True)
        if not messagebox.askyesno(APP_TITLE, f"Create {len(self.jobs)} RAR archive(s)?\\n\\nOriginal folders will be kept."):
            return
        self.cancel_requested = False
        self.start_btn.config(state="disabled")
        self.convert_btn.config(state="disabled")
        self.worker = threading.Thread(target=self._convert_worker, args=(str(rar), str(output), list(self.jobs)), daemon=True)
        self.worker.start()
        self.status_var.set("Converting...")

    def _convert_worker(self, rar_exe, output, jobs):
        output_dir = Path(output)
        success = 0
        failed = 0
        for index, (folder, username) in enumerate(jobs, 1):
            if self.cancel_requested:
                break
            archive = unique_archive_path(output_dir, username)
            self.events.put(("row", index-1, username, f"Compressing → {archive.name}"))
            try:
                # Run from inside the folder so the archive contains its contents,
                # rather than an extra enclosing folder level.
                command = [rar_exe, "a", "-r", "-ep1", "-idq", str(archive), "*"]
                result = subprocess.run(command, cwd=str(folder), capture_output=True, text=True, timeout=None)
                if result.returncode == 0 and archive.is_file() and archive.stat().st_size > 0:
                    success += 1
                    self.events.put(("row", index-1, username, f"SUCCESS — {archive.name}"))
                else:
                    failed += 1
                    message = (result.stderr or result.stdout or f"RAR exit code {result.returncode}").strip()
                    self.events.put(("row", index-1, username, f"FAILED — {message[:180]}"))
                    if archive.exists() and archive.stat().st_size == 0:
                        archive.unlink(missing_ok=True)
            except Exception as exc:
                failed += 1
                self.events.put(("row", index-1, username, f"FAILED — {exc}"))
            self.events.put(("progress", index, len(jobs), success, failed))
        self.events.put(("done", success, failed, len(jobs), self.cancel_requested))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "row":
                    _, idx, username, status = event
                    items = self.tree.get_children()
                    if idx < len(items):
                        self.tree.item(items[idx], values=(username, status))
                elif event[0] == "progress":
                    _, current, total, success, failed = event
                    self.progress_var.set(current / total * 100 if total else 0)
                    self.status_var.set(f"Processed {current}/{total} — {success} successful, {failed} failed.")
                elif event[0] == "done":
                    _, success, failed, total, cancelled = event
                    self.start_btn.config(state="normal")
                    self.convert_btn.config(state="normal" if self.jobs else "disabled")
                    msg = f"Finished: {success} successful, {failed} failed."
                    if cancelled:
                        msg += " Stopped early."
                    self.status_var.set(msg)
                    messagebox.showinfo(APP_TITLE, msg + "\\n\\nOriginal folders were not changed.")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
