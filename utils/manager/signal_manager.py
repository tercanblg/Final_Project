from PyQt5.QtCore import QObject, pyqtSignal, QVariant

class SignalManager(QObject):
    process_signal = pyqtSignal(QVariant, QVariant, QVariant)
    pagination_signal = pyqtSignal(bool)
    table_items_signal = pyqtSignal(dict)
    browser_signal = pyqtSignal()
    tab_signal = pyqtSignal()
