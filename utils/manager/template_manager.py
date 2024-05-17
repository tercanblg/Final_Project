import os
import json
from utils.manager.file_manager import get_folder_path
from exceptions.file_exceptions import FileDeletionException
import uuid
from urllib.parse import urlparse
import logging

TEMPLATE_FOLDER = get_folder_path("templates")
logger = logging.getLogger(__name__)

def save_template(url, process_manager, column_titles):
    try:
        create_folder()
        columns = []
        for i, column in enumerate(process_manager.columns):
            columns.append({
                "xpath": column.xpath,
                "visual_index": column.visual_index,
                "first_text": column.first_text,
                "num_elements": column.num_elements,
                "column_title": column_titles[i]
            })

        # Generate a unique id for the template and use it as the filename
        template_id = str(uuid.uuid4())

        template = {
            "url": url,
            "pagination_xpath": process_manager.pagination_xpath,
            "id": template_id,
            "columns": columns
        }

        template_path = _get_template_path(template_id)

        with open(template_path, "w") as f:
            json.dump(template, f)
            
        return template_id
    except Exception as e:
        logger.error(f"Error saving template: {e}")
        return None

def create_folder():
    if not os.path.exists(TEMPLATE_FOLDER):
        os.makedirs(TEMPLATE_FOLDER)

def _get_template_path(template_id):
    return os.path.join(TEMPLATE_FOLDER, f"{template_id}.json")

def list_templates():
    files = os.listdir(TEMPLATE_FOLDER)
    ids = [file[:-5] for file in files if file.endswith(".json")]
    return ids

def load_template(template_id):
    # Check if the provided id exists in the list of templates
    template_ids = list_templates()
    if template_id not in template_ids:
        return None

    # Load the template using the id
    with open(_get_template_path(template_id), "r") as f:
        template = json.load(f)

    return template

def get_column_data_from_template(template, key):
    result = []
    try:
        for column in template["columns"]:
            result.append(column[key])
        return result
    except Exception as e:
        logger.error(f"Error getting data from template: {e}")
        return None

def get_domain(url):
    result = urlparse(url)
    domain = result.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain
    
def clear_stored_templates():
    try:
        if os.path.exists(TEMPLATE_FOLDER):
            for file in os.listdir(TEMPLATE_FOLDER):
                file_path = os.path.join(TEMPLATE_FOLDER, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            return True
        return False
    except Exception as e:
        exception_text = "Error deleting stored templates"
        logger.error(f"{exception_text}: {e}")
        raise FileDeletionException(exception_text)

def delete_template(template_id):
    try:
        template_path = _get_template_path(template_id)
        if os.path.exists(template_path):
            os.remove(template_path)
            return True
        return False
    except Exception as e:
        exception_text = f"Error deleting template: {template_id}"
        logger.error(f"{exception_text}: {e}")
        raise FileDeletionException(exception_text)
