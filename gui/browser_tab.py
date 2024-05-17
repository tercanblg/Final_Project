from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidgetItem, QScrollArea, QSizePolicy, QHeaderView, QInputDialog, QMenu, QAction, QAbstractItemView, QMessageBox, QCheckBox, QStyle, QStyleOption, QLabel, QSpinBox, QTextEdit, QToolButton
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from PyQt5.QtCore import QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QPainter
import web.javascript_strings as jss
from utils.pyqt5_utils.web_engine_page import WebEnginePage
from scrapers.scrapy_scraper import ScrapyScraper
import threading
from utils.pyqt5_utils.custom_table_widget import CustomTableWidget
from utils.manager.template_manager import save_template, get_column_data_from_template
import static
import random
import logging

COLUMN_COUNT = 0
PAGINATION_WIDGET_WIDTH_PERCENTAGE = 1/3

logger = logging.getLogger(__name__)

class BrowserTab(QWidget):

    def __init__(self, parent=None, process_manager=None, signal_manager=None, settings=None):
        super().__init__(parent)
        self.process_manager = process_manager
        self.signal_manager = signal_manager
        self.settings = settings

        self.browser_tab_layout = QVBoxLayout(self)
        self.browser_tab_layout.addWidget(QWidget(self))

        # Use self.tr() to translate the constants
        self.PLACEHOLDER_TEXT = self.tr("Search or enter a URL")
        self.PAGINATION_OFF_TEXT = self.tr("Click to select the pagination button...")
        self.PAGINATION_ON_TEXT = self.tr("Click to stop selecting the pagination button...")

        # Create a browser window
        self.browser = QWebEngineView(self)

        # Create a widget for scraping
        self.scrape_widget = QWidget(self)
        self.scrape_widget_layout = QVBoxLayout(self.scrape_widget)
        self.horizontal_scrape_layout = QHBoxLayout()
        self.scrape_tables_layout = QVBoxLayout()
        self.scrape_widget.hide()

        # Widget to manage pagination
        self.pagination_widget = QWidget(self)
        self.pagination_layout = QVBoxLayout(self.pagination_widget)
        self.pagination_widget.hide()

        self.horizontal_scrape_layout.addWidget(self.pagination_widget)

        self.pagination_checkbox = QCheckBox(self.PAGINATION_OFF_TEXT, self)
        self.pagination_layout.addWidget(self.pagination_checkbox)
        self.pagination_checkbox.clicked.connect(self.set_pagination)

        self.pagination_xpath_input = QTextEdit(self)
        self.pagination_xpath_input.setPlaceholderText(self.tr("Click on the pagination buttons or enter the XPaths, one per line"))
        self.pagination_xpath_input.setEnabled(False)
        self.pagination_xpath_input.textChanged.connect(self.handle_pagination_changed)
        self.pagination_layout.addWidget(self.pagination_xpath_input)

        # Add a label and a spin box to enter the maximum pages to be scraped
        # along with a checkbox to set automation on or off and a help button in a horizontal layout
        self.second_row_layout = QHBoxLayout()

        self.max_pages_label = QLabel(self.tr("Pages to scrape:"))
        self.second_row_layout.addWidget(self.max_pages_label)
        self.max_pages_input = QSpinBox(self)
        self.max_pages_input.setMinimum(0)
        self.max_pages_input.setMaximum(1000000)
        self.max_pages_input.setSpecialValueText(self.tr("Unlimited"))
        self.second_row_layout.addWidget(self.max_pages_input)

        # Add stretch to push the remaining widgets to the right
        self.second_row_layout.addStretch()

        self.automated_checkbox = QCheckBox(self.tr("Run in the background"), self)
        self.automated_checkbox.setChecked(True)  # set default as automated
        self.second_row_layout.addWidget(self.automated_checkbox)

        self.help_button = QToolButton(self)
        self.help_button.setText('?')
        self.help_button.clicked.connect(self.show_help_dialog)
        self.second_row_layout.addWidget(self.help_button)

        # Add the second row to the pagination layout
        self.pagination_layout.addLayout(self.second_row_layout)

        # Create a scroll area to hold the table widget
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scrape_tables_layout.addWidget(self.scroll_area)

        # Create a table widget to show scraped data
        self.table_widget = CustomTableWidget(self)
        self.table_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table_widget.setColumnCount(COLUMN_COUNT)
        self.table_widget.horizontalHeader().customContextMenuRequested.connect(self.create_horizontal_header_context_menu)
        self.table_widget.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(lambda pos: self.create_table_context_menu(pos, self.table_widget))
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Signal to update the table widget
        self.signal_manager.table_items_signal.connect(self.set_table_data)

        # Set the table widget as the scroll area's widget
        self.scroll_area.setWidget(self.table_widget)

        # Allow users to edit column headers
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.horizontalHeader().setSectionsMovable(False)
        self.table_widget.horizontalHeader().sectionDoubleClicked.connect(self.change_column_header)

        if self.table_widget.rowCount() == 0:
            self.table_widget.setRowCount(1)
        if self.table_widget.columnCount() == 0:
            self.table_widget.setColumnCount(1)
        self.table_widget.horizontalHeader().setVisible(True)

        # Get the row height
        row_height = self.table_widget.rowHeight(0)
        header_height = self.table_widget.horizontalHeader().height() + 4

        if self.table_widget.rowCount() == 1:
            self.table_widget.setRowCount(0)
        if self.table_widget.columnCount() == 0:
            self.table_widget.setColumnCount(COLUMN_COUNT)

        height_hint = header_height + row_height * 5

        self.scroll_area.setMinimumHeight(height_hint)
        self.scroll_area.setMaximumHeight(height_hint)

        # Create a second table to edit the xpath of each column
        self.table_xpath = CustomTableWidget(self)
        self.table_xpath.verticalHeader().setVisible(False)
        self.table_xpath.setMinimumHeight(row_height + 2)
        self.table_xpath.setMaximumHeight(row_height + 2)
        self.table_xpath.horizontalHeader().setVisible(False)
        self.table_xpath.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_xpath.cellChanged.connect(self.handle_cell_changed)
        self.table_xpath.customContextMenuRequested.connect(lambda pos: self.create_table_context_menu(pos, self.table_xpath))
        self.table_xpath.setContextMenuPolicy(Qt.CustomContextMenu)        

        self.scrape_tables_layout.addWidget(self.table_xpath)

        # Create a Scraping bar with buttons
        self.scrape_bar = QWidget(self)
        self.scrape_bar_layout = QHBoxLayout(self.scrape_bar)

        # Add a button to select the pagination element
        self.pagination_button = QPushButton(self.tr("Pagination"), self.scrape_widget)
        pagination_icon = QIcon(static.pagination_path)
        self.pagination_button.setIcon(pagination_icon)
        self.scrape_bar_layout.addWidget(self.pagination_button)

        # Add a button to save template
        self.save_template_button = QPushButton(self.tr("Save Template"), self.scrape_widget)
        save_icon = QIcon(static.save_path)
        self.save_template_button.setIcon(save_icon)
        self.scrape_bar_layout.addWidget(self.save_template_button)
        self.save_template_button.clicked.connect(self.save_current_template)
        
        # Add a button to download the table contents as an Excel file
        self.download_button = QPushButton(self.tr("Download Data"), self.scrape_widget)
        download_icon = QIcon(static.download_path)
        self.download_button.setIcon(download_icon)
        self.download_menu = QMenu(self.download_button)
        self.download_button.setMenu(self.download_menu)
        self.scrape_bar_layout.addWidget(self.download_button)

        self.download_excel_action = QAction(self.tr("Download Excel"), self)
        self.download_csv_action = QAction(self.tr("Download CSV"), self)
        self.download_json_action = QAction(self.tr("Download JSON"), self)
        self.download_xml_action = QAction(self.tr("Download XML"), self)

        self.download_menu.addAction(self.download_excel_action)
        self.download_menu.addAction(self.download_csv_action)
        self.download_menu.addAction(self.download_json_action)
        self.download_menu.addAction(self.download_xml_action)

        # Set language
        QWebEngineProfile.defaultProfile().setHttpAcceptLanguage(self.settings["locale"] if "locale" in self.settings else "en")
        page = WebEnginePage(self.browser, self.table_widget, self.table_xpath, self.process_manager, self.pagination_xpath_input)
        self.browser.setPage(page)
        page.runJavaScript(jss.START_JS)
        # Connect the urlChanged signal to update the URL field
        self.browser.urlChanged.connect(self.update_url_field)

        # Create a URL bar with navigation buttons
        self.navigation_bar = QWidget(self)
        self.navigation_bar_layout = QHBoxLayout(self.navigation_bar)
        self.back_button = QPushButton(self.navigation_bar)
        back_icon = QIcon(static.back_path)
        self.back_button.setIcon(back_icon)
        self.back_button.clicked.connect(self.browser.back)
        self.navigation_bar_layout.addWidget(self.back_button)

        self.forward_button = QPushButton(self.navigation_bar)
        forward_icon = QIcon(static.forward_path)
        self.forward_button.setIcon(forward_icon)
        self.forward_button.clicked.connect(self.browser.forward)
        self.navigation_bar_layout.addWidget(self.forward_button)

        self.refresh_button = QPushButton(self.navigation_bar)
        self.refresh_button.clicked.connect(self.refresh_browser)
        self.navigation_bar_layout.addWidget(self.refresh_button)

        refresh_icon = QIcon(static.refresh_path)
        self.refresh_button.setIcon(refresh_icon)

        self.home_button = QPushButton(self.navigation_bar)
        self.home_button.clicked.connect(self.load_homepage)
        self.navigation_bar_layout.addWidget(self.home_button)

        home_icon = QIcon(static.home_path)
        self.home_button.setIcon(home_icon)

        self.url_field = QLineEdit(self.navigation_bar)
        self.url_field.returnPressed.connect(self.load_url)
        self.navigation_bar_layout.addWidget(self.url_field)
        self.url_field.setPlaceholderText(self.PLACEHOLDER_TEXT)
        self.url_field.setClearButtonEnabled(True)

        self.browser_tab_layout.addWidget(self.navigation_bar, 0, Qt.AlignTop)

        self.load_homepage()
        self.browser_tab_layout.addWidget(self.browser, 1)

        # Create a button to toggle the scrape widget
        self.scrape_button = QPushButton(self.tr("Scrape"), self.navigation_bar)
        scraping_icon = QIcon(static.scraping_path)
        self.scrape_button.setIcon(scraping_icon)
        self.scrape_button.clicked.connect(self.toggle_scrape_widget)
        self.navigation_bar_layout.addWidget(self.scrape_button, 0, Qt.AlignRight)

        # Add the scrape widget at the bottom of the browser
        self.horizontal_scrape_layout.addLayout(self.scrape_tables_layout)
        self.scrape_widget_layout.addLayout(self.horizontal_scrape_layout)
        self.scrape_widget_layout.addWidget(self.scrape_bar)
        self.browser_tab_layout.addWidget(self.scrape_widget, 0)

        # Create a QTimer to check for new links every second
        self.timer = QTimer(self)

        self.browser.loadFinished.connect(lambda: self.browser.page().runJavaScript(jss.LOGIN_DETECTION_JS))
        self.browser.loadFinished.connect(self.handle_load_finished)

        self.pagination_button.clicked.connect(self.toggle_pagination)

        self.selected_template = None

        # Get the maximum width among the three buttons
        max_width = max(self.pagination_button.sizeHint().width(), self.save_template_button.sizeHint().width(), self.download_button.sizeHint().width()) + 20

        # Set the width of the three buttons to be the maximum width
        self.pagination_button.setFixedWidth(max_width)
        self.save_template_button.setFixedWidth(max_width)
        self.download_button.setFixedWidth(max_width)

        self.pagination_xpath_input.setMinimumWidth(int(height_hint * 0.75))
        self.pagination_xpath_input.setMaximumHeight(int(height_hint * 0.75))

        self.create_interaction_widget()

        self.wait_data = False

        self.setStyleSheet(f"""
            BrowserTab {{
                background-image: url({static.background_path});
                background-repeat: no-repeat;
                background-position: center;
            }}
        """)

        self.download_button.setStyleSheet("""
            QPushButton { text-align: center; }
        """)

        self.pagination_checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 52px;
                height: 32px;
            }
            QCheckBox::indicator:unchecked {
                image: url(static/off.png);
            }
            QCheckBox::indicator:checked {
                image: url(static/on.png);
            }
        """)

    def handle_load_finished(self, ok):
        # If the load was not successful and the scraping process is running, stop it
        if not ok and self.scrape_widget.isVisible():
            self.toggle_scrape_widget()

    def refresh_browser(self):
        self.browser.reload()
        self.browser.loadFinished.connect(lambda _: self.update_url_field(self.browser.url()))

    def enable_elements_layout(self, layout, enable):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.setEnabled(enable)

    def export_data(self, action):
        self.process_manager.file_format = action.text().split(" ")[-1].lower()

    def set_pagination(self, state):
        page = self.browser.page()
        if state == 1:
            self.signal_manager.pagination_signal.emit(True)
            self.pagination_xpath_input.setEnabled(True)
            self.pagination_checkbox.setText(self.PAGINATION_ON_TEXT)
            page.runJavaScript(jss.SELECT_PAGINATION_JS)
        else:
            page.runJavaScript(jss.DISABLE_PAGINATION_JS)
            self.signal_manager.pagination_signal.emit(False)
            self.pagination_xpath_input.setEnabled(False)
            self.pagination_checkbox.setText(self.PAGINATION_OFF_TEXT)

    def toggle_pagination(self):
        if self.pagination_widget.isVisible():
            self.pagination_widget.hide()
            if self.process_manager.pagination_xpath:
                self.remove_background("", "green")
            self.browser.page().runJavaScript(jss.DISABLE_PAGINATION_JS)
            self.pagination_xpath_input.setText("")
            self.pagination_checkbox.setChecked(False)
            self.pagination_xpath_input.setEnabled(False)
            self.pagination_checkbox.setText(self.PAGINATION_OFF_TEXT)
            self.signal_manager.pagination_signal.emit(False)
            self.process_manager.pagination_xpath = None
            self.process_manager.file_name = None

        else:
            self.pagination_widget.show()
            widget_width = self.scrape_widget.width()
            widget_width = int(widget_width * (1 / 3))

            self.pagination_widget.setFixedWidth(widget_width)
        
    def get_column_titles(self):
        column_titles = []
        if self.scrape_widget.isVisible():
            column_titles = [self.table_widget.horizontalHeaderItem(col).text() 
                        if self.table_widget.horizontalHeaderItem(col) else str(self.process_manager.get_column(col).get_visual_index())
                        for col in range(self.table_widget.columnCount())][:self.process_manager.get_column_count()]
        return column_titles

    def load_homepage(self):
        self.browser.load(QUrl(self.settings["home_page"]))

    def save_current_template(self):
        if save_template(self.url_field.text(), self.process_manager, self.get_column_titles()):
            self.show_message(self.tr("Template saved successfully"))
        else:
            self.show_message(self.tr("Error saving template"))

    def show_message(self, message):
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Information"))
        msg.setText(message)
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)

        msg.exec_()

    def load_url(self):
        url = self.url_field.text()
        if " " in url or "." not in url:
            # If the URL contains spaces or doesn't contain a dot, search for it
            url = self.settings["search_engine"] + url.replace(" ", "+")
        elif not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        self.browser.load(QUrl(url))

    def update_url_field(self, url):
        self.url_field.setText(url.toString())
        self.scrape_widget.setVisible(False)
        self.browser.page().runJavaScript(jss.START_JS)
        self.browser.page().runJavaScript(jss.UNHIGHLIGHT_TEXT_JS)
        self.process_manager.clear_columns()
        self.pagination_checkbox.setChecked(False)
        self.pagination_xpath_input.setEnabled(False)
        self.pagination_checkbox.setText(self.PAGINATION_OFF_TEXT)
        self.signal_manager.pagination_signal.emit(False)
        self.pagination_xpath_input.setText("")
        self.pagination_widget.setVisible(False)

    def toggle_scrape_widget(self):
        # Get the page
        page = self.browser.page()

        # Toggle the visibility of the scrape widget
        self.scrape_widget.setVisible(not self.scrape_widget.isVisible())

        # Disable links if the scrape widget is visible
        if self.scrape_widget.isVisible():
            self.table_widget.clear()
            self.table_xpath.clear()
            self.table_widget.setRowCount(0)
            self.table_xpath.setRowCount(0)
            self.table_widget.setColumnCount(COLUMN_COUNT)
            self.table_xpath.setColumnCount(COLUMN_COUNT)
            self.timer.singleShot(100, self.disable_links)
        # Enable links if the scrape widget is not visible
        else:
            self.timer.stop()
            page.runJavaScript(jss.DISABLE_PAGINATION_JS)
            page.runJavaScript(jss.ENABLE_LINKS_JS)
            page.runJavaScript(jss.UNHIGHLIGHT_TEXT_JS)
            self.process_manager.clear_columns()
            self.pagination_checkbox.setChecked(False)
            self.pagination_xpath_input.setEnabled(False)
            self.pagination_checkbox.setText(self.PAGINATION_OFF_TEXT)
            self.signal_manager.pagination_signal.emit(False)
            self.pagination_xpath_input.setText("")
            self.pagination_widget.setVisible(False)

    # Create a loop that continuously disables all links in the page
    def disable_links(self):
        self.browser.page().runJavaScript(jss.HIGHIGHT_TEXT_JS)
        self.browser.page().runJavaScript(jss.DISABLE_LINKS_JS)

    def change_column_header(self, index):
        current_header = self.table_widget.horizontalHeaderItem(index)
        new_header_text, ok = QInputDialog.getText(self, self.tr("Edit Column Header"), self.tr("Enter new column header text:"), QLineEdit.Normal, current_header.text() if current_header else "")
        if ok and new_header_text:
            new_header = QTableWidgetItem(new_header_text)
            self.table_widget.setHorizontalHeaderItem(index, new_header)

    @pyqtSlot(dict)
    def set_table_data(self, items):
        for i, key in enumerate(items.keys()):
            for j, item in enumerate(items[key]):
                if self.table_widget.rowCount() < j+1:
                    self.table_widget.setRowCount(j+1)
                self.table_widget.setItem(j, i, QTableWidgetItem(item))
        
        if self.wait_data and (self.table_widget.columnCount() == len(items.keys()) or items == {}):
            self.wait_data = False
            self.signal_manager.tab_signal.emit()
    
    def preview_scrape(self, html):
        thread = threading.Thread(target=self.thread_preview_scrape, args=(self.browser.url().toString(), self.get_column_titles(), self.process_manager.get_all_xpaths(), html, self.process_manager.get_all_first_texts()), daemon=True)
        thread.start()

    def thread_preview_scrape(self, url, column_titles, xpaths, html, selected_texts):
        scraper = ScrapyScraper()
        try:
            items = scraper.scrape(url, column_titles, xpaths, html, max_items=5)
            actual_column_titles = self.get_column_titles()
            if items is not None and len(items) > 0 and column_titles == actual_column_titles:
                for i, key in enumerate(items.keys()):
                    if len(items[key]) == 0 or all(item == "" for item in items[key]):
                        items[key] = [selected_texts[i]] + [""] * 4
                self.signal_manager.table_items_signal.emit(items)
            elif self.wait_data:
                self.signal_manager.table_items_signal.emit({})
        except Exception as e:
            logger.error("Error: No items found. " + str(e))
            if self.wait_data:
                self.signal_manager.table_items_signal.emit({})

    def handle_cell_changed(self, row, column):
        if self.scrape_widget.isVisible():
            last_xpath = self.process_manager.get_column(column).get_xpath()
            if last_xpath:
                self.remove_background(last_xpath, "red")
            xpath = self.table_xpath.item(row, column).text()
            self.process_manager.get_column(column).set_xpath(xpath)
            self.paint_background(xpath, "red")
            self.browser.page().toHtml(self.preview_scrape)

    def handle_pagination_changed(self):
        pagination_xpath = self.pagination_xpath_input.toPlainText()
        self.process_manager.pagination_xpath = pagination_xpath
        xpaths = pagination_xpath.split("\n")
        
        self.remove_background("", "green")
        for xpath in xpaths:
            self.paint_background(xpath, "green")

    def remove_background(self, xpath, color):
        js_code = f"var xpath = '{xpath}'; var color = '{color}'; {jss.REMOVE_BACKGROUND_JS}"
        self.browser.page().runJavaScript(js_code)

    def paint_background(self, xpath, color):
        js_code = f"var xpath = '{xpath}'; var color = '{color}'; {jss.PAINT_BACKGROUND_JS}"
        self.browser.page().runJavaScript(js_code)
    
    def remove_column(self, column):
        xpath = self.table_xpath.item(0, column).text()
        self.table_widget.removeColumn(column)
        self.table_xpath.removeColumn(column)
        self.process_manager.remove_column(column)
        for col in self.process_manager.get_columns():
            if col.get_visual_index() > column:
                col.set_visual_index(col.get_visual_index() - 1)
        self.remove_background(xpath, "red")

        self.browser.page().toHtml(self.preview_scrape)

        # Expand remaining columns to occupy all available space
        total_width = self.table_widget.width()
        num_columns = self.table_widget.columnCount()
        if num_columns > 0:
            for i in range(num_columns):
                self.table_widget.setColumnWidth(i, total_width // num_columns)

    def create_horizontal_header_context_menu(self, pos):
        column = self.table_widget.horizontalHeader().logicalIndexAt(pos)
        menu = QMenu(self)
        combine_action = menu.addAction(self.tr("Combine Column"))
        remove_action = menu.addAction(self.tr("Remove Column"))
        combine_action.triggered.connect(lambda: self.combine_column(column))
        remove_action.triggered.connect(lambda: self.remove_column(column))
        menu.exec_(self.table_widget.mapToGlobal(pos))

    def combine_column(self, original_column):
        column_titles = self.get_column_titles()
        if len(column_titles) <= 1:
            QMessageBox.warning(self, self.tr('Warning'), self.tr('No more columns to combine.'))
            return
        
        column_titles.pop(original_column)
        column, ok = QInputDialog.getItem(self, self.tr("Combine Column"), self.tr("Choose column to combine:"), column_titles, 0, False)

        if ok and column:
            column_index = column_titles.index(column)
            if column_index >= original_column:
                column_index += 1
            self._combine_columns(original_column, column_index)

    def _combine_columns(self, col1, col2):
        xpath1 = self.table_xpath.item(0, col1).text()
        xpath2 = self.table_xpath.item(0, col2).text()
        # Combine the xpaths
        new_xpath = self.simplify_xpaths(xpath1, xpath2)
        # Determine the column to keep and the one to remove
        column_to_keep, column_to_remove = sorted([col1, col2])
        # Update the xpath in the kept column
        self.table_xpath.setItem(0, column_to_keep, QTableWidgetItem(new_xpath))
        # Remove the other column
        self.remove_column(column_to_remove)
        # Handle cell changed
        self.handle_cell_changed(0, column_to_keep)
    
    def simplify_xpaths(self, xpath1, xpath2):
        components1 = xpath1.split('//')
        components2 = xpath2.split('//')

        # Check if both paths have the same length
        if len(components1) != len(components2):
            return xpath1 + ' | ' + xpath2

        simplified_components = []

        for comp1, comp2 in zip(components1, components2):
            # Check if the components are exactly the same
            if comp1 == comp2:
                simplified_components.append(comp1)
            else:
                # If they're not, compare the base tags without attributes
                base_tag1 = comp1.split('[')[0]
                base_tag2 = comp2.split('[')[0]

                if base_tag1 == base_tag2:
                    simplified_components.append(base_tag1)
                else:
                    # If base tags are also different, return original XPaths
                    return xpath1 + ' | ' + xpath2

        simplified_xpath = '//'.join(simplified_components)
        return simplified_xpath

    def create_table_context_menu(self, pos, table):
        # Get the index of the cell at the position pos
        index = table.indexAt(pos)

        # Check if the index is valid
        if index.isValid():
            column = index.column()
            menu = QMenu(self)
            combine_action = QAction(self.tr("Combine Column"), self)
            remove_action = QAction(self.tr("Remove Column"), self)
            combine_action.triggered.connect(lambda: self.combine_column(column))
            remove_action.triggered.connect(lambda: self.remove_column(column))
            menu.addAction(combine_action)
            menu.addAction(remove_action)
            menu.exec_(table.viewport().mapToGlobal(pos))

    def load_template(self, template):
        # Open the scrape widget
        self.scrape_widget.show()

        # Browse to the URL
        self.browser.load(QUrl(template['url']))

        self.selected_template = template

        QTimer.singleShot(4000, self.set_template)

    def set_template(self):
        self.browser.page().runJavaScript(jss.START_JS)
        self.scrape_widget.setVisible(False)
        self.toggle_scrape_widget()

        if self.selected_template and self.selected_template['pagination_xpath']:
            self.toggle_pagination()
            self.pagination_xpath_input.setText(self.selected_template['pagination_xpath'])
            self.handle_pagination_changed()

        # Save all this information in the current process manager (including the pagination xpath if it exists)
        self.update_process_manager(self.selected_template)

        # Set column titles
        self.set_column_titles(get_column_data_from_template(self.selected_template, "column_title"))

        # Set the first texts in the first row of the table widget
        self.set_first_row_data(get_column_data_from_template(self.selected_template, "first_text"))

        # Set the xpaths in the xpath table
        self.set_xpaths(get_column_data_from_template(self.selected_template, "xpath"))

    @pyqtSlot()
    def infinite_scroll(self):
        def process_heights(result):
            if result:
                random_time = random.randint(100, 500)
                QTimer.singleShot(random_time, handle_scroll_height)
            else:
                # emit the signal here, once the infinite scrolling has finished
                self.signal_manager.browser_signal.emit()

        def handle_scroll_height(result=None):
            self.browser.page().runJavaScript(jss.COMPARE_HEIGHTS_JS, process_heights)

        self.browser.page().runJavaScript(jss.GET_HEIGHT_JS, handle_scroll_height)

    def set_process_manager(self, process_manager, scrape=True):
        self.process_manager = process_manager
        self.browser.page().process_manager = process_manager
        self.browser.page().runJavaScript(jss.START_JS)
        self.toggle_scrape_widget()

        if process_manager and process_manager.pagination_xpath:
            self.toggle_pagination()
            self.pagination_xpath_input.setText(process_manager.pagination_xpath)
            self.handle_pagination_changed()

        self.set_column_titles(process_manager.get_titles())

        # Set the first texts in the first row of the table widget
        self.set_first_row_data(process_manager.get_all_first_texts())

        # Set the xpaths in the xpath table
        self.set_xpaths(process_manager.get_all_xpaths())

        if scrape:
            # Start the infinite scroll
            self.infinite_scroll()
        else:
            self.wait_data = True

    def set_column_titles(self, column_titles):
        self.table_widget.setColumnCount(len(column_titles))
        self.table_xpath.setColumnCount(len(column_titles))
        for i, title in enumerate(column_titles):
            header_item = QTableWidgetItem(title)
            self.table_widget.setHorizontalHeaderItem(i, header_item)

    def set_first_row_data(self, first_row_data):
        self.table_widget.setRowCount(1)
        for i, data in enumerate(first_row_data):
            item = QTableWidgetItem(data)
            self.table_widget.setItem(0, i, item)

    def set_xpaths(self, xpaths):
        self.table_xpath.setRowCount(1)
        for i, xpath in enumerate(xpaths):
            item = QTableWidgetItem(xpath)
            self.table_xpath.setItem(0, i, item)

    def update_process_manager(self, template):
        self.process_manager.clear_columns()
        for i, (xpath, text) in enumerate(zip(get_column_data_from_template(template, "xpath"), get_column_data_from_template(template, "first_text"))):
            self.process_manager.create_column(xpath)
            self.process_manager.set_first_text(i, text)
        if 'pagination_xpath' in template and template['pagination_xpath'] is not None:
            self.process_manager.pagination_xpath = template['pagination_xpath']

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pagination_widget.isVisible():
            widget_width = self.scrape_widget.width()
            widget_width = int(widget_width * PAGINATION_WIDGET_WIDTH_PERCENTAGE)
            self.pagination_widget.setFixedWidth(widget_width)

    def paintEvent(self, _):
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)

    def show_help_dialog(self):
        QMessageBox.information(
            self,
            self.tr("Help"),
            self.tr("If you encounter any issues that prevent the successful completion of scraping during the "
                    "automatic pagination process (IP blocks, failure to find the pagination button, etc.), "
                    "but you do have access to the required website from this browser, disable this option "
                    "and try again. Note that the interface will be blocked until the process is completed.")
        )

    def create_interaction_widget(self):
        self.interaction_widget = QWidget(self)
        self.interaction_widget_layout = QHBoxLayout(self.interaction_widget)

        self.cancel_button = QPushButton(self.tr("Stop Process"), self.interaction_widget)
        self.interaction_widget_layout.addWidget(self.cancel_button)

        self.continue_button = QPushButton(self.tr("Continue Process"), self.interaction_widget)
        self.interaction_widget_layout.addWidget(self.continue_button)

        self.interaction_widget.hide()
        self.browser_tab_layout.addWidget(self.interaction_widget, 0, Qt.AlignBottom)
