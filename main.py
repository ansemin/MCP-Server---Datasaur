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
DATASAUR_GROK_UNCENSORED_API_URL = os.getenv("DATASAUR_GROK_UNCENSORED_API_URL")

# --- Add URL for GPT 4.1 Sandbox ---
DATASAUR_GPT41_API_URL = os.getenv("DATASAUR_GPT41_API_URL") # Added default based on your example

# --- Add URL for GPT o3 Sandbox ---
DATASAUR_GPT_O3_API_URL = os.getenv("DATASAUR_GPT_O3_API_URL")

# --- Add URL for Grok 3 Sandbox ---
DATASAUR_GROK_3_API_URL = os.getenv("DATASAUR_GROK_3_API_URL")

# --- Add URL for Gemini Exp Sandbox ---
DATASAUR_GEMINI_EXP_API_URL = os.getenv("DATASAUR_GEMINI_EXP_API_URL")

# --- Add URL for DeepSeek R1 Sandbox ---
DATASAUR_DEEPSEEK_R1_API_URL = os.getenv("DATASAUR_DEEPSEEK_R1_API_URL")

# --- Add URL for MCP Helper Sandbox ---
DATASAUR_MCP_HELPER_API_URL = os.getenv("DATASAUR_MCP_HELPER_API_URL")

# --- Add URL for Email Helper Sandbox ---
DATASAUR_EMAIL_HELPER_API_URL = os.getenv("DATASAUR_EMAIL_HELPER_API_URL")

# --- Add URL for Weekly Report Helper Sandbox ---
DATASAUR_WEEKLY_REPORT_HELPER_API_URL = os.getenv("DATASAUR_WEEKLY_REPORT_HELPER_API_URL")
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
async def call_grok_uncensored(prompt: str) -> str:
    """
    Sends a given prompt string to the 'grok uncensored' model via the specific Datasaur Grok API sandbox and returns the model's response.
    Use this for general queries or instructions intended for an uncensored LLM.

    Args:
        prompt: The text prompt to send to the Grok model.
    """
    logging.debug(f"Received Grok prompt: {prompt[:100]}...")

    # --- Use specific Grok URL and check credentials ---
    if not DATASAUR_GROK_UNCENSORED_API_URL or not DATASAUR_API_KEY:
        # Note: The error message still mentions DATASAUR_GROK_API_URL, kept for consistency with original code structure
        logging.error("DATASAUR_GROK_UNCENSORED_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur Grok API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur Grok API: {DATASAUR_GROK_UNCENSORED_API_URL}")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
             # --- Use specific Grok URL ---
             response = await client.post(DATASAUR_GROK_UNCENSORED_API_URL, headers=headers, json=payload)
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

# --- NEW TOOL ADDED BELOW ---
@mcp.tool()
async def call_GPT_4_1(prompt: str) -> str:
    """
    Sends a given prompt string to the 'GPT 4.1' AI coding assistant model via the specific Datasaur API sandbox and returns the model's response.
    Use this for complex programming challenges or coding assistance tasks.

    Args:
        prompt: The text prompt to send to the GPT-4.1 model.
    """
    logging.debug(f"Received GPT-4.1 prompt: {prompt[:100]}...")

    # --- Use specific GPT-4.1 URL and check credentials ---
    if not DATASAUR_GPT41_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_GPT41_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur GPT-4.1 API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    # Note: We are only sending the user's prompt. The detailed system prompt you provided
    # is assumed to be configured on the Datasaur sandbox side for the deployment.
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur GPT-4.1 API: {DATASAUR_GPT41_API_URL}")

    try:
        # Increased timeout for potentially longer coding responses
        async with httpx.AsyncClient(timeout=180.0) as client:
             # --- Use specific GPT-4.1 URL ---
             response = await client.post(DATASAUR_GPT41_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur GPT-4.1 API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur GPT-4.1 API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur GPT-4.1 API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur GPT-4.1 API: {e}")
        return f"Error: An unexpected error occurred during GPT-4.1 API request. Check server logs."

    # --- (Response processing identical to Grok tool) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            # GPT responses are likely text (code, explanation), so just return as string.
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur GPT-4.1 API response choice: {response_json}")
             return "Error: Received unexpected response format from GPT-4.1 API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur GPT-4.1 API response: {response_json}")
        return "Error: Received unexpected response format from GPT-4.1 API (missing choices)."

