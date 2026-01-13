import sys
from PySide6.QtCore import QObject, QTimer

from neurotempo.ui.break_popup import BreakPopup  # used on Windows/Linux only


class BreakAlerter(QObject):
    def __init__(self):
        super().__init__()
        self._popup_qt = None
        self._panel_macos = None  # keep reference alive

    def show_break(self, title: str, message: str):
        if sys.platform == "darwin":
            def _do():
                from neurotempo.core.break_popup_native import show_break_popup_center
                self._panel_macos = show_break_popup_center(title, message)
            QTimer.singleShot(0, _do)
            return

        # Windows/Linux
        if self._popup_qt is not None and self._popup_qt.isVisible():
            return

        def _do_qt():
            self._popup_qt = BreakPopup(title=title, message=message)
            self._popup_qt.show()
            self._popup_qt.raise_()
            # do NOT activateWindow()
        QTimer.singleShot(0, _do_qt)


_break_alerter = BreakAlerter()


def show_break_popup(title: str, message: str):
    _break_alerter.show_break(title, message)