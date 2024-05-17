from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QPushButton, QStyle, QStyleOption, QProgressBar, QMenu, QMessageBox
from PyQt5.QtCore import Qt, QVariant, pyqtSlot
from PyQt5.QtGui import QPainter
import csv
from datetime import datetime
import os
from multiprocessing import Value
from static import background_path
from utils.manager.file_manager import get_file_path
import sys
import threading
from utils.manager.process_manager import ProcessStatus
import logging
import uuid

PROCESSES_FILE = get_file_path("processes.csv")
logger = logging.getLogger(__name__)

class ProcessesTab(QWidget):
    def __init__(self, parent=None, notification_manager=None):
        super().__init__(parent)
        self.notification_manager = notification_manager

        self.STATUS_STRINGS = {
            ProcessStatus.RUNNING: self.tr("Running"),
            ProcessStatus.STOPPING: self.tr("Stopping..."),
            ProcessStatus.FINISHED: self.tr("Finished"),
            ProcessStatus.ERROR: self.tr("Error"),
            ProcessStatus.REQUIRES_INTERACTION: self.tr("Requires interaction"),
            ProcessStatus.INTERACTING: self.tr("Interacting..."),
            ProcessStatus.STOPPED: self.tr("Stopped"),
            ProcessStatus.UNKNOWN: self.tr("Unknown")
        }

        self.processes_tab_layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([self.tr('Scraped Web'), self.tr('File Name'), self.tr('Scraped Items'), self.tr('Status'), self.tr('Date'), self.tr('Time'), self.tr('Action')])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) # Set stretch factor for 'Scraped Web' column
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False) # Disable stretching of last section
        self.processes_tab_layout.addWidget(self.table)
        self.no_data_label = QLabel(self) # Create label
        self.no_data_label.setAlignment(Qt.AlignCenter) # Center label
        self.processes_tab_layout.addWidget(self.no_data_label) # Add label to layout
        self.status_codes = [] # Stores status codes for each process
        self.load_data()

        self.uuid_row_mapping = {}
        self.row_uuid_mapping = {}
        self.stop_variables = {}
        self.interaction_variables = {}

        self.setStyleSheet(f"""
            ProcessesTab {{
                background-image: url({background_path});
                background-repeat: no-repeat;
                background-position: center;
            }}
        """)

    def create_open_file_button(self, file_name):
        open_file_button = QPushButton(self.tr('Open'))
        open_file_button.clicked.connect(lambda: self.open_file(file_name))
        return open_file_button
    
    def create_stop_button(self, unique_id):
        stop_button = QPushButton(self.tr('Stop'))
        stop_button.clicked.connect(lambda: self.stop_process(unique_id))
        return stop_button
    
    def create_interaction_button(self, unique_id):
        interaction_button = QPushButton(self.tr('Interact'))
        interaction_button.clicked.connect(lambda: self.on_interaction(unique_id))
        return interaction_button
    
    def create_resolved_button(self, unique_id):
        resolved_button = QPushButton(self.tr('Resolved'))
        resolved_button.clicked.connect(lambda: self.on_resolved(unique_id))
        return resolved_button
    
    def translate_status(self, status_code):
        status = ProcessStatus(status_code)
        return self.tr(self.STATUS_STRINGS.get(status, "Unknown"))
        
    def load_data(self):
        try:
            with open(PROCESSES_FILE, newline='') as file:
                reader = csv.reader(file)
                data = list(reader)
                self.table.setRowCount(len(data))
                for row, item in enumerate(data):
                    for col in range(len(item)):
                        if col == 3:
                            status = int(item[col]) if item[col] else ProcessStatus.ERROR.value
                            if status == ProcessStatus.FINISHED.value:
                                self.table.setCellWidget(row, 6, self.create_open_file_button(item[1]))
                            elif status in [ProcessStatus.RUNNING.value, ProcessStatus.STOPPING.value, ProcessStatus.REQUIRES_INTERACTION.value, ProcessStatus.INTERACTING.value]:
                                status = ProcessStatus.STOPPED.value
                            self.status_codes.append(status)
                            status_str = self.translate_status(status)
                            table_item = QTableWidgetItem(status_str)
                        else:
                            table_item = QTableWidgetItem(item[col])
                        table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)  # Disable editing
                        self.table.setItem(row, col, table_item)
                
                self.save_data()

                if len(data) > 0:
                    self.no_data_label.hide() # Hide label if data is found
                    self.table.show() # Show table if data is found
                else:
                    self.hide_table()
                
        except FileNotFoundError:
            self.hide_table()

    def hide_table(self):
        self.no_data_label.setText(self.tr("No processes found")) # Set label text if no data is found
        self.no_data_label.show() # Show label if no data is found
        self.table.hide() # Hide table if no data is found
        self.table.setRowCount(0)

    def add_row(self, scraped_web, file_name, column_titles):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        now = datetime.now()
        date = now.strftime("%d/%m/%Y")
        time = now.strftime("%H:%M:%S")
        
        status_code = ProcessStatus.RUNNING.value
        items = [scraped_web, file_name, ', '.join(column_titles), self.translate_status(status_code), date, time]
        self.status_codes.append(status_code)
        for col, text in enumerate(items):
            table_item = QTableWidgetItem(text)
            table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)  # Disable editing
            self.table.setItem(row_count, col, table_item)

        unique_id = str(uuid.uuid4())
        self.uuid_row_mapping[unique_id] = row_count
        self.row_uuid_mapping[row_count] = unique_id

        self.table.setCellWidget(row_count, 6, self.create_stop_button(unique_id))
        self.table.show()
        self.no_data_label.hide()

        stop = Value('b', False)
        self.stop_variables[unique_id] = stop

        interaction = threading.Event()
        self.interaction_variables[unique_id] = interaction

        return unique_id, stop, interaction

    def get_table_data(self):
        table_data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                if self.table.item(row, col):
                    if col == 3:
                        status_code = self.status_codes[row] if row < len(self.status_codes) else ''
                        row_data.append(status_code)
                    else:
                        row_data.append(self.table.item(row, col).text())
                else:
                    row_data.append('')
            table_data.append(row_data)
        return table_data
    
    def save_data(self):
        try:
            with open(PROCESSES_FILE, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(self.get_table_data())
        except Exception as e:
            logger.error(f"Error saving processes: {e}")

    def open_file(self, file_name):
        if os.name == 'nt':
            os.system(f'start {file_name}')
            logger.info(f"Opening file '{file_name}'")
        elif os.name == 'posix':
            if sys.platform.startswith('darwin'):
                os.system(f"open '{file_name}'")
            else:
                os.system(f"xdg-open '{file_name}'")
            logger.info(f"Opening file '{file_name}'")
        else:
            logger.error("Error: File is not opening due to unknown operating system")

    @pyqtSlot(QVariant, QVariant, QVariant)
    def update_status(self, unique_id, status, file_name):
        if unique_id not in self.uuid_row_mapping:
            return
        row = self.uuid_row_mapping[unique_id]
        if "%" in status:
            progress = QProgressBar()
            progress.setValue(int(status.replace("%", ""))) # Remove '%' character
            self.table.setItem(row, 3, None)
            self.table.setCellWidget(row, 3, progress)

            status_code = ProcessStatus.RUNNING.value
        else:
            # Remove QProgressBar from the cell
            self.table.setCellWidget(row, 3, None)

            status_code = int(status)
            self.table.setItem(row, 3, QTableWidgetItem(self.translate_status(status_code)))
            if status_code == ProcessStatus.FINISHED.value:
                self.table.setCellWidget(row, 6, self.create_open_file_button(file_name))
                self.notification_manager.show_notification(self.tr("Process finished"), self.tr("A process has finished successfully"))
            elif status_code == ProcessStatus.STOPPED.value or status_code == ProcessStatus.ERROR.value:
                self.table.setCellWidget(row, 6, None)
            elif status_code == ProcessStatus.REQUIRES_INTERACTION.value:
                self.table.setCellWidget(row, 6, self.create_interaction_button(unique_id))
                self.notification_manager.show_notification(self.tr("Interaction required"), self.tr("Please interact with the browser to continue the process"))
        if row < len(self.status_codes):
            self.status_codes[row] = status_code
        self.table.setItem(row, 1, QTableWidgetItem(file_name))
        self.save_data()

    def stop_process(self, unique_id):
        row = self.uuid_row_mapping[unique_id]
        self.stop_variables[unique_id].value = True
        status_code = ProcessStatus.STOPPING.value
        self.table.setCellWidget(row, 3, None)
        self.table.setItem(row, 3, QTableWidgetItem(self.translate_status(status_code)))
        self.status_codes[row] = status_code
        self.table.setCellWidget(row, 6, None)

    def on_interaction(self, unique_id):
        row = self.uuid_row_mapping[unique_id]
        self.interaction_variables[unique_id].set()
        status_code = ProcessStatus.INTERACTING.value
        self.table.setItem(row, 3, QTableWidgetItem(self.translate_status(status_code)))
        self.table.setCellWidget(row, 6, self.create_resolved_button(unique_id))
        self.status_codes[row] = status_code

    def on_resolved(self, unique_id):
        row = self.uuid_row_mapping[unique_id]
        unique_id = self.row_uuid_mapping[row]
        self.interaction_variables[unique_id].set()
        status_code = ProcessStatus.RUNNING.value
        self.table.setItem(row, 3, QTableWidgetItem(self.translate_status(status_code)))
        self.table.setCellWidget(row, 6, self.create_stop_button(unique_id))
        self.status_codes[row] = status_code

    def paintEvent(self, _):
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        del_action = context_menu.addAction(self.tr("Delete Row"))
        del_file_and_action = context_menu.addAction(self.tr("Delete Row and File"))

        action = context_menu.exec_(self.table.mapToGlobal(event.pos()))

        if action == del_action or action == del_file_and_action:
            row = self.table.currentRow()
            if row >= 0:
                if action == del_file_and_action:
                    file_name = self.table.item(row, 1).text()
                    if file_name and os.path.exists(file_name):
                        try:
                            os.remove(file_name)
                        except PermissionError:
                            QMessageBox.critical(self, "Error", self.tr("The file could not be removed. Please make sure it's closed."))
                            return  # Don't proceed to row deletion if file deletion failed
                self.delete_row(row)

    def delete_row(self, row):
        # If the process is running, stop it.
        status_code = self.status_codes[row]
        unique_id = None
        if row in self.row_uuid_mapping:
            unique_id = self.row_uuid_mapping[row]
            if status_code == ProcessStatus.RUNNING.value or status_code == ProcessStatus.REQUIRES_INTERACTION.value or status_code == ProcessStatus.INTERACTING.value:
                self.stop_process(unique_id)

        # Remove the row from the table.
        self.table.removeRow(row)
        if self.table.rowCount() == 0:
            self.hide_table()

        # Remove the status code from the list.
        self.status_codes.pop(row)
        if row in self.stop_variables:
            del self.stop_variables[row]
        if row in self.interaction_variables:
            del self.interaction_variables[row]

        # Update the row numbers in the dictionary.
        self.row_uuid_mapping = {}
        for key, value in self.uuid_row_mapping.items():
            if value > row:
                self.uuid_row_mapping[key] = value - 1
                self.row_uuid_mapping[value - 1] = key
            elif value < row:
                self.row_uuid_mapping[value] = key
                
        # Remove the row number from the dictionary.
        if unique_id:
            del self.uuid_row_mapping[unique_id]

        # Save changes to the "processes.csv" file.
        self.save_data()
