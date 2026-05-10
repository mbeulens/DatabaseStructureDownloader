"""Entry point: `python -m db_structure_downloader`."""

import sys

from db_structure_downloader.gui import DbStructureApp, install_excepthook


def main() -> int:
    install_excepthook()
    return DbStructureApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