# --- NEW TOOL ADDED BELOW FOR GPT o3 ---
@mcp.tool()
async def call_GPT_o3(prompt: str) -> str:
    """
    Sends a given prompt string to the 'GPT o3' AI coding assistant model via the specific Datasaur API sandbox and returns the model's response.
    Use this for complex programming challenges or coding assistance tasks.

    Args:
        prompt: The text prompt to send to the GPT o3 model.
    """
    logging.debug(f"Received GPT o3 prompt: {prompt[:100]}...")

    # --- Use specific GPT o3 URL and check credentials ---
    if not DATASAUR_GPT_O3_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_GPT_O3_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur GPT o3 API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    # Note: We are only sending the user's prompt. The detailed system prompt you provided
    # is assumed to be configured on the Datasaur sandbox side for the deployment.
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur GPT o3 API: {DATASAUR_GPT_O3_API_URL}")

    try:
        # Increased timeout for potentially longer coding responses
        async with httpx.AsyncClient(timeout=180.0) as client:
             # --- Use specific GPT o3 URL ---
             response = await client.post(DATASAUR_GPT_O3_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur GPT o3 API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur GPT o3 API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur GPT o3 API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur GPT o3 API: {e}")
        return f"Error: An unexpected error occurred during GPT o3 API request. Check server logs."

    # --- (Response processing identical to Grok tool) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            # GPT responses are likely text (code, explanation), so just return as string.
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur GPT o3 API response choice: {response_json}")
             return "Error: Received unexpected response format from GPT o3 API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur GPT o3 API response: {response_json}")
        return "Error: Received unexpected response format from GPT o3 API (missing choices)."

# --- NEW TOOL ADDED BELOW FOR Grok 3 ---
@mcp.tool()
async def call_grok_3(prompt: str) -> str:
    """
    Sends a given prompt string to the 'Grok 3' AI coding assistant model via the specific Datasaur API sandbox and returns the model's response.
    Use this for complex programming challenges or coding assistance tasks.

    Args:
        prompt: The text prompt to send to the Grok 3 model.
    """
    logging.debug(f"Received Grok 3 prompt: {prompt[:100]}...")

    # --- Use specific Grok 3 URL and check credentials ---
    if not DATASAUR_GROK_3_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_GROK_3_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur Grok 3 API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    # Note: We are only sending the user's prompt. The detailed system prompt you provided
    # is assumed to be configured on the Datasaur sandbox side for the deployment.
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur Grok 3 API: {DATASAUR_GROK_3_API_URL}")

    try:
        # Increased timeout for potentially longer coding responses
        async with httpx.AsyncClient(timeout=180.0) as client:
             # --- Use specific Grok 3 URL ---
             response = await client.post(DATASAUR_GROK_3_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur Grok 3 API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur Grok 3 API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur Grok 3 API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur Grok 3 API: {e}")
        return f"Error: An unexpected error occurred during Grok 3 API request. Check server logs."

    # --- (Response processing identical to other coding assistants) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            # Assuming Grok 3 response is text (code, explanation), return as string.
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur Grok 3 API response choice: {response_json}")
             return "Error: Received unexpected response format from Grok 3 API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur Grok 3 API response: {response_json}")
        return "Error: Received unexpected response format from Grok 3 API (missing choices)."

# --- NEW TOOL ADDED BELOW FOR Gemini Exp ---
@mcp.tool()
async def call_gemini_exp(prompt: str) -> str:
    """
    Sends a given prompt string to the 'Gemini 2.5 Pro Experimental' AI coding assistant model via the specific Datasaur API sandbox and returns the model's response.
    Use this for complex programming challenges or coding assistance tasks.

    Args:
        prompt: The text prompt to send to the Gemini 2.5 Pro Exp model.
    """
    logging.debug(f"Received Gemini Exp prompt: {prompt[:100]}...")

    # --- Use specific Gemini Exp URL and check credentials ---
    if not DATASAUR_GEMINI_EXP_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_GEMINI_EXP_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur Gemini Exp API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    # Note: We are only sending the user's prompt. The detailed system prompt you provided
    # is assumed to be configured on the Datasaur sandbox side for the deployment.
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur Gemini Exp API: {DATASAUR_GEMINI_EXP_API_URL}")

    try:
        # Increased timeout for potentially longer coding responses
        async with httpx.AsyncClient(timeout=180.0) as client:
             # --- Use specific Gemini Exp URL ---
             response = await client.post(DATASAUR_GEMINI_EXP_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur Gemini Exp API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur Gemini Exp API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur Gemini Exp API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur Gemini Exp API: {e}")
        return f"Error: An unexpected error occurred during Gemini Exp API request. Check server logs."

    # --- (Response processing identical to other coding assistants) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            # Assuming Gemini Exp response is text (code, explanation), return as string.
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur Gemini Exp API response choice: {response_json}")
             return "Error: Received unexpected response format from Gemini Exp API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur Gemini Exp API response: {response_json}")
        return "Error: Received unexpected response format from Gemini Exp API (missing choices)."

