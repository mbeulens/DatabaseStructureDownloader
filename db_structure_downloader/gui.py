# db_structure_downloader/gui.py
"""Tkinter GUI. Two screens (connection, export) presented as frames swapped
inside a single Tk root window. Knows nothing about SQL or markdown layout."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pymysql

from db_structure_downloader import config, db
from db_structure_downloader.markdown import render


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Database Structure Downloader")
        self.geometry("600x500")
        self._container = ttk.Frame(self, padding=12)
        self._container.pack(fill="both", expand=True)
        self._show_connection_screen()

    def _show_connection_screen(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()
        ConnectionFrame(self._container, on_connected=self._show_export_screen).pack(
            fill="both", expand=True
        )

    def _show_export_screen(self, conn, database: str, conn_args: dict) -> None:
        # Filled in in Task 10.
        raise NotImplementedError


class ConnectionFrame(ttk.Frame):
    def __init__(self, master, on_connected) -> None:
        super().__init__(master)
        self._on_connected = on_connected

        self._host = tk.StringVar(value="localhost")
        self._port = tk.StringVar(value="3306")
        self._user = tk.StringVar(value="root")
        self._password = tk.StringVar()
        self._database = tk.StringVar()

        saved = config.load_last_connection()
        if saved:
            self._host.set(saved.get("host", "localhost"))
            self._port.set(str(saved.get("port", 3306)))
            self._user.set(saved.get("user", "root"))
            self._database.set(saved.get("database", ""))

        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Connect to MySQL", font=("", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 12), sticky="w"
        )

        rows = [
            ("Host", self._host, False),
            ("Port", self._port, False),
            ("User", self._user, False),
            ("Password", self._password, True),
            ("Database", self._database, False),
        ]
        for i, (label, var, is_secret) in enumerate(rows, start=1):
            ttk.Label(self, text=label).grid(row=i, column=0, sticky="w", pady=4)
            entry = ttk.Entry(self, textvariable=var, show="*" if is_secret else "")
            entry.grid(row=i, column=1, sticky="ew", pady=4)

        self.columnconfigure(1, weight=1)

        self._error = ttk.Label(self, foreground="red", wraplength=500)
        self._error.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w", pady=(8, 4))

        ttk.Button(self, text="Connect", command=self._on_connect_click).grid(
            row=len(rows) + 2, column=0, columnspan=2, pady=(8, 0)
        )

    def _on_connect_click(self) -> None:
        self._error.config(text="")
        try:
            port = int(self._port.get())
        except ValueError:
            self._error.config(text="Port must be a number.")
            return

        conn_args = dict(
            host=self._host.get().strip(),
            port=port,
            user=self._user.get().strip(),
            password=self._password.get(),
            database=self._database.get().strip(),
        )
        try:
            conn = db.connect(**conn_args)
        except pymysql.Error as e:
            self._error.config(text=f"Connection failed: {e}")
            return

        self._on_connected(conn, conn_args["database"], conn_args)
