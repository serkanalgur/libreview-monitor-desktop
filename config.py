import json
import os
import base64
from cryptography.fernet import Fernet
import uuid

class Config:
    APP_NAME = "LibreViewMonitor"
    CONFIG_FILE = os.path.expanduser("~/.libreview_monitor.json")
    # A local key to provide some level of encryption for the stored password
    _KEY_FILE = os.path.expanduser("~/.libreview_monitor.key")
    
    def __init__(self):
        self.email = ""
        self.region = None
        self.min_version = "4.16.0"
        self.low_threshold = 70
        self.high_threshold = 180
        self.encrypted_password = ""
        self.load()
        self._key = self._get_or_create_key()

    def _get_or_create_key(self):
        if os.path.exists(self._KEY_FILE):
            with open(self._KEY_FILE, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self._KEY_FILE, "wb") as f:
                f.write(key)
            return key

    def load(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.email = data.get("email", "")
                    self.region = data.get("region")
                    self.min_version = data.get("min_version", "4.16.0")
                    self.low_threshold = data.get("low_threshold", 70)
                    self.high_threshold = data.get("high_threshold", 180)
                    self.encrypted_password = data.get("password_enc", "")
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        data = {
            "email": self.email,
            "region": self.region,
            "min_version": self.min_version,
            "low_threshold": self.low_threshold,
            "high_threshold": self.high_threshold,
            "password_enc": self.encrypted_password
        }
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_password(self):
        if not self.encrypted_password:
            return None
        try:
            f = Fernet(self._key)
            return f.decrypt(self.encrypted_password.encode()).decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return None

    def set_password(self, password):
        if not password:
            return
        try:
            f = Fernet(self._key)
            self.encrypted_password = f.encrypt(password.encode()).decode()
            self.save()
        except Exception as e:
            print(f"Encryption error: {e}")

    def clear(self):
        if os.path.exists(self.CONFIG_FILE):
            os.remove(self.CONFIG_FILE)
        if os.path.exists(self._KEY_FILE):
            os.remove(self._KEY_FILE)
        self.__init__()
