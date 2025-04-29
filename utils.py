# Utility functions for mcp-datasaur

import os
import logging
from dotenv import load_dotenv

load_dotenv()

def get_datasaur_api_config():
    """
    Returns the Datasaur API URL and API key from environment variables.
    """
    api_url = os.getenv("DATASAUR_API_URL")
    api_key = os.getenv("DATASAUR_API_KEY")
    if not api_url or not api_key:
        logging.error("DATASAUR_API_URL or DATASAUR_API_KEY not set in .env")
        return None, None
    return api_url, api_key