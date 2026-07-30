"""Configuration module"""
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:7799").rstrip("/")
# Foundry runs can legitimately take up to 180 seconds; document analysis and
# optional fact-checking add bounded work around that model call.
REQUEST_TIMEOUT = 240.0