# --- NEW TOOL ADDED BELOW FOR DeepSeek R1 ---
@mcp.tool()
async def call_deepseek_r1(prompt: str) -> str:
    """
    Sends a given prompt string to the 'DeepSeek Coder R1' AI coding assistant model via the specific Datasaur API sandbox and returns the model's response.
    Use this for complex programming challenges or coding assistance tasks.

    Args:
        prompt: The text prompt to send to the DeepSeek R1 model.
    """
    logging.debug(f"Received DeepSeek R1 prompt: {prompt[:100]}...")

    # --- Use specific DeepSeek R1 URL and check credentials ---
    if not DATASAUR_DEEPSEEK_R1_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_DEEPSEEK_R1_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur DeepSeek R1 API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    # Note: We are only sending the user's prompt. The detailed system prompt you provided
    # is assumed to be configured on the Datasaur sandbox side for the deployment.
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur DeepSeek R1 API: {DATASAUR_DEEPSEEK_R1_API_URL}")

    try:
        # Increased timeout for potentially longer coding responses
        async with httpx.AsyncClient(timeout=180.0) as client:
             # --- Use specific DeepSeek R1 URL ---
             response = await client.post(DATASAUR_DEEPSEEK_R1_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur DeepSeek R1 API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur DeepSeek R1 API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur DeepSeek R1 API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur DeepSeek R1 API: {e}")
        return f"Error: An unexpected error occurred during DeepSeek R1 API request. Check server logs."

    # --- (Response processing identical to other coding assistants) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            # Assuming DeepSeek R1 response is text (code, explanation), return as string.
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur DeepSeek R1 API response choice: {response_json}")
             return "Error: Received unexpected response format from DeepSeek R1 API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur DeepSeek R1 API response: {response_json}")
        return "Error: Received unexpected response format from DeepSeek R1 API (missing choices)."

# --- NEW TOOL ADDED BELOW FOR MCP Helper ---
@mcp.tool()
async def call_mcp_helper(prompt: str) -> str:
    """
    Sends a given prompt string to the 'MCP Helper' AI assistant via the specific Datasaur API sandbox and returns the model's response.
    Use this tool for expert assistance with generating code, debugging, or answering questions related to the Model Context Protocol (MCP).

    Args:
        prompt: The text prompt detailing the MCP-related question, coding task, or debugging issue.
    """
    logging.debug(f"Received MCP Helper prompt: {prompt[:100]}...")

    # --- Use specific MCP Helper URL and check credentials ---
    if not DATASAUR_MCP_HELPER_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_MCP_HELPER_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur MCP Helper API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur MCP Helper API: {DATASAUR_MCP_HELPER_API_URL}")

    try:
        # Using a standard timeout, adjust if MCP helper tasks are expected to be longer
        async with httpx.AsyncClient(timeout=180.0) as client:
             # --- Use specific MCP Helper URL ---
             response = await client.post(DATASAUR_MCP_HELPER_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur MCP Helper API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur MCP Helper API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur MCP Helper API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur MCP Helper API: {e}")
        return f"Error: An unexpected error occurred during MCP Helper API request. Check server logs."

    # --- (Response processing identical to other assistants) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            # Assuming MCP Helper response is text, return as string.
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur MCP Helper API response choice: {response_json}")
             return "Error: Received unexpected response format from MCP Helper API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur MCP Helper API response: {response_json}")
        return "Error: Received unexpected response format from MCP Helper API (missing choices)."

