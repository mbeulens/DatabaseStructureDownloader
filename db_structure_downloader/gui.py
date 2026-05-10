# db_structure_downloader/gui.py
"""Tkinter GUI. Two screens (connection, export) presented as frames swapped
inside a single Tk root window. Knows nothing about SQL or markdown layout."""

from __future__ import annotations

import os
from pathlib import Path

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
        self.report_callback_exception = self._on_unhandled_exception
        self._container = ttk.Frame(self, padding=12)
        self._container.pack(fill="both", expand=True)
        self._show_connection_screen()

    def _on_unhandled_exception(self, exc_type, exc_value, exc_tb) -> None:
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_tb)
        messagebox.showerror(
            "Unexpected error",
            f"{exc_type.__name__}: {exc_value}\n\nThe app will keep running.",
        )

    def _show_connection_screen(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()
        ConnectionFrame(self._container, on_connected=self._show_export_screen).pack(
            fill="both", expand=True
        )

    def _show_export_screen(self, conn, database: str, conn_args: dict) -> None:
        for child in self._container.winfo_children():
            child.destroy()
        ExportFrame(
            self._container,
            conn=conn,
            database=database,
            conn_args=conn_args,
        ).pack(fill="both", expand=True)


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


class ExportFrame(ttk.Frame):
    def __init__(self, master, conn, database: str, conn_args: dict) -> None:
        super().__init__(master)
        self._conn = conn
        self._database = database
        self._conn_args = conn_args

        self._output_folder = tk.StringVar()
        self._table_vars: dict[str, tk.BooleanVar] = {}

        self._build()
        self._load_tables()

    def _build(self) -> None:
        ttk.Label(self, text=f"Tables in `{self._database}`",
                  font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))

        button_row = ttk.Frame(self)
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Select all",
                   command=self._select_all).pack(side="left")
        ttk.Button(button_row, text="Deselect all",
                   command=self._deselect_all).pack(side="left", padx=(8, 0))

        # Scrollable checkbox list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, pady=(8, 8))

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self._inner = ttk.Frame(canvas)

        self._inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Output folder row
        folder_row = ttk.Frame(self)
        folder_row.pack(fill="x", pady=(0, 8))
        ttk.Label(folder_row, text="Output folder:").pack(side="left")
        ttk.Entry(folder_row, textvariable=self._output_folder).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(folder_row, text="Browse...",
                   command=self._pick_folder).pack(side="left")

        ttk.Button(self, text="Export", command=self._on_export_click).pack(
            anchor="e", pady=(0, 8)
        )

        self._status = tk.Text(self, height=8, state="disabled", wrap="word")
        self._status.pack(fill="both", expand=False)

    def _load_tables(self) -> None:
        try:
            tables = db.list_tables(self._conn)
        except pymysql.Error as e:
            messagebox.showerror("Failed to list tables", str(e))
            return
        for t in tables:
            var = tk.BooleanVar(value=False)
            self._table_vars[t] = var
            ttk.Checkbutton(self._inner, text=t, variable=var).pack(anchor="w")

    def _select_all(self) -> None:
        for v in self._table_vars.values():
            v.set(True)

    def _deselect_all(self) -> None:
        for v in self._table_vars.values():
            v.set(False)

    def _pick_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose output folder")
        if chosen:
            self._output_folder.set(chosen)

    def _append_status(self, line: str) -> None:
        self._status.configure(state="normal")
        self._status.insert("end", line + "\n")
        self._status.see("end")
        self._status.configure(state="disabled")
        self.update_idletasks()

    def _on_export_click(self) -> None:
        selected = [t for t, v in self._table_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("No tables selected",
                                   "Pick at least one table to export.")
            return
        folder = self._output_folder.get().strip()
        if not folder:
            messagebox.showwarning("No output folder",
                                   "Pick an output folder.")
            return
        out_path = Path(folder)
        if not out_path.is_dir() or not os.access(out_path, os.W_OK):
            messagebox.showerror("Folder not writable",
                                 f"Cannot write to {out_path}.")
            return

        exported = 0
        failed: list[tuple[str, str]] = []
        total = len(selected)

        for i, table in enumerate(selected, start=1):
            try:
                meta = db.fetch_table_metadata(self._conn, self._database, table)
                content = render(meta)
                (out_path / f"{table}.md").write_text(content, encoding="utf-8")
                exported += 1
                self._append_status(f"Exported {table} ({i} / {total})")
            except (pymysql.Error, OSError) as e:
                failed.append((table, str(e)))
                self._append_status(f"Failed: {table} — {e}")

        if failed:
            self._append_status(
                f"Done. Exported {exported} / {total} tables. "
                f"{len(failed)} failed: {', '.join(t for t, _ in failed)} "
                f"(see above)."
            )
        else:
            self._append_status(f"Done. Exported {exported} / {total} tables.")
            config.save_last_connection(
                host=self._conn_args["host"],
                port=self._conn_args["port"],
                user=self._conn_args["user"],
                database=self._conn_args["database"],
            )
