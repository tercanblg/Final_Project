from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout

class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        label = QLabel(self.tr("Please wait for the process to finish..."), self)
        layout.addWidget(label)

        self.setWindowTitle("Scraping Interface")
