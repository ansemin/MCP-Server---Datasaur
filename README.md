# MCP Server with Datasaur Sandbox

A comprehensive guide for beginners to set up and use a Model Context Protocol (MCP) server with Datasaur Sandbox.

## Table of Contents
- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Your MCP Server](#running-your-mcp-server)
- [Using Your MCP Server](#using-your-mcp-server)
- [Troubleshooting](#troubleshooting)
- [Extending Functionality](#extending-functionality)

## Introduction

### What is MCP?

Model Context Protocol (MCP) is a standardized way for applications to communicate with AI models. It defines a protocol that allows tools to exchange structured data with large language models (LLMs), enabling them to use external functions and tools.

### What is a Datasaur Sandbox?

Datasaur Sandbox provides managed API access to various AI models. This project implements an MCP server that acts as a bridge between your applications and Datasaur's API endpoints, allowing your applications to:

- Process and analyze data
- Access AI models deployed through Datasaur
- Build specialized assistants for various tasks

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.8+** installed on your system
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **A Datasaur account with API access**
   - Sign up at [datasaur.ai](https://www.datasaur.ai)
   - Obtain your API key from your account dashboard

3. **Basic knowledge of command-line operations**

## Installation

### Step 1: Clone or Create the Project

Create a new directory for your project:

```bash
mkdir datasaur-mcp-server
cd datasaur-mcp-server
```

### Step 2: Set Up Your Environment

Create a virtual environment (recommended):

```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

Create a `requirements.txt` file with the following content:

```
mcp[cli]
httpx
python-dotenv
uv
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

OR using UV (for faster installation):

```bash
pip install uv
uv pip install -r requirements.txt
```

### Step 4: Create Essential Files

#### 1. Create `.env` file

Create a `.env` file in your project root to store your API keys and configurations:

```
DATASAUR_API_KEY=your_api_key_here
DATASAUR_SANDBOX_API_URL=your_sandbox_url
```

You can add more environment variables for additional sandbox models as needed.

#### 2. Create `utils.py`

Create a utility file `utils.py` with helper functions:

```python
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
```

#### 3. Create `main.py`

Create the main MCP server file (`main.py`). This file will contain all the code needed to run your MCP server. You can copy the code from the sample provided or create a simplified version.

The full example is too long to include here, but should contain:
- Environment loading
- MCP server setup
- Tool definitions for various Datasaur API endpoints
- Main execution code

## Configuration

### Understanding the Configuration Files

#### `.env` File

The `.env` file contains sensitive information like API keys and service URLs. Never commit this file to public repositories.

#### Claude Desktop Configuration (for Claude users)

If you're using Claude Desktop, create a `claude_desktop_config.json` file:

```json
{
  "mcpServers": {
    "mcp-datasaur": {
      "command": "path\\to\\your\\python.exe",
      "args": ["path\\to\\your\\main.py"],
      "env": {
        "TRANSPORT": "stdio",
        "DATASAUR_API_KEY": "your-api-key-here",
        "DATASAUR_SANDBOX_API_URL": "https://deployment.datasaur.ai/api/deployment/your-deployment-id/your-model-id/chat/completions"
      }
    }
  }
}
```

Replace:
- `path\\to\\your\\python.exe` with your Python executable path
- `path\\to\\your\\main.py` with your main.py file path
- `your-api-key-here` with your actual Datasaur API key
- `your-deployment-id` and `your-model-id` with your actual deployment and model IDs from Datasaur

### Getting Datasaur API URLs

1. Log in to your Datasaur account
2. Navigate to the Deployments section
3. Create or select your deployment
4. Note your deployment ID and model ID
5. The API URL format is typically: `https://deployment.datasaur.ai/api/deployment/{deployment_id}/{model_id}/chat/completions`

## Running Your MCP Server

### Running Directly

To run your MCP server directly:

```bash
# Activate your virtual environment first if using one
python main.py
```

### Running with Claude Desktop

If you're using Claude Desktop:

1. Place your `claude_desktop_config.json` file in the Claude Desktop configuration directory
2. Open Claude Desktop
3. Your MCP server will be available to Claude as a tool

## Using Your MCP Server

Your MCP server provides a bridge between your applications and Datasaur's AI models. Here are the types of tools you can implement:

1. **Data Processing Tools**
   - Convert files between formats (e.g., CSV to JSON)
   - Process and analyze structured data
   - Send data to specialized AI models for analysis

2. **AI Model Access**
   - Create functions that send prompts to any AI model you deploy in Datasaur
   - Each function can follow the same pattern, changing only the endpoint URL and any model-specific parameters
   - Examples: language models, code assistants, specialized domain experts

3. **Helper Tools**
   - Create purpose-specific tools for common tasks
   - Examples: email drafting, report generation, domain-specific assistants

### Example Tool Function Pattern

Here's the general pattern for creating a tool that accesses a Datasaur sandbox model:

```python
@mcp.tool()
async def call_your_model(prompt: str) -> str:
    """
    Sends a given prompt string to your deployed model via Datasaur API sandbox.
    
    Args:
        prompt: The text prompt to send to the model.
    """
    logging.debug(f"Received prompt: {prompt[:100]}...")

    # Check configuration
    if not DATASAUR_SANDBOX_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_SANDBOX_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Datasaur API configuration missing on server."

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(DATASAUR_SANDBOX_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            response_json = response.json()
            
            # Process response
            if 'choices' in response_json and len(response_json['choices']) > 0:
                if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
                    return str(response_json['choices'][0]['message']['content'])
            
            return "Error: Unexpected response format"
    except Exception as e:
        logging.error(f"Error: {e}")
        return f"Error: {e}"
```

### Example Usage in Python

```python
import asyncio
from mcp.client import MCPClient

async def main():
    # Connect to your MCP server
    client = MCPClient()
    await client.connect_process(["python", "main.py"])
    
    # Use your tool
    result = await client.call_tool("call_your_model", {"prompt": "Your prompt here"})
    print(result)
    
    # Disconnect when done
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### Common Issues and Solutions

1. **"API key not configured" error**
   - Ensure your `.env` file includes the `DATASAUR_API_KEY` variable
   - Check that the API key is correctly copied from your Datasaur account

2. **"API URL not configured" error**
   - Make sure all needed Datasaur API URLs are set in your `.env` file
   - Verify the URLs follow the correct format

3. **Connection errors**
   - Check your internet connection
   - Verify your Datasaur account is active and has API access

4. **"Module not found" errors**
   - Ensure you've installed all dependencies: `pip install -r requirements.txt`
   - Activate your virtual environment if you're using one

5. **Permission issues**
   - Run your terminal or command prompt as administrator/with elevated permissions

## Extending Functionality

### Adding New Models

To add a new model to your MCP server:

1. Add a new environment variable in your `.env` file:
```
DATASAUR_ANOTHER_MODEL_API_URL=your_another_model_url
```

2. Add the environment variable to `claude_desktop_config.json` (if using Claude Desktop)

3. Create a new function in `main.py` following the pattern shown in the "Example Tool Function Pattern" section above:

```python
@mcp.tool()
async def call_another_model(prompt: str) -> str:
    """
    Documentation for your new model function.
    """
    logging.debug(f"Received prompt: {prompt[:100]}...")

    # Check configuration
    if not DATASAUR_ANOTHER_MODEL_API_URL or not DATASAUR_API_KEY:
        logging.error("DATASAUR_ANOTHER_MODEL_API_URL or DATASAUR_API_KEY not configured.")
        return "Error: Configuration missing on server."

    headers = {
        'Authorization': f'Bearer {DATASAUR_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = { "messages": [ {"role": "user", "content": prompt} ] }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(DATASAUR_ANOTHER_MODEL_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            response_json = response.json()
            
            # Process and return response
            if 'choices' in response_json and response_json['choices']:
                if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
                    return str(response_json['choices'][0]['message']['content'])
            
            return "Error: Unexpected response format"
    except Exception as e:
        logging.error(f"Error: {e}")
        return f"Error: {e}"
```

### Customizing Response Processing

To customize how responses are processed:

1. Modify the response processing section of the relevant function
2. You can parse JSON, extract specific fields, or format the response differently

### Adding Authentication

For additional authentication:

1. Add authentication credentials to your `.env` file
2. Modify the headers in your API requests

## Resources

- [Model Context Protocol Documentation](https://github.com/model-context-protocol/model-context-protocol)
- [Datasaur Documentation](https://www.datasaur.ai/docs)
- [Python httpx Library](https://www.python-httpx.org/)
- [FastMCP Documentation](https://github.com/model-context-protocol/fastmcp) (if applicable)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created with ❤️ using Datasaur Sandbox 