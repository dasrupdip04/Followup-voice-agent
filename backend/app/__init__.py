"""Followup voice agent backend package.

Loads environment variables from the project root .env file.
"""
import os
import logging
from dotenv import load_dotenv

# Load .env located at the repository root (one level up from this package)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(dotenv_path=os.path.join(project_root, ".env"))

logger = logging.getLogger(__name__)

