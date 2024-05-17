import os
from utils.manager.file_manager import get_file_path
from exceptions.file_exceptions import FileDeletionException
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ProcessStatus(Enum):
    RUNNING = 1
    STOPPING = 2
    FINISHED = 3
    ERROR = 4
    REQUIRES_INTERACTION = 5
    INTERACTING = 6
    STOPPED = 7
    UNKNOWN = 8

def clear_process_history():
    try:
        file_path = get_file_path("processes.csv")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        exception_text = "Error deleting process history"
        logger.error(f"{exception_text}: {e}")
        raise FileDeletionException(exception_text)

class Column:
    def __init__(self, xpath, visual_index):
        self.xpath = xpath
        self.visual_index = visual_index
        self.first_text = None
        self.num_elements = None
        self.title = None

    def get_xpath(self):
        return self.xpath
    
    def set_xpath(self, xpath):
        self.xpath = xpath

    def get_visual_index(self):
        return self.visual_index
    
    def set_visual_index(self, visual_index):
        self.visual_index = visual_index
    
    def get_first_text(self):
        return self.first_text
    
    def set_first_text(self, first_text):
        self.first_text = first_text
    
    def get_num_elements(self):
        return self.num_elements
    
    def set_num_elements(self, num_elements):
        self.num_elements = num_elements

class ProcessManager:
    def __init__(self):
        self.columns = []
        self.pagination_xpath = None
        self.file_name = None
        self.append = False
        self.unique_id = None
        self.stop = None
        self.interaction = None
        self.url = None
        self.max_pages = None

    def create_column(self, xpath):
        visual_index = len(self.columns) + 1
        column = Column(xpath, visual_index)
        self.columns.append(column)

    def remove_column(self, index):
        if index >= 0 and index < len(self.columns):
            self.columns.pop(index)

    def get_column(self, index):
        if index >= 0 and index < len(self.columns):
            return self.columns[index]
        else:
            return None
        
    def get_all_xpaths(self):
        return [column.xpath for column in self.columns]
    
    def get_all_first_texts(self):
        return [column.first_text for column in self.columns]
            
    def get_column_count(self):
        return len(self.columns)
    
    def set_first_text(self, index, text):
        column = self.get_column(index)
        if column:
            column.first_text = text

    def set_titles(self, titles):
        if len(titles) == len(self.columns):
            for i, title in enumerate(titles):
                self.columns[i].title = title

    def get_titles(self):
        return [column.title if column.title else column.get_visual_index() for column in self.columns]

    def clear_columns(self):
        self.columns = []

    def get_columns(self):
        return self.columns
