#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import getpass
import threading
import subprocess
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd

# -----------------------------
# Configuration
# -----------------------------

BASE_DIR = Path(__file__).resolve().parent

DIR_PDFS = BASE_DIR / "01_PDFs"
DIR_PARSED = BASE_DIR / "02_Parsed_Data"
DIR_MASTER = BASE_DIR / "03_Master_Data"
DIR_UNMATCHED = DIR_MASTER / "unmatched addresses"
DIR_SYSTEM = DIR_MASTER / "_system"
DIR_LOGS = BASE_DIR / "00_Logs"
DIR_TODAY = BASE_DIR / "05_Todays_Output"
DIR_ARCHIVE = BASE_DIR / "04_Archive"
DIR_HISTORIC = BASE_DIR / "06_Historic_Output_Files"
DIR_PARSERS = BASE_DIR / "Parsers"

USER_PATHS_FILE = DIR_SYSTEM / "user_paths.json"
DELETE_AFTER_IMPORT_FILE = DIR_SYSTEM / "delete_after_import.json"

ADMIN_PIN = "122333444455555"
SUPERADMIN_PIN = "04971401861009201117122015"


def ensure_unmatched_file_exists_only(path: Path):
    """
    GUI rule (FINAL):
    - Ensure folder exists
    - Ensure file exists
    - NEVER define schema
    - NEVER touch columns
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        pd.DataFrame().to_excel(path, index=False)


# -----------------------------
# Helpers
# -----------------------------

def ensure_dirs():
    for d in [
        DIR_PDFS, DIR_PARSED, DIR_MASTER, DIR_UNMATCHED,
        DIR_SYSTEM, DIR_LOGS, DIR_TODAY, DIR_ARCHIVE, DIR_HISTORIC
    ]:
        d.mkdir(parents=True, exist_ok=True)


def load_user_paths():
    if USER_PATHS_FILE.exists():
        try:
            with open(USER_PATHS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_user_paths(mapping):
    with open(USER_PATHS_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)


def load_delete_flag():
    if DELETE_AFTER_IMPORT_FILE.exists():
        try:
            with open(DELETE_AFTER_IMPORT_FILE, "r", encoding="utf-8") as f:
                return bool(json.load(f).get("delete_after_import", False))
        except Exception:
            pass
    return False


def save_delete_flag(flag):
    with open(DELETE_AFTER_IMPORT_FILE, "w", encoding="utf-8") as f:
        json.dump({"delete_after_import": flag}, f, indent=2)


def _file_locked(path: Path) -> bool:
    try:
        with open(path, "a"):
            return False
    except PermissionError:
        return True


# -----------------------------
# GUI
# -----------------------------

class V12GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PO Processing V12 – Control Panel")
        self.geometry("900x720")

        ensure_dirs()

        self.current_user = getpass.getuser()
        self.user_paths = load_user_paths()
        self.delete_after_import = load_delete_flag()

        self.admin_unlocked = False
        self.superadmin = False
        self.v12_running = False
        self.update_running = False

        self._build_ui()
        self.after(1000, self.refresh_button_states)

    def refresh_button_states(self):
        try:
            unmatched_file = DIR_UNMATCHED / "Unmatched_Addresses.xlsx"

            if not self.v12_running and not self.update_running:
                ensure_unmatched_file_exists_only(unmatched_file)

            unmatched_exists = False
            unmatched_locked = False

            if unmatched_file.exists():
                unmatched_locked = _file_locked(unmatched_file)
                if not unmatched_locked:
                    try:
                        df = pd.read_excel(unmatched_file)
                        unmatched_exists = not df.empty
                    except Exception:
                        unmatched_exists = False

            pdf_count = len(list(DIR_PDFS.glob("*.pdf")))

            if self.v12_running or self.update_running:
                self.btn_process.configure(state="disabled")
            elif unmatched_exists:
                self.btn_process.configure(state="disabled")
            elif pdf_count == 0:
                self.btn_process.configure(state="disabled")
            else:
                self.btn_process.configure(state="normal")

            if self.update_running or self.v12_running:
                self.btn_update_master.configure(state="disabled")
            elif unmatched_exists and not unmatched_locked:
                self.btn_update_master.configure(state="normal")
            else:
                self.btn_update_master.configure(state="disabled")

        except Exception as e:
            self.log(f"[GUI] refresh error: {e}")

        self.after(1000, self.refresh_button_states)

    def log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # --- remaining GUI code unchanged ---
