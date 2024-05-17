from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QFormLayout, QApplication,
    QRadioButton, QComboBox, QGroupBox, QSpacerItem, QSizePolicy, QMessageBox, QStyleOption, QStyle
)
from PyQt5.QtCore import Qt, QLocale
import json
from utils.manager.password_manager import clear_stored_passwords
from utils.manager.template_manager import clear_stored_templates
from exceptions.file_exceptions import FileDeletionException
from static import background_path
from PyQt5.QtGui import QPainter
from utils.manager.process_manager import clear_process_history
from . constants import SETTINGS_FILE, LANGUAGES, RESTART_CODE

SEARCH_ENGINES = {
    "Google": ["https://www.google.com/search?q=", "https://www.google.com"],
    "Ecosia": ["https://www.ecosia.org/search?q=", "https://www.ecosia.org"],
    "DuckDuckGo": ["https://duckduckgo.com/?q=", "https://duckduckgo.com/"]
}

default_engine = next(iter(SEARCH_ENGINES.keys()))
default_settings = {
    "search_engine": SEARCH_ENGINES[default_engine][0], 
    "home_page": SEARCH_ENGINES[default_engine][1],
    "locale": QLocale().name().split('_')[0]
}

class SettingsTab(QWidget):
    def __init__(self, parent=None, settings=None, processes_tab=None, main_window=None, app=None):
        super().__init__(parent)

        self.settings = settings
        self.processes_tab = processes_tab
        self.main_window = main_window
        self.app = app

        # Create the UI elements
        self.search_engine_radio = QRadioButton(self.tr("Search Engine Home Page"))
        self.custom_home_page_radio = QRadioButton(self.tr("Custom Home Page"))
        self.search_engine_combo = QComboBox(self)

        self.home_page_edit = QLineEdit(self)
        self.custom_home_page_radio.toggled.connect(self.home_page_edit.setEnabled)
        self.search_engine_radio.clicked.connect(self.save_settings)

        self.clear_passwords_button = QPushButton(self.tr("Clear Stored Passwords"), self)
        self.clear_passwords_button.clicked.connect(self.clear_passwords)

        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded_json = json.load(f)

                if "search_engine" in loaded_json and "home_page" in loaded_json and "locale" in loaded_json:
                    # Both "search_engine" and "home_page" keys exist in the JSON object
                    self.settings.update(loaded_json)
                    self.check_values()
                else:
                    self.settings = default_settings
                    self.check_values()
                    self.save_json()
        except FileNotFoundError:
            self.check_values()
            self.save_json()

        self.home_page_edit.setText(self.settings["home_page"])

        for engine, urls in SEARCH_ENGINES.items():
            self.search_engine_combo.addItem(engine, urls[0])
        self.search_engine_combo.setCurrentText(self.get_search_engine_name())

        self.search_engine_combo.currentIndexChanged.connect(self.save_settings)

        save_button = QPushButton(self.tr("Save"), self)
        save_button.clicked.connect(self.save_settings)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        home_page_group = QGroupBox(self.tr("Browser Settings"))
        home_page_layout = QVBoxLayout()
        home_page_layout.addWidget(self.search_engine_radio)
        home_page_layout.addWidget(self.custom_home_page_radio)

        edit_layout = QHBoxLayout()
        edit_layout.addWidget(self.home_page_edit)
        edit_layout.addWidget(save_button)
        home_page_layout.addLayout(edit_layout)

        button_layout = QVBoxLayout()
        button_layout.addLayout(home_page_layout)

        self.search_engine_layout = QHBoxLayout()
        self.search_engine_layout.addWidget(QLabel(self.tr("Search Engine:")))
        self.search_engine_layout.addWidget(self.search_engine_combo)
        home_page_layout.addLayout(self.search_engine_layout)

        home_page_group.setLayout(button_layout)

        form_layout.addRow(home_page_group)

        password_manager_group = QGroupBox()
        password_manager_label = QLabel(self.tr("Password Manager:"))
        password_manager_layout = QHBoxLayout()
        password_manager_layout.addWidget(password_manager_label)
        password_manager_layout.addWidget(self.clear_passwords_button)
        password_manager_group.setLayout(password_manager_layout)
        form_layout.addRow(password_manager_group)

        self.clear_templates_button = QPushButton(self.tr("Clear Stored Templates"), self)
        self.clear_templates_button.clicked.connect(self.clear_templates)

        template_manager_group = QGroupBox()
        template_manager_label = QLabel(self.tr("Template Manager:"))
        template_manager_layout = QHBoxLayout()
        template_manager_layout.addWidget(template_manager_label)
        template_manager_layout.addWidget(self.clear_templates_button)
        template_manager_group.setLayout(template_manager_layout)
        form_layout.addRow(template_manager_group)


        self.clear_processes_button = QPushButton(self.tr("Clear Process History"), self)
        self.clear_processes_button.clicked.connect(self.clear_processes)

        process_manager_group = QGroupBox()
        process_manager_label = QLabel(self.tr("Process Manager:"))
        process_manager_layout = QHBoxLayout()
        process_manager_layout.addWidget(process_manager_label)
        process_manager_layout.addWidget(self.clear_processes_button)
        process_manager_group.setLayout(process_manager_layout)
        form_layout.addRow(process_manager_group)

        self.language_combo = QComboBox(self)
        for language, locale in LANGUAGES.items():
            self.language_combo.addItem(language, locale)

        self.language_combo.setCurrentIndex(self.language_combo.findData(self.settings["locale"]))
        self.language_combo.currentIndexChanged.connect(self.save_settings)

        user_settings_group = QGroupBox()
        language_label = QLabel(self.tr("Language:"))
        language_layout = QHBoxLayout()
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        user_settings_group.setLayout(language_layout)
        form_layout.addRow(user_settings_group)

        spacer_item = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        form_layout.addItem(spacer_item)

        widget = QWidget()
        widget.setLayout(form_layout)

        # Set the maximum width of the widget to 600 pixels
        widget.setMaximumWidth(600)

        layout.addWidget(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self.setStyleSheet(f"""
            SettingsTab {{
                background-image: url({background_path});
                background-repeat: no-repeat;
                background-position: center;
            }}
        """)

        dropdown_style = """
            QListView {
                selection-background-color: #8573a0;
            }
        """

        self.search_engine_combo.view().setStyleSheet(dropdown_style)
        self.language_combo.view().setStyleSheet(dropdown_style)

    def check_values(self):
        # Check if the search engine is in the SEARCH_ENGINES dictionary
        if self.settings["home_page"] and self.settings["home_page"] not in [engine[1][1] for engine in SEARCH_ENGINES.items()]:
            self.custom_home_page_radio.setChecked(True)
            self.home_page_edit.setEnabled(True)
        elif self.settings["search_engine"] in [engine[1][0] for engine in SEARCH_ENGINES.items()]:
            self.search_engine_radio.setChecked(True)
            self.home_page_edit.setEnabled(False)
        else:
            # Save the default search engine URL in the settings file
            search_engine = self.get_search_engine_name()
            self.settings["search_engine"] = SEARCH_ENGINES[search_engine][0]
            self.save_json()
            self.search_engine_radio.setChecked(True)
            self.home_page_edit.setEnabled(False)
        self.home_page_edit.setText(self.settings["home_page"])

    def get_search_engine_name(self):
        for i in range(self.search_engine_combo.count()):
            if self.settings["search_engine"] and self.settings["search_engine"].startswith(self.search_engine_combo.itemData(i)):
                return self.search_engine_combo.itemText(i)
            if self.settings["home_page"] and self.settings["home_page"] != "":
                for engine, value in SEARCH_ENGINES.items():
                    url = self.settings["home_page"]
                    if url in value[1]:
                        return engine
        return next(iter(SEARCH_ENGINES)) # Return the first search engine
    
    def save_json(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f)

    def save_settings(self):
        # Update the settings dictionary with the new values
        if self.custom_home_page_radio.isChecked():
            self.settings["home_page"] = self.home_page_edit.text()
            self.settings["search_engine"] = self.search_engine_combo.currentData()
        else:
            self.settings["search_engine"] = self.search_engine_combo.currentData()
            self.settings["home_page"] = self.get_home_page_url()
        
        if self.settings["locale"] != self.language_combo.currentData():
            self.settings["locale"] = self.language_combo.currentData()

            # Prompt the user to restart the application
            reply = QMessageBox.question(
                self,
                self.tr("Restart Required"),
                self.tr("Language change will take effect after restart. Do you want to restart now?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Restart the application
                self.check_values()
                self.save_json()

                self.main_window.close()
                self.app.quit()
                QApplication.instance().exit(RESTART_CODE)

        # Save the settings to the file
        self.check_values()
        self.save_json()

        if not self.custom_home_page_radio.isChecked():
            search_engine = self.get_search_engine_name()
            self.settings["search_engine"] = SEARCH_ENGINES[search_engine][0]
            self.settings["home_page"] = SEARCH_ENGINES[search_engine][1]

        self.home_page_edit.clearFocus()

    def get_home_page_url(self):
        for engine, urls in SEARCH_ENGINES.items():
            if self.search_engine_radio.isChecked() and self.settings["search_engine"].startswith(urls[0]):
                return urls[1]
        return self.settings["home_page"]

    # Unused
    def reset_settings(self):
        # Reset the settings dictionary to the defaults
        self.settings = default_settings
        self.check_values()
        self.save_json()

        # Update the UI elements
        self.search_engine_combo.setCurrentText(self.get_search_engine_name())
        self.home_page_edit.setText(self.settings["home_page"])
        self.custom_home_page_radio.setChecked(self.settings["search_engine"] is None)
        self.search_engine_radio.setChecked(not self.custom_home_page_radio.isChecked())

    def clear_passwords(self):
        try:
            msg = self.show_message()
            message = ""
            if clear_stored_passwords():
                message = self.tr("All stored credentials have been removed.")
            else:
                message = self.tr("No credentials were found.")
            msg.setText(message)
            msg.setIcon(QMessageBox.Information)
            msg.exec_()
        except FileDeletionException as e:
            msg = self.show_message()
            msg.setText(str(e))
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()

    def clear_templates(self):
        try:
            msg = self.show_message()
            message = ""
            if clear_stored_templates():
                message = self.tr("All stored templates have been removed.")
            else:
                message = self.tr("No templates were found.")
            msg.setText(message)
            msg.setIcon(QMessageBox.Information)
            msg.exec_()
        except FileDeletionException as e:
            msg = self.show_message()
            msg.setText(str(e))
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()

    def clear_processes(self):
        try:
            msg = self.show_message()
            message = ""
            if clear_process_history():
                message = self.tr("Process history have been removed.")
            else:
                message = self.tr("No process history was found.")
            msg.setText(message)
            msg.setIcon(QMessageBox.Information)
            msg.exec_()
            self.processes_tab.load_data()
        except FileDeletionException as e:
            msg = self.show_message()
            msg.setText(str(e))
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()
            self.processes_tab.load_data()

    def show_message(self):
        msg = QMessageBox(self)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setWindowTitle(self.tr("Information"))
        return msg
    
    def paintEvent(self, _):
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)
