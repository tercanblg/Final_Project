from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt5.QtCore import pyqtSlot
from utils.manager.password_manager import save_login_file
import logging

logger = logging.getLogger(__name__)

class WebEnginePage(QWebEnginePage):
    
    def __init__(self, parent=None, table_widget=None, table_xpath=None, process_manager=None, pagination_xpath_label=None):
        super().__init__(parent)
        self.table_widget = table_widget
        self.table_xpath = table_xpath
        self.process_manager = process_manager
        self.pagination_xpath_label = pagination_xpath_label
        self.pagination_clicked = False
        self.username = None
        self.password = None

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if message.startswith("To Python>"):
            text = message.split(">")
            message_type = text[1]
            value = text[2]
            if message_type == "login_text_input":
                self.username = value
            elif message_type == "login_password_input" and self.password != value:
                self.password = value
                if self.username and self.password:
                    user_choice = self.show_save_credentials_dialog(self.view(), self.username, self.password)
                    if user_choice == QMessageBox.Yes:
                        logger.info("User chose to save the credentials.")
                        # Save the credentials for future use
                        login_info = {
                            'url': self.url().toString(),
                            'username': self.username,
                            'password': self.password,
                        }
                        save_success = save_login_file(login_info)
                        if not save_success:
                            msg = QMessageBox()
                            msg.setIcon(QMessageBox.Critical)
                            msg.setText("Error saving the credentials.")
                            msg.setWindowTitle("Save Credentials")
                            msg.exec_()
                    else:
                        logger.info("User chose not to save the credentials.")
            elif self.table_widget.isVisible():
                if message_type == "selectedText" and not self.pagination_clicked:
                    row = int(text[3])
                    col = self.process_manager.get_column_count() - 1
                    if row == 1:
                        self.process_manager.get_column(col).set_first_text(value)
                    if self.table_widget.rowCount() < row:
                        self.table_widget.setRowCount(row)
                    self.table_widget.setItem(row-1, col, QTableWidgetItem(value))
                elif message_type == "xpath" and not self.pagination_clicked:
                    self.process_manager.create_column(value)
                    if self.table_xpath.rowCount() < 1:
                        self.table_xpath.setRowCount(1)
                    count = self.process_manager.get_column_count()
                    if self.table_widget.columnCount() < count:
                        self.table_widget.setColumnCount(count)
                        self.table_xpath.setColumnCount(count)
                    col = count - 1
                    self.table_xpath.setItem(0, col, QTableWidgetItem(value))
                elif message_type == "xpathRel" and self.pagination_clicked:
                    actual_xpath = self.process_manager.pagination_xpath
                    if actual_xpath and actual_xpath != "fake" and value not in actual_xpath:
                        value = actual_xpath + "\n" + value    
                    self.process_manager.pagination_xpath = value
                    self.pagination_xpath_label.setText(value)

    @pyqtSlot(bool)
    def on_pagination_button_clicked(self, clicked):
        self.pagination_clicked = clicked

    def show_save_credentials_dialog(self, parent, username, password):
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(self.tr("Save credentials"))
        msg_box.setText(self.tr("Do you want to save your login credentials for this website? (The scraper will fill in the login form for you)"))
        msg_box.setInformativeText(f"{self.tr('Username')}: {username}\n{self.tr('Password')}: {'*' * len(password)}")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)

        return msg_box.exec_()
