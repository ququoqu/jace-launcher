"""Write crashes to <data folder>/crash.log, so a window that just closes still leaves a trace.

- Python errors (also in Qt slots and background threads) are logged and shown in a message box.
- Hard crashes (e.g. inside Qt) are logged by faulthandler with a Python stack.
"""
import faulthandler
import sys
import threading
import time
import traceback

from jace import APP_VERSION
from jace.config import DATA_DIR

LOG = DATA_DIR / "crash.log"
_file = None


def install():
    global _file
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if LOG.exists() and LOG.stat().st_size > 1_000_000:      # keep it small
            LOG.replace(LOG.with_suffix(".old.log"))
        _file = open(LOG, "a", encoding="utf-8", buffering=1)
        _file.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} Jace Launcher {APP_VERSION} on {sys.platform} started\n")
        faulthandler.enable(file=_file, all_threads=True)
    except OSError:
        return
    sys.excepthook = _hook
    threading.excepthook = lambda a: _hook(a.exc_type, a.exc_value, a.exc_traceback, a.thread)


def _hook(exc_type, exc, tb, thread=None):
    if exc_type is SystemExit:
        return
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    where = f" in thread {thread.name}" if thread else ""
    try:
        _file.write(f"--- {time.strftime('%H:%M:%S')} error{where}\n{text}")
    except Exception:  # noqa: BLE001
        pass
    if thread is None or thread is threading.main_thread():
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                QMessageBox.critical(None, "Jace Launcher hit a problem",
                                     f"{exc_type.__name__}: {exc}\n\nDetails were saved to:\n{LOG}")
        except Exception:  # noqa: BLE001
            pass


def note(text: str):
    """Add a line to the log (e.g. how setup ended)."""
    try:
        if _file:
            _file.write(f"--- {time.strftime('%H:%M:%S')} {text}\n")
    except Exception:  # noqa: BLE001
        pass


def watch_quit(app):
    """Log why the app quits, with the Python stack that asked for it."""
    def last_window():
        note("last window closed")

    def about_to_quit():
        note("quitting\n" + "".join(traceback.format_stack(limit=12)))
    app.lastWindowClosed.connect(last_window)
    app.aboutToQuit.connect(about_to_quit)
