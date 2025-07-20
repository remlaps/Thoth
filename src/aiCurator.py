import requests
import json
import time
import random
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

# API Retry settings
MAX_RETRIES = int(config.get('ARLIAI', 'MAX_RETRIES', fallback=3))
INITIAL_BACKOFF_SECONDS = float(config.get('ARLIAI', 'INITIAL_BACKOFF_SECONDS', fallback=2.0))
JITTER_FACTOR = float(config.get('ARLIAI', 'JITTER_FACTOR', fallback=0.2))

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

def aicurate(arliaiKey, arliaiModel, arliaiUrl, postBody, maxTokens=8192):
    today = datetime.now()
    arliaiKey = arliaiKey.split()[0]  # Eliminate comments after the key (should be redundant)
    
    try:
        with open(systemPromptFile, 'r', encoding='utf-8') as f:
            systemPrompt = f.read()
    except FileNotFoundError:
        logging.error(f"System prompt file not found: {systemPromptFile}")
        return "System Prompt File Error"

    systemPrompt += f"\n\nToday is {today.strftime('%Y-%m-%d')}.\n" # Correctly format and append today's date

    try:
        with open(userPromptFile, 'r', encoding='utf-8') as f:
            curationPrompt = f.read()
    except FileNotFoundError:
        logging.error(f"User prompt file not found: {userPromptFile}")
        return "Curation Prompt File Error"

    if not postBody or postBody.strip() == "":
        logging.error("aicurate: Received an empty or whitespace-only postBody. Cannot proceed.")
        return "Content Error - Empty Body"

    if arliaiModel.startswith("gemini"):
        stop_param_name = "stop"
    else:
        stop_param_name = "stop_sequences"

    payloadDict = {
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
        "temperature": 0.3,
        "top_p": 0.85,
        "max_tokens": maxTokens,
        "stream": False,
        stop_param_name: ["END_OF_CURATION_REPORT", "DO NOT CURATE"]
    }

    if arliaiModel.startswith("Mistral-Nemo"):
        payloadDict["repetition_penalty"] = 1.1
        payloadDict["top_k"] = 40
        payloadDict["frequency_penalty"] = 0.3
        payloadDict["presence_penalty"] = 0.3

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {arliaiKey}"
    }

    payload = json.dumps(payloadDict)

    for attempt in range(MAX_RETRIES + 1):
        try:
            logging.debug(f"Attempt {attempt + 1}/{MAX_RETRIES + 1} to call AI API: {arliaiUrl} with model {arliaiModel}")
            response = requests.post(arliaiUrl, headers=headers, data=payload)
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
            try:
                aiResponse = response.json()['choices'][0]['message']['content']
            except KeyError:
                logging.error(f"KeyError accessing response data: 'content'. Response JSON: {response.json()}")
                return "Response Error"

            if len(aiResponse) < 100: # Or another threshold for "suspiciously short"
                logging.warning(f"Received suspiciously short AI response: '{aiResponse}'.")
                logging.warning(f"Request payload that led to short response: {json.dumps(payloadDict, indent=2)}") # Be mindful of log size/sensitivity
                # You could also log response.text here if you suspect JSON parsing issues for these cases

            return aiResponse

        except requests.exceptions.HTTPError as e:
            is_overloaded_error = False
            error_details_text = ""
            status_code = e.response.status_code if e.response is not None else "Unknown"

            try:
                error_details = e.response.json()
                error_details_text = json.dumps(error_details, indent=2)
                if status_code == 503 and \
                   isinstance(error_details, list) and len(error_details) > 0 and \
                   isinstance(error_details[0], dict) and 'error' in error_details[0] and \
                   isinstance(error_details[0]['error'], dict) and \
                   error_details[0]['error'].get('code') == 503 and \
                   "The model is overloaded. Please try again later." in error_details[0]['error'].get('message', ''):
                    is_overloaded_error = True
            except json.JSONDecodeError:
                error_details_text = e.response.text if e.response is not None else "No response text available"

            if is_overloaded_error and attempt < MAX_RETRIES:
                backoff_time = INITIAL_BACKOFF_SECONDS * (1.25 ** attempt)
                jitter = random.uniform(0, JITTER_FACTOR * backoff_time)
                actual_wait_time = backoff_time + jitter
                logging.warning(
                    f"Model overloaded (503). Attempt {attempt + 1}/{MAX_RETRIES + 1}. "
                    f"Retrying in {actual_wait_time:.2f} seconds..."
                )
                time.sleep(actual_wait_time)
                continue
            else:
                error_message_intro = f"API request failed. Status: {status_code}."
                if e.response is not None:
                    error_message_intro = f"API request failed with status {status_code} ({e.response.reason}) for URL {e.request.url}."
                
                final_error_message = f"{error_message_intro} Attempt {attempt + 1}/{MAX_RETRIES + 1}."
                return_value = f"API Error - HTTP {status_code}"

                if is_overloaded_error: # Max retries for overload reached
                    final_error_message += " Max retries for model overload (503) exceeded."
                    return_value = "API Error - Model Overloaded (Max Retries)"
                
                final_error_message += f"\nResponse Content: {error_details_text}"
                logging.error(final_error_message)
                return return_value

        except requests.exceptions.RequestException as e: # Non-HTTP errors (e.g., network, DNS)
            logging.error(f"API request failed (network issue): {e}. Attempt {attempt + 1}/{MAX_RETRIES + 1}.")
            if attempt < MAX_RETRIES:
                backoff_time = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                jitter = random.uniform(0, JITTER_FACTOR * backoff_time)
                actual_wait_time = backoff_time + jitter
                logging.warning(f"Retrying network issue in {actual_wait_time:.2f} seconds...")
                time.sleep(actual_wait_time)
                continue
            else:
                logging.error(f"Max retries ({MAX_RETRIES + 1} attempts) exceeded for network issue.")
                return "API Error - Network Issue (Max Retries)"
        
        except json.JSONDecodeError as e_json:
            logging.error(f"JSON decode error for a successful response: {e_json}. Response text: {response.text if 'response' in locals() else 'Response object not available'}")
            return "JSON Error"
        except KeyError as e_key:
            logging.error(f"KeyError accessing response data: {e_key}. Response JSON: {response.json() if 'response' in locals() and hasattr(response, 'json') else 'Response JSON not available'}")
            return "Response Error"
        except Exception as e_unexp:
            logging.error(f"An unexpected error occurred: {e_unexp}. Attempt {attempt + 1}/{MAX_RETRIES + 1}.")
            return "Unexpected Error"

    logging.error(f"Exhausted all retries ({MAX_RETRIES + 1} attempts) for API call to {arliaiUrl}.")
    return "API Error - Max Retries Exceeded (General)"