import keyring
from cryptography.fernet import Fernet
import os
import json
from urllib.parse import urlparse
from exceptions.file_exceptions import FileDeletionException
from utils.manager.file_manager import get_file_path
import logging

KEY_NAME = "scraping_interface_password_manager_key"
SERVICE_NAME = "scraping_interface"
FILE_NAME = "login.txt"

logger = logging.getLogger(__name__)

def create_key():
    try:
        # Password manager key
        stored_key = keyring.get_password(SERVICE_NAME, KEY_NAME)

        if stored_key is None:
            key = Fernet.generate_key()
            keyring.set_password(SERVICE_NAME, KEY_NAME, key.decode("utf-8"))
            logger.info("Key generated and stored.")
    except Exception as e:
        logger.warning(f"Warning: Error creating the key to encript the passwords: {e}\nYou won't be able to use the Password Manager.")

def get_key():
    try:
        stored_key = keyring.get_password(SERVICE_NAME, KEY_NAME)
        if stored_key is None:
            create_key()
            stored_key = keyring.get_password(SERVICE_NAME, KEY_NAME)
        return stored_key.encode("utf-8")
    except Exception as e:
        logger.error(f"Error getting the key to encrypt the passwords: {e}")
        return None

def save_login_file(login_info):
    try:
        # Use the key to create a Fernet object
        cipher_suite = Fernet(get_key())

        # Read existing data from the file
        file_path = get_file_path(FILE_NAME)

        # Decrypt the existing data if the file exists
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                encrypted_data = f.read()
                decrypted_data = cipher_suite.decrypt(encrypted_data).decode("utf-8")
                existing_login_data = json.loads(decrypted_data)
        else:
            existing_login_data = []

        # Extract the domain name from the given URL
        domain_name = get_domain_name(login_info['url'])

        if domain_name is None:
            return False

        # Find the matching login info
        login_info_updated = False
        for i, stored_login_info in enumerate(existing_login_data):
            stored_domain_name = get_domain_name(stored_login_info['url'])

            if stored_domain_name is None:
                continue

            # If a matching domain is found, update the login_info
            if domain_name == stored_domain_name:
                existing_login_data[i] = login_info
                login_info_updated = True
                break

        # If no match is found, append the new login_info to the existing data
        if not login_info_updated:
            existing_login_data.append(login_info)

        # Convert the updated login data to a JSON string
        updated_login_data_json = json.dumps(existing_login_data)

        # Encrypt the JSON string
        encrypted_updated_login_data = cipher_suite.encrypt(updated_login_data_json.encode("utf-8"))

        # Store encrypted_updated_login_data securely in a file
        with open(file_path, "wb") as f:
            f.write(encrypted_updated_login_data)

        # Set file permissions to read and write for the owner only (chmod 600)
        os.chmod(file_path, 0o600)

        logger.info("Credentials stored successfully.")
        return True
    except Exception as e:
        logger.error(f"Error saving the credentials: {e}")
        return False

def get_login_info(url):
    try:
        # Use the key to create a Fernet object
        cipher_suite = Fernet(get_key())

        # Read encrypted data from the file
        file_path = get_file_path(FILE_NAME)

        if not os.path.exists(file_path):
            return None

        with open(file_path, "rb") as f:
            encrypted_data = f.read()

        # Decrypt the data
        decrypted_data = cipher_suite.decrypt(encrypted_data).decode("utf-8")
        login_data = json.loads(decrypted_data)

        domain_name = get_domain_name(url)
        if domain_name is None:
            return None

        # Find the matching login info
        for login_info in login_data:
            stored_domain_name = urlparse(login_info['url']).netloc.split(".")
            if len(stored_domain_name) >= 2:
                stored_domain_name = ".".join(stored_domain_name[-2:])
            else:
                continue

            if domain_name == stored_domain_name:
                return login_info

        logger.info("No login credentials were found.")
        # If no match is found, return None
        return None
    except Exception as e:
        logger.error(f"Error getting the login info: {e}")
        return None

def clear_stored_passwords():
    try:
        file_path = get_file_path(FILE_NAME)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        exception_text = "Error deleting stored passwords"
        logger.error(f"{exception_text}: {e}")
        raise FileDeletionException(exception_text)

def get_domain_name(url):
    try:
        domain_name = urlparse(url).netloc.split(".")
        
        if len(domain_name) >= 2:
            domain_name = ".".join(domain_name[-2:])
        else:
            domain_name = None

        return domain_name
    except Exception as e:
        logger.error(f"Error getting domain name: {e}")
        return None
