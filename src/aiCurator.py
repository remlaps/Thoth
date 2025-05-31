import requests
import json
import utils
from datetime import datetime
import logging
import configparser
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()
config.read('config/config.ini')

systemPromptFile=config.get('ARLIAI', 'SYSTEM_PROMPT_FILE')
systemPromptTemplateFile=config.get('ARLIAI', 'SYSTEM_PROMPT_TEMPLATE', fallback=None)
userPromptFile=config.get('ARLIAI', 'USER_PROMPT_FILE')
userPromptTemplateFile=config.get('ARLIAI', 'USER_PROMPT_TEMPLATE', fallback=None)

def ensurePromptFileExists(promptFilePath, templateFilePath, promptTypeName):
    """Checks if a prompt file exists, and copies from template if not."""
    if not Path(promptFilePath).exists():
        logging.info(f"{promptTypeName} prompt file '{promptFilePath}' not found.")
        if templateFilePath and Path(templateFilePath).exists():
            try:
                # Ensure directory exists
                Path(promptFilePath).parent.mkdir(parents=True, exist_ok=True)
                with open(templateFilePath, 'r', encoding='utf-8') as src_file:
                    with open(promptFilePath, 'w', encoding='utf-8') as dest_file:
                        dest_file.write(src_file.read())
                logging.info(f"Copied content from template '{templateFilePath}' to '{promptFilePath}'.")

            except Exception as e:
                logging.error(f"Error copying {promptTypeName} prompt template: {e}")
        elif templateFilePath:
            logging.warning(f"{promptTypeName} AI prompt template '{templateFilePath}' not found. Cannot create default prompt file.")
        else:
            logging.warning(f"No template file specified for {promptTypeName} prompt. Cannot create default prompt file.")

ensurePromptFileExists(systemPromptFile, systemPromptTemplateFile, "System")
ensurePromptFileExists(userPromptFile, userPromptTemplateFile, "User")

def aicurate(arliaiKey, arliaiModel, arliaiUrl, postBody, maxTokens=1024):
    if ( arliaiModel[:6] == "gemini" ):
        stopParameter = "stop"
    else:
        stopParameter = "stop_sequences"

    today = datetime.now()
    try:
        with open(systemPromptFile, 'r', encoding='utf-8') as f:
            systemPrompt = f.read()
    except FileNotFoundError:
        logging.error(f"System prompt file not found: {systemPromptFile}")
        return "System Prompt File Error"

    systemPrompt += "\n\nToday is {today}.\n"

    try:
        with open(userPromptFile, 'r', encoding='utf-8') as f:
            curationPrompt = f.read()
    except FileNotFoundError:
        logging.error(f"User prompt file not found: {userPromptFile}")
        return "Curation Prompt File Error"

    postBody = utils.remove_formatting(postBody)

    payload = json.dumps({
        "model": arliaiModel,
        "messages": [
            {
                "role": "system",
                "content": systemPrompt
            },
            {
                "role": "user",
                "content": f"{curationPrompt} - {postBody}"
            }
        ],
        # "repetition_penalty": 1.1,
        "temperature": 0.6,
        "top_p": 0.9,
        # "top_k": 40,
        "max_tokens": maxTokens,
        "stream": False,
        # "frequency_penalty": 0.3,
        # "presence_penalty": 0.3,
        stopParameter: ["END_OF_CURATION_REPORT", "DO NOT CURATE"]
        # "stop_sequences": ["\n\n\n", "END_OF_CURATION_REPORT", "DO NOT CURATE"]
        # "stop": ["\n\n\n", "END_OF_CURATION_REPORT", "DO NOT CURATE"]

    })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {arliaiKey}"
    }

    try:
        response = requests.post(arliaiUrl, headers=headers, data=payload)
        response.raise_for_status()
        aiResponse = response.json()['choices'][0]['message']['content']
        return aiResponse
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return "API Error"
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}, response text: {response.text}")
        return "JSON Error"
    except KeyError as e:
        logging.error(f"KeyError: {e}, response json: {response.json()}")
        return "Response Error"
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return "Unexpected Error"