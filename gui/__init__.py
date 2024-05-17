from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from PyQt5.QtGui import QIcon, QFont
from utils.manager.password_manager import create_key
import sys
import io
from static import icon_path
from PyQt5.QtCore import QTranslator, QLocale
import os
import json
from . constants import SETTINGS_FILE, LANGUAGES, RESTART_CODE
import logging
from utils.manager.file_manager import get_folder_path
import platform

def main():

    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a console handler to print logs in the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create a file handler to write logs to a file
    file_handler = logging.FileHandler(f"{get_folder_path('logs')}/application.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Password manager key
    try:
        create_key()
    except Exception as e:
        logger.error(f"Error creating password manager key: {e}")

    # Set 'utf-8' encoding
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            logger.info("stdout encoding set to 'utf-8'.")
        else:
            logger.warning("Warning: stdout has no buffer. utf-8 encoding was not set.")
    except Exception as e:
        logger.warning(f"Warning: Error setting the 'utf-8' encoding. {e}")

    # Run the application
    app = QApplication([])
    exit_code = RESTART_CODE
    translator = QTranslator(app)

    while exit_code == RESTART_CODE:
        logger.info("Application started.")

        app.removeTranslator(translator)

        # Load settings
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            logger.info("Settings loaded successfully.")
        except FileNotFoundError:
            logger.warning("Settings file not found. Creating a new one.")
            settings = {}
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            settings = {}

        # Translate the app
        if 'locale' not in settings:
            system_locale = QLocale.system()
            language = system_locale.languageToString(system_locale.language())
            if language in LANGUAGES:
                settings['locale'] = LANGUAGES[language]
            else:
                settings['locale'] = 'en'

        locale = settings.get('locale')
        if locale != 'en':
            translator = QTranslator(app)
            translation_file = os.path.abspath(f"translations/translations_{locale}.qm")
            if translator.load(QLocale(locale), translation_file):  # Load the specified locale (if not found, don't translate)
                app.installTranslator(translator)
                logger.info(f"Translator loaded successfully: {locale}")

        # Create the main window
        try:
            if platform.system() == 'Darwin':
                app.setStyle('Macintosh')
            else:
                stylesheet = """
                QWidget {
                    font-size: 16px;
                    font-family: 'Helvetica';
                }
                QLineEdit:focus {
                    border: 1px solid #8573a0;
                }
                QTableView::item:selected {
                    background-color: #f1edff;
                    color: black;
                }
                QProgressBar {
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #dbd0fb;
                }
                QMenu::item:selected {
                    background-color: #8573a0;
                }
                QSpinBox {
                    border: 1px solid #808080;
                }
                QSpinBox:focus {
                    border: 1px solid #8573a0;
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    width: 20px;
                }
                QSpinBox::up-arrow, QSpinBox::down-arrow {
                    width: 10px;
                    height: 10px;
                }
                """
                app.setStyleSheet(stylesheet)
                app.setStyle('Fusion')
                font = QFont("Helvetica", 8)
                font.setStyleHint(QFont.Helvetica, QFont.PreferAntialias)
                app.setFont(font)
            
            app.setWindowIcon(QIcon(icon_path))
            window = MainWindow(app)
            window.show()
            logger.info("Main window created successfully.")
            exit_code = app.exec_()
            logger.info(f"Application closed: {exit_code}")
        except Exception as e:
            logger.error(f"Error creating main window: {e}")
            exit_code = RESTART_CODE

    sys.exit(exit_code)