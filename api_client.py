import requests
import hashlib
import json
import os
import time
from typing import Optional, Dict, List, Any

class LibreViewAPI:
    DEFAULT_API_VERSION = "4.16.0"
    
    def __init__(self, region: Optional[str] = None):
        self.region = region
        self.base_url = self._build_api_url(region)
        self.token = None
        self.account_id_hash = None
        self.patient_id = None
        self.min_version = self.DEFAULT_API_VERSION
        
    def _build_api_url(self, region: Optional[str]) -> str:
        if region:
            return f"https://api-{region}.libreview.io"
        return "https://api.libreview.io"

    def get_headers(self) -> Dict[str, str]:
        return {
            "accept-encoding": "gzip",
            "cache-control": "no-cache",
            "connection": "Keep-Alive",
            "content-type": "application/json",
            "product": "llu.android",
            "version": self.min_version,
        }

    def _sha256(self, message: str) -> str:
        return hashlib.sha256(message.encode()).hexdigest()

    def login(self, email: str, password: str) -> bool:
        url = f"{self.base_url}/llu/auth/login"
        payload = {"email": email, "password": password}
        
        try:
            response = requests.post(url, json=payload, headers=self.get_headers())
            
            if response.status_code == 403:
                data = response.json()
                if "data" in data and "minimumVersion" in data["data"]:
                    self.min_version = data["data"]["minimumVersion"]
                    print(f"Updating API version to {self.min_version}")
                    return self.login(email, password)
            
            response.raise_for_status()
            data = response.json()
            
            login_data = data.get("data", {})
            if data.get("status") == 0 and login_data.get("redirect") and login_data.get("region"):
                self.region = login_data["region"]
                self.base_url = self._build_api_url(self.region)
                print(f"Redirecting to region {self.region} at {self.base_url}")
                return self.login(email, password)
            
            self.token = login_data.get("authTicket", {}).get("token")
            account_id = login_data.get("user", {}).get("id")
            
            if not self.token or not account_id:
                return False
                
            self.account_id_hash = self._sha256(account_id)
            return self._fetch_connections()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                 data = e.response.json()
                 if "data" in data and "minimumVersion" in data["data"]:
                    self.min_version = data["data"]["minimumVersion"]
                    print(f"Updating API version to {self.min_version} after error")
                    return self.login(email, password)
            print(f"Login failed: {e}")
            return False
        except Exception as e:
            print(f"An error occurred during login: {e}")
            return False

    def _fetch_connections(self) -> bool:
        if not self.token or not self.account_id_hash:
            return False
            
        url = f"{self.base_url}/llu/connections"
        headers = self.get_headers()
        headers["authorization"] = f"Bearer {self.token}"
        headers["account-id"] = self.account_id_hash
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            connections = data.get("data", [])
            if not connections:
                return False
                
            # Usually the first connection is the primary one
            self.patient_id = connections[0].get("patientId")
            return self.patient_id is not None
            
        except Exception as e:
            print(f"Fetching connections failed: {e}")
            return False

    def fetch_glucose_data(self) -> Optional[Dict[str, Any]]:
        if not self.patient_id or not self.token or not self.account_id_hash:
            return None
            
        url = f"{self.base_url}/llu/connections/{self.patient_id}/graph"
        headers = self.get_headers()
        headers["authorization"] = f"Bearer {self.token}"
        headers["account-id"] = self.account_id_hash
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 403:
                data = response.json()
                if "data" in data and "minimumVersion" in data["data"]:
                    self.min_version = data["data"]["minimumVersion"]
                    return self.fetch_glucose_data()
            
            response.raise_for_status()
            data = response.json()
            
            connection_data = data.get("data", {}).get("connection", {})
            glucose_measurement = connection_data.get("glucoseMeasurement", {})
            graph_data = data.get("data", {}).get("graphData", [])
            
            return {
                "current": {
                    "value": glucose_measurement.get("Value"),
                    "trend": glucose_measurement.get("TrendArrow"),
                    "timestamp": glucose_measurement.get("Timestamp"),
                    "color": glucose_measurement.get("MeasurementColor")
                },
                "graph": graph_data
            }
            
        except Exception as e:
            print(f"Fetching glucose data failed: {e}")
            return None
