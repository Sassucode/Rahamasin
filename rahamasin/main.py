import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='RAHAMASIN desktop ONDO research')
    parser.add_argument('--db',type=Path,default=Path.home()/'.rahamasin'/'rahamasin.sqlite3')
    parser.add_argument('--smoke-test',action='store_true',help='Create the UI offscreen and exit')
    parser.add_argument('--screenshot',type=Path,help='Save a screenshot during smoke test')
    args = parser.parse_args()
    if args.smoke_test:
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6 import QtWidgets, QtCore
    from .storage import Repository
    from .ui.window import Window
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName('Rahamasin')
    window = Window(Repository(args.db)); window.show()
    if args.smoke_test:
        def finish():
            if args.screenshot:
                window.grab().save(str(args.screenshot))
            app.quit()
        QtCore.QTimer.singleShot(500,finish)
    else:
        QtCore.QTimer.singleShot(0,window.start_live)
    return app.exec()

if __name__ == '__main__':
    raise SystemExit(main())
