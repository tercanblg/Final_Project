from PyQt5.QtCore import QUrl, Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QFontMetrics
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame
from utils.manager.template_manager import get_domain
from PyQt5.QtWidgets import QMenu, QAction
import logging

logger = logging.getLogger(__name__)

class TemplateThumbnail(QFrame):
    clicked = pyqtSignal()
    deleted = pyqtSignal(str)

    def __init__(self, template, index, parent=None):
        super().__init__(parent)
        self.template = template
        self.index = index

        self.setFixedSize(QSize(100, 100))
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout()

        # Add website logo
        self.logo = QLabel(self)
        self.logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo)

        # Add domain name
        domain = get_domain(template["url"])
        domain_label = QLabel(domain, self)
        domain_label.setAlignment(Qt.AlignCenter)

        # Set elide mode
        font_metrics = QFontMetrics(domain_label.font())
        elided_text = font_metrics.elidedText(domain, Qt.ElideRight, 75)
        domain_label.setText(elided_text)

        layout.addWidget(domain_label)

        self.setLayout(layout)

        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.set_window_icon_from_response)
        self.nam.get(QNetworkRequest(QUrl(f"https://{domain}/favicon.ico")))

        # Set background color
        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: #FFFFFF; border-radius: 16px;")

    def set_window_icon_from_response(self, http_response):
        try:
            if http_response.error() == QNetworkReply.NoError:
                pixmap = QPixmap()
                if pixmap.loadFromData(http_response.readAll()):
                    pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.logo.setPixmap(pixmap)
                else:
                    self.load_default_favicon()
            else:
                self.load_default_favicon()
        except Exception as e:
            logger.warning(f"Warning: Error getting the favicon of a template. {e}")
            self.load_default_favicon()

    def load_default_favicon(self):
        try:
            pixmap = QPixmap("static/favicon.ico")
            if not pixmap.isNull():
                pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo.setPixmap(pixmap)
        except Exception as e:
            logger.warning(f"Warning: Error loading default favicon: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        delete_action = QAction('Delete', self)
        delete_action.triggered.connect(self.delete_template)

        context_menu.addAction(delete_action)

        context_menu.setStyleSheet("""
        QMenu::item:selected {
            background-color: #000000;
        }
        """)

        context_menu.exec_(event.globalPos())

    def delete_template(self):
        self.deleted.emit(str(self.template["id"]))