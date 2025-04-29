import os
import csv
import json
import logging
from io import StringIO
from mcp.server.fastmcp import FastMCP, Context
import httpx
from dotenv import load_dotenv
import asyncio
import mcp.types as types # Import MCP types
import sys 

# Load environment variables from .env for local execution or secrets
# Variables set in Claude config 'env' block might override these when run by the client
load_dotenv()

# --- Configuration Loading ---
# API Key (Secret - primarily from .env or system env)
DATASAUR_API_KEY = os.getenv("DATASAUR_API_KEY")

# Specific URL for the CSV processing sandbox
DATASAUR_CSV_API_URL = os.getenv("DATASAUR_CSV_API_URL")

# Specific URL for the Grok sandbox
DATASAUR_GROK_API_URL = os.getenv("DATASAUR_GROK_API_URL")
# --- End Configuration Loading ---

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

mcp = FastMCP("Datasaur API Processor")


@mcp.tool()
async def convert_csv_to_json(file_path: str) -> list:
    """
    Reads a CSV file from the specified file path and converts it to a JSON-like list of dicts.
    Provide the full path to the CSV file as a string.
    """
    logging.debug(f"Reading CSV file from path: {file_path}")
    # ... (rest of the function remains the same) ...
    try:
        # Ensure the path exists and is a file
        if not os.path.exists(file_path):
            logging.error(f"File not found at path: {file_path}")
            return [{"error": f"File not found at path: {file_path}"}]
        if not os.path.isfile(file_path):
             logging.error(f"Path is not a file: {file_path}")
             return [{"error": f"Path is not a file: {file_path}"}]

        with open(file_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
    except FileNotFoundError:
        logging.error(f"File not found error for path: {file_path}")
        return [{"error": f"File not found: {file_path}"}]
    except PermissionError:
        logging.error(f"Permission denied for path: {file_path}")
        return [{"error": f"Permission denied: {file_path}"}]
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return [{"error": f"Error reading file: {e}"}]

    reader = csv.DictReader(StringIO(csv_content))
    data = []
    for row in reader:
        processed_row = {}
        for key, value in row.items():
            # Attempt to convert numeric strings to numbers
            if value:
                if value.isdigit():
                    processed_row[key] = int(value)
                elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                     try:
                         processed_row[key] = float(value)
                     except ValueError:
                         processed_row[key] = value # Fallback to string if float conversion fails unexpectedly
                else:
                    processed_row[key] = value
            else:
                 processed_row[key] = value # Keep empty strings as they are or handle as None if preferred
        data.append(processed_row)
    logging.debug(f"CSV converted to JSON: {data}")
    return data


@mcp.tool()
async def process_and_send_csv(file_path: str) -> str:
    """
    Reads a CSV file from the specified path, converts to JSON, sends its content to the specific Datasaur CSV API sandbox, and returns the API's result.
    Provide the full path to the CSV file as a string.
    """
    logging.debug(f"Processing CSV file from path: {file_path}")
    json_data = await convert_csv_to_json(file_path)

    if isinstance(json_data, list) and len(json_data) > 0 and "error" in json_data[0]:
       logging.error(f"CSV conversion failed for {file_path}: {json_data[0]['error']}")
       return f"Error processing CSV: {json_data[0]['error']}"

    json_content_string = json.dumps(json_data, ensure_ascii=False)

    # --- Use specific CSV URL and check credentials ---
    if not DATASAUR_CSV_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_CSV_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur CSV API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = { "messages": [ {"role": "user", "content": json_content_string} ] }

    logging.debug(f"Sending processed CSV data to Datasaur API: {DATASAUR_CSV_API_URL}")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # --- Use specific CSV URL ---
            response = await client.post(DATASAUR_CSV_API_URL, headers=headers, json=payload)
            # --- End Use ---
            response.raise_for_status()
            response_json = response.json()
            logging.debug(f"Received response from Datasaur CSV API: {response_json}")
    except httpx.RequestError as e:
        logging.error(f"Datasaur CSV API request failed for {file_path}: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur CSV API request failed for {file_path} with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur CSV API for {file_path}: {e}")
        return f"Error: An unexpected error occurred during API request. Check server logs."

    # --- (Response processing remains the same) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            try:
                if isinstance(content, (dict, list)):
                     return json.dumps(content, indent=2, ensure_ascii=False)
                content_json = json.loads(content)
                return json.dumps(content_json, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                 return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur CSV API response choice for {file_path}: {response_json}")
             return "Error: Received unexpected response format from CSV API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur CSV API response for {file_path}: {response_json}")
        return "Error: Received unexpected response format from CSV API (missing choices)."


@mcp.tool()
async def call_grok_via_datasaur(prompt: str) -> str:
    """
    Sends a given prompt string to the 'grok uncensored' model via the specific Datasaur Grok API sandbox and returns the model's response.
    Use this for general queries or instructions intended for an uncensored LLM.

    Args:
        prompt: The text prompt to send to the Grok model.
    """
    logging.debug(f"Received Grok prompt: {prompt[:100]}...")

    # --- Use specific Grok URL and check credentials ---
    if not DATASAUR_GROK_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_GROK_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur Grok API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur Grok API: {DATASAUR_GROK_API_URL}")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
             # --- Use specific Grok URL ---
             response = await client.post(DATASAUR_GROK_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur Grok API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur Grok API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur Grok API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur Grok API: {e}")
        return f"Error: An unexpected error occurred during Grok API request. Check server logs."

    # --- (Response processing remains the same) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur Grok API response choice: {response_json}")
             return "Error: Received unexpected response format from Grok API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur Grok API response: {response_json}")
        return "Error: Received unexpected response format from Grok API (missing choices)."

if __name__ == "__main__":
    # Optional: Add startup checks for API keys/URLs if needed for standalone running
    # if not DATASAUR_API_KEY:
    #    logging.critical("DATASAUR_API_KEY is not set. Exiting.")
    #    sys.exit(1) # Use sys.exit here
    # Add similar checks for URLs if they are absolutely critical at startup

    transport_type = os.getenv("TRANSPORT", "stdio")

    if transport_type == 'stdio':
        logging.info("Starting MCP server in STDIO mode...")
        try:
            # Call mcp.run() directly. It manages the event loop.
            mcp.run(transport='stdio')
            logging.info("MCP server finished in STDIO mode.")
        except Exception as e:
            logging.exception("MCP server encountered an unhandled exception during run.") # Log the full exception
        finally:
            # This block will execute even if mcp.run() exits unexpectedly
            logging.critical("MCP server process __main__ block is ending.")
            # Using sys.stderr requires sys to be imported
            print("MCP server process __main__ block is ending.", file=sys.stderr)
    else:
        # ... (handle other transports or errors) ...
        logging.error(f"Unsupported transport type: {transport_type}")
        sys.exit(1) # Exit if transport is unsupported