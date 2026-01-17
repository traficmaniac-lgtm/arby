from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


def bind_shortcut(
    parent: QtWidgets.QWidget,
    sequence: QtGui.QKeySequence | str,
    callback,
) -> QtWidgets.QShortcut:
    shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(sequence), parent)
    shortcut.setContext(QtCore.Qt.ApplicationShortcut)
    shortcut.activated.connect(callback)
    return shortcut
