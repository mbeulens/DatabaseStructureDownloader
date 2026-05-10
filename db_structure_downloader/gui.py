"""GTK4 + libadwaita GUI. Two screens (connection, export) presented as
pages in a Gtk.Stack inside a single Adw.ApplicationWindow. Knows nothing
about SQL or markdown layout."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, GLib, Gio  # noqa: E402

import pymysql  # noqa: E402

from db_structure_downloader import config, db  # noqa: E402
from db_structure_downloader.markdown import render  # noqa: E402


APP_ID = "nl.syntec.DbStructureDownloader"


class DbStructureApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._win: MainWindow | None = None

    def do_activate(self) -> None:
        if self._win is None:
            self._win = MainWindow(application=self)
        self._win.present()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_title("Database Structure Downloader")
        self.set_default_size(640, 720)

        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self._toast_overlay.set_child(toolbar)

        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        toolbar.set_content(self._stack)

        self._show_connection_screen()

    def _show_connection_screen(self) -> None:
        self._clear_stack()
        screen = ConnectionScreen(on_connected=self._on_connected)
        self._stack.add_named(screen, "connection")
        self._stack.set_visible_child_name("connection")

    def _on_connected(self, conn, conn_args: dict) -> None:
        self._clear_stack()
        screen = ExportScreen(
            conn=conn,
            conn_args=conn_args,
            toast_overlay=self._toast_overlay,
        )
        self._stack.add_named(screen, "export")
        self._stack.set_visible_child_name("export")

    def _clear_stack(self) -> None:
        child = self._stack.get_first_child()
        while child is not None:
            self._stack.remove(child)
            child = self._stack.get_first_child()


class ConnectionScreen(Gtk.Box):
    def __init__(self, on_connected) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._on_connected = on_connected

        clamp = Adw.Clamp(
            maximum_size=520,
            margin_top=24,
            margin_bottom=24,
            margin_start=12,
            margin_end=12,
        )
        self.append(clamp)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp.set_child(outer)

        title = Gtk.Label(label="Connect to MySQL", xalign=0)
        title.add_css_class("title-1")
        outer.append(title)

        saved = config.load_last_connection() or {}

        group = Adw.PreferencesGroup()
        outer.append(group)

        self._host = Adw.EntryRow(title="Host")
        self._host.set_text(saved.get("host", "localhost"))
        group.add(self._host)

        self._port = Adw.EntryRow(title="Port")
        self._port.set_text(str(saved.get("port", 3306)))
        group.add(self._port)

        self._user = Adw.EntryRow(title="User")
        self._user.set_text(saved.get("user", "root"))
        group.add(self._user)

        self._password = Adw.PasswordEntryRow(title="Password")
        group.add(self._password)

        self._database = Adw.EntryRow(title="Database")
        self._database.set_text(saved.get("database", ""))
        group.add(self._database)

        self._error = Gtk.Label(xalign=0, wrap=True)
        self._error.add_css_class("error")
        self._error.set_visible(False)
        outer.append(self._error)

        connect_btn = Gtk.Button(label="Connect", halign=Gtk.Align.END)
        connect_btn.add_css_class("suggested-action")
        connect_btn.add_css_class("pill")
        connect_btn.connect("clicked", self._on_connect_clicked)
        outer.append(connect_btn)

        for row in (self._host, self._port, self._user, self._password, self._database):
            row.connect("entry-activated", self._on_connect_clicked)

    def _on_connect_clicked(self, _widget) -> None:
        self._error.set_visible(False)
        try:
            port = int(self._port.get_text())
        except ValueError:
            self._show_error("Port must be a number.")
            return

        conn_args = dict(
            host=self._host.get_text().strip(),
            port=port,
            user=self._user.get_text().strip(),
            password=self._password.get_text(),
            database=self._database.get_text().strip(),
        )
        try:
            conn = db.connect(**conn_args)
        except pymysql.Error as e:
            self._show_error(f"Connection failed: {e}")
            return

        self._on_connected(conn, conn_args)

    def _show_error(self, message: str) -> None:
        self._error.set_text(message)
        self._error.set_visible(True)


class ExportScreen(Gtk.Box):
    def __init__(self, conn, conn_args: dict, toast_overlay: Adw.ToastOverlay) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._conn = conn
        self._conn_args = conn_args
        self._toast_overlay = toast_overlay
        self._table_checks: dict[str, Gtk.CheckButton] = {}
        self._output_folder: Path | None = None

        clamp = Adw.Clamp(
            maximum_size=640,
            margin_top=18,
            margin_bottom=18,
            margin_start=12,
            margin_end=12,
        )
        self.append(clamp)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        clamp.set_child(outer)

        title = Gtk.Label(
            label=f"Tables in {self._conn_args['database']}",
            xalign=0,
        )
        title.add_css_class("title-1")
        outer.append(title)

        select_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        outer.append(select_row)
        sel_all = Gtk.Button(label="Select all")
        sel_all.connect("clicked", lambda _b: self._set_all(True))
        select_row.append(sel_all)
        desel_all = Gtk.Button(label="Deselect all")
        desel_all.connect("clicked", lambda _b: self._set_all(False))
        select_row.append(desel_all)

        scrolled = Gtk.ScrolledWindow(
            vexpand=True,
            has_frame=True,
            min_content_height=240,
        )
        outer.append(scrolled)

        self._listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._listbox.add_css_class("boxed-list")
        scrolled.set_child(self._listbox)

        folder_group = Adw.PreferencesGroup()
        outer.append(folder_group)
        self._folder_row = Adw.ActionRow(
            title="Output folder",
            subtitle="(none chosen)",
        )
        browse_btn = Gtk.Button(label="Browse...", valign=Gtk.Align.CENTER)
        browse_btn.connect("clicked", self._on_browse_clicked)
        self._folder_row.add_suffix(browse_btn)
        folder_group.add(self._folder_row)

        export_btn = Gtk.Button(label="Export", halign=Gtk.Align.END)
        export_btn.add_css_class("suggested-action")
        export_btn.add_css_class("pill")
        export_btn.connect("clicked", self._on_export_clicked)
        outer.append(export_btn)

        status_scrolled = Gtk.ScrolledWindow(
            has_frame=True,
            min_content_height=140,
        )
        outer.append(status_scrolled)
        self._status_buf = Gtk.TextBuffer()
        status_view = Gtk.TextView(
            buffer=self._status_buf,
            editable=False,
            cursor_visible=False,
            monospace=True,
            wrap_mode=Gtk.WrapMode.WORD,
            top_margin=6,
            bottom_margin=6,
            left_margin=6,
            right_margin=6,
        )
        status_scrolled.set_child(status_view)

        self._load_tables()

    def _load_tables(self) -> None:
        try:
            tables = db.list_tables(self._conn)
        except pymysql.Error as e:
            self._show_toast(f"Failed to list tables: {e}")
            return
        for name in tables:
            row = Adw.ActionRow(title=name)
            check = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            row.add_prefix(check)
            row.set_activatable_widget(check)
            self._listbox.append(row)
            self._table_checks[name] = check

    def _set_all(self, value: bool) -> None:
        for check in self._table_checks.values():
            check.set_active(value)

    def _on_browse_clicked(self, _btn) -> None:
        dialog = Gtk.FileDialog(title="Choose output folder")
        dialog.select_folder(self.get_root(), None, self._on_folder_selected)

    def _on_folder_selected(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        self._output_folder = Path(folder.get_path())
        self._folder_row.set_subtitle(str(self._output_folder))

    def _show_toast(self, message: str, timeout: int = 3) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=message, timeout=timeout))

    def _append_status(self, line: str) -> None:
        end = self._status_buf.get_end_iter()
        self._status_buf.insert(end, line + "\n")
        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

    def _on_export_clicked(self, _btn) -> None:
        selected = [t for t, c in self._table_checks.items() if c.get_active()]
        if not selected:
            self._show_toast("Pick at least one table to export.")
            return
        if self._output_folder is None:
            self._show_toast("Pick an output folder.")
            return
        if not self._output_folder.is_dir() or not os.access(self._output_folder, os.W_OK):
            self._show_toast(f"Cannot write to {self._output_folder}.")
            return

        exported = 0
        failed: list[tuple[str, str]] = []
        total = len(selected)

        for i, table in enumerate(selected, start=1):
            try:
                meta = db.fetch_table_metadata(self._conn, self._conn_args["database"], table)
                content = render(meta)
                (self._output_folder / f"{table}.md").write_text(content, encoding="utf-8")
                exported += 1
                self._append_status(f"Exported {table} ({i} / {total})")
            except (pymysql.Error, OSError) as e:
                failed.append((table, str(e)))
                self._append_status(f"Failed: {table} — {e}")

        if failed:
            self._append_status(
                f"Done. Exported {exported} / {total} tables. "
                f"{len(failed)} failed: {', '.join(t for t, _ in failed)} (see above)."
            )
            self._show_toast(f"Done with {len(failed)} failure(s).")
        else:
            self._append_status(f"Done. Exported {exported} / {total} tables.")
            self._show_toast(f"Exported {exported} table(s).")
            config.save_last_connection(
                host=self._conn_args["host"],
                port=self._conn_args["port"],
                user=self._conn_args["user"],
                database=self._conn_args["database"],
            )


def install_excepthook() -> None:
    """Make sure unhandled exceptions reach stderr instead of disappearing
    into GLib's default handler."""

    def hook(exc_type, exc_value, exc_tb):
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = hook
