"""Configuration module"""
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:7799").rstrip("/")
REQUEST_TIMEOUT = 60.0
