"""Prefer Qt 6/PySide6; support existing PyQt5 installations as a fallback."""
import os
import sys

try:
    if os.environ.get('QT_API', '').lower() == 'pyqt5':
        raise ImportError('PyQt5 explicitly requested')
    from PySide6 import QtCore, QtGui, QtWidgets
    os.environ['QT_API'] = 'pyside6'
    BINDING = 'PySide6'
except ImportError:
    # Matplotlib detects already imported QtCore modules before consulting QT_API.
    # A broken/partial PySide6 install must not override the working fallback.
    for name in tuple(sys.modules):
        if name.startswith('PySide6.'):
            sys.modules.pop(name, None)
    from PyQt5 import QtCore, QtGui, QtWidgets
    os.environ['QT_API'] = 'pyqt5'
    BINDING = 'PyQt5'

Qt = QtCore.Qt
QSize = QtCore.QSize
QSignalBlocker = QtCore.QSignalBlocker
QFont, QPixmap, QPainter, QIcon, QKeySequence = (
    QtGui.QFont, QtGui.QPixmap, QtGui.QPainter, QtGui.QIcon, QtGui.QKeySequence)
QAction = QtGui.QAction if hasattr(QtGui, 'QAction') else QtWidgets.QAction
QShortcut = QtGui.QShortcut if hasattr(QtGui, 'QShortcut') else QtWidgets.QShortcut
QApplication = QtWidgets.QApplication
QComboBox, QLabel, QLineEdit, QPushButton = (
    QtWidgets.QComboBox, QtWidgets.QLabel, QtWidgets.QLineEdit, QtWidgets.QPushButton)
QSizePolicy, QSlider, QSpinBox, QWidget = (
    QtWidgets.QSizePolicy, QtWidgets.QSlider, QtWidgets.QSpinBox, QtWidgets.QWidget)
QGridLayout, QVBoxLayout, QTabWidget = (
    QtWidgets.QGridLayout, QtWidgets.QVBoxLayout, QtWidgets.QTabWidget)
QFileDialog, QMainWindow, QMessageBox = (
    QtWidgets.QFileDialog, QtWidgets.QMainWindow, QtWidgets.QMessageBox)