# --- NEW TOOL ADDED BELOW FOR Email Helper ---
@mcp.tool()
async def call_email_helper(prompt: str) -> str:
    """
    Sends a given prompt, likely containing the content of an incoming email, to the 'Email Helper' AI assistant via the specific Datasaur API sandbox.
    The assistant is designed to generate a professional email reply adhering to a specific format (greeting, acknowledgement, response, action, closing).
    Use this tool to draft email responses.

    Args:
        prompt: The text prompt, typically the content of the email needing a reply, to send to the Email Helper model.
    """
    logging.debug(f"Received Email Helper prompt: {prompt[:100]}...")

    # --- Use specific Email Helper URL and check credentials ---
    if not DATASAUR_EMAIL_HELPER_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_EMAIL_HELPER_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur Email Helper API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur Email Helper API: {DATASAUR_EMAIL_HELPER_API_URL}")

    try:
        # Using a standard timeout
        async with httpx.AsyncClient(timeout=180.0) as client:
             # --- Use specific Email Helper URL ---
             response = await client.post(DATASAUR_EMAIL_HELPER_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur Email Helper API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur Email Helper API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur Email Helper API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur Email Helper API: {e}")
        return f"Error: An unexpected error occurred during Email Helper API request. Check server logs."

    # --- (Response processing identical to other assistants) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            # Assuming Email Helper response is the formatted email text, return as string.
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur Email Helper API response choice: {response_json}")
             return "Error: Received unexpected response format from Email Helper API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur Email Helper API response: {response_json}")
        return "Error: Received unexpected response format from Email Helper API (missing choices)."

# --- NEW TOOL ADDED BELOW FOR Weekly Report Helper ---
@mcp.tool()
async def call_weekly_report_helper(prompt: str) -> str:
    """
    Sends a given prompt, containing daily updates or relevant information, to the 'Weekly Report Helper' AI assistant via the specific Datasaur API sandbox.
    The assistant generates a structured weekly report including sections like Executive Summary, Tasks Completed, Challenges, Meetings, Knowledge Development, Technical Issues, and Next Week's Priorities.
    Use this tool to consolidate updates into a formatted weekly report.

    Args:
        prompt: The text prompt containing the daily updates or information needed to generate the weekly report.
    """
    logging.debug(f"Received Weekly Report Helper prompt: {prompt[:100]}...")

    # --- Use specific Weekly Report Helper URL and check credentials ---
    if not DATASAUR_WEEKLY_REPORT_HELPER_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_WEEKLY_REPORT_HELPER_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur Weekly Report Helper API configuration missing on server."
    # --- End Check ---

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    logging.debug(f"Sending prompt to Datasaur Weekly Report Helper API: {DATASAUR_WEEKLY_REPORT_HELPER_API_URL}")

    try:
        # Using a standard timeout, adjust if report generation is expected to be lengthy
        async with httpx.AsyncClient(timeout=180.0) as client:
             # --- Use specific Weekly Report Helper URL ---
             response = await client.post(DATASAUR_WEEKLY_REPORT_HELPER_API_URL, headers=headers, json=payload)
             # --- End Use ---
             response.raise_for_status()
             response_json = response.json()
             logging.debug(f"Received response from Datasaur Weekly Report Helper API: {response_json}")

    except httpx.RequestError as e:
        logging.error(f"Datasaur Weekly Report Helper API request failed: {e}")
        return f"Error: API request failed: {e}"
    except httpx.HTTPStatusError as e:
        logging.error(f"Datasaur Weekly Report Helper API request failed with status {e.response.status_code}: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}. Check server logs."
    except Exception as e:
        logging.error(f"An unexpected error occurred sending to Datasaur Weekly Report Helper API: {e}")
        return f"Error: An unexpected error occurred during Weekly Report Helper API request. Check server logs."

    # --- (Response processing identical to other assistants) ---
    if 'choices' in response_json and len(response_json['choices']) > 0:
        if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
            content = response_json['choices'][0]['message']['content']
            # Assuming Weekly Report Helper response is the formatted report text, return as string.
            return str(content)
        else:
             logging.warning(f"'message' or 'content' key missing in Datasaur Weekly Report Helper API response choice: {response_json}")
             return "Error: Received unexpected response format from Weekly Report Helper API (missing message content)."
    else:
        logging.warning(f"'choices' key missing or empty in Datasaur Weekly Report Helper API response: {response_json}")
        return "Error: Received unexpected response format from Weekly Report Helper API (missing choices)."


if __name__ == "__main__":
    # Optional: Add startup checks for API keys/URLs if needed for standalone running
    # if not DATASAUR_API_KEY:
    #     logging.critical("DATASAUR_API_KEY is not set. Exiting.")
    #     sys.exit(1) # Use sys.exit here
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