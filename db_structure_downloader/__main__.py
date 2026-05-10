# db_structure_downloader/__main__.py
"""Entry point: `python -m db_structure_downloader`."""

from db_structure_downloader.gui import App


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
