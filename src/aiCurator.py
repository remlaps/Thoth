import re
import requests
import json
import time
import random
from datetime import datetime
import logging
import configparser
from pathlib import Path
from modelManager import ModelManager
from promptHelper import construct_messages
from localization import Localization

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()
config.read('config/config.ini')

# Initialize ModelManager with potentially comma-separated model list
model_manager = ModelManager(config.get('LLM', 'LLM_MODEL', fallback='gemini'))
modelPrefix = model_manager.get_model_prefix()
print(f"Using model prefix: {modelPrefix}")

systemPromptFile=config.get('LLM', 'SYSTEM_PROMPT_FILE')
systemPromptTemplateFile=f"{config.get('LLM', 'SYSTEM_PROMPT_TEMPLATE', fallback=None)}_{modelPrefix}.txt"
userPromptFile=config.get('LLM', 'USER_PROMPT_FILE')
userPromptTemplateFile=f"{config.get('LLM', 'USER_PROMPT_TEMPLATE', fallback=None)}_{modelPrefix}.txt"
print(f"Using system prompt file: {systemPromptFile}")
print(f"Using user prompt file: {userPromptFile}")
print(f"Using system prompt template file: {systemPromptTemplateFile}")
print(f"Using user prompt template file: {userPromptTemplateFile}")
print(f"Available models: {model_manager.models}")

# API Retry settings
MAX_RETRIES = int(config.get('LLM', 'MAX_RETRIES', fallback=3))
INITIAL_BACKOFF_SECONDS = float(config.get('LLM', 'INITIAL_BACKOFF_SECONDS', fallback=2.0))
JITTER_FACTOR = float(config.get('LLM', 'JITTER_FACTOR', fallback=0.2))

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

def aicurate(llmKey, llmModel, llmUrl, postBody, maxTokens=8192, model_manager=None, enable_switching=False, dry_run=False, author="", permlink=""):
    """
    Curate a post using the AI API.
    
    Args:
        llmKey: API key for the LLM service
        llmModel: Model name (can be comma-separated list; will be handled by model_manager)
        llmUrl: URL for the LLM API
        postBody: The post content to evaluate
        maxTokens: Maximum tokens for the response
        model_manager: Optional ModelManager instance for handling multiple models
        author: Optional author name for debugging/logging
        permlink: Optional permlink for debugging/logging
        
    Returns:
        str: The AI curation response or error message
    """
    today = datetime.now()
    llmKey = llmKey.split()[0]  # Eliminate comments after the key (should be redundant)
    loc = Localization()
    
    # Use provided model_manager or create one from the model string
    if model_manager is None:
        model_manager = ModelManager(llmModel)
    
    output_language = config.get('LLM', 'OUTPUT_LANGUAGE', fallback='English')
    try:
        with open(systemPromptFile, 'r', encoding='utf-8') as f:
            systemPrompt = f.read().format(language=output_language)
    except FileNotFoundError:
        logging.error(f"System prompt file not found: {systemPromptFile}")
        return "System Prompt File Error"

    systemPrompt += f"\n\n{loc.get('today_is', date=today.strftime('%Y-%m-%d'))}\n" # Correctly format and append today's date

    try:
        with open(userPromptFile, 'r', encoding='utf-8') as f:
            curationPromptTemplate = f.read()
        curationPrompt = curationPromptTemplate.format(
            language=output_language,
            key_takeaways_header=loc.get('heading_key_takeaways'),
            target_audience_header=loc.get('heading_target_audience'),
            conversation_starters_header=loc.get('heading_conversation_starters')
        )
    except FileNotFoundError:
        logging.error(f"User prompt file not found: {userPromptFile}")
        return "Curation Prompt File Error"

    if not postBody or postBody.strip() == "":
        logging.error("aicurate: Received an empty or whitespace-only postBody. Cannot proceed.")
        return "Content Error - Empty Body"

    # Context token management for ArliAI's 12K limit
    if llmUrl.startswith("https://api.arliai.com"):
        if maxTokens > 4096:
            maxTokens = 4096
        # 1 token is approx 4 characters. 12K tokens is approx 48K characters.
        # Cap post body at 30,000 chars to leave plenty of room for prompt and generation.
        max_chars = 30000
        if len(postBody) > max_chars:
            post_id = f"@{author}/{permlink}" if author and permlink else "Unknown Post"
            logging.warning(f"[{post_id}] Post body exceeds safe limit for ArliAI 12K context. Truncating from {len(postBody)} to {max_chars} characters.")
            postBody = postBody[:max_chars] + "\n...[TRUNCATED FOR LENGTH]..."

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {llmKey}"
    }

    # Try models in sequence if rate limiting occurs
    while True:
        current_model = model_manager.current_model
        
        payloadDict = {
            "model": current_model,
            "messages": construct_messages(llmUrl, current_model, systemPrompt, f"{curationPrompt}\n\n## ARTICLE FOR EVALUATION\n\n{postBody}"),
            "temperature": 0.3,
            "top_p": 0.85,
            "max_tokens": maxTokens,
            "stream": False,
            "stop": ["END_OF_CURATION_REPORT"]
        }

        if llmUrl.startswith("https://api.arliai.com"):  # VLLM API/models
            payloadDict["repetition_penalty"] = 1.1
            payloadDict["top_k"] = 40
            payloadDict["frequency_penalty"] = 0.3
            payloadDict["presence_penalty"] = 0.3
            payloadDict["min_p"] = 0.0

        payload = json.dumps(payloadDict)

        for attempt in range(MAX_RETRIES + 1):
            try:
                logging.debug(f"Attempt {attempt + 1}/{MAX_RETRIES + 1} to call AI API: {llmUrl} with model {current_model}")
                response = requests.post(llmUrl, headers=headers, data=payload)
                response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
                
                data = response.json()
                if isinstance(data, list):
                    data = data[0] if len(data) > 0 else {}
                rawResponse = data.get('choices', [{}])[0].get('message', {}).get('content') or ''

                # Post-process to remove any <think>...</think> blocks that the model might still include.
                # The re.DOTALL flag ensures that the pattern matches even if the block spans multiple lines.
                # .strip() removes any leading/trailing whitespace left after the removal.
                cleanedResponse = re.sub(r'<think>.*?</think>', '', str(rawResponse), flags=re.DOTALL).strip()

                post_id = f"@{author}/{permlink}" if author and permlink else "Unknown Post"
                
                if not cleanedResponse:
                    logging.info(f"[{post_id}] AI model returned a completely empty response. Interpreting as an implicit rejection.")
                    return "DO NOT CURATE"

                if len(cleanedResponse) < 100: # Or another threshold for "suspiciously short"
                    logging.warning(f"[{post_id}] Received suspiciously short AI response after cleaning: '{cleanedResponse}'.")
                    logging.warning(f"Original raw response: '{rawResponse}'")  # Add this line
                    logging.warning(f"Request payload that led to short response: {json.dumps(payloadDict, indent=2)}")

                print(f"Response before cleaning:", rawResponse)
                print(f"Response after cleaning:", cleanedResponse)
                return cleanedResponse

            except requests.exceptions.HTTPError as e:
                is_rate_limited = False
                is_overloaded_error = False
                error_details_text = ""
                status_code = e.response.status_code if e.response is not None else "Unknown"

                try:
                    error_details = e.response.json()
                    error_details_text = json.dumps(error_details, indent=2)
                    
                    # Check for rate limiting (429 or server errors like 502, 503, 504)
                    if status_code == 429:
                        is_rate_limited = True
                    elif status_code == 503:
                        is_overloaded_error = True
                        is_rate_limited = True
                    elif status_code in [500, 502, 504]:
                        is_rate_limited = True
                except json.JSONDecodeError:
                    error_details_text = e.response.text if e.response is not None else "No response text available"
                    if status_code in [429, 500, 502, 503, 504]:
                        is_rate_limited = True
                        if status_code == 503:
                            is_overloaded_error = True

                # If rate limited and we have another model available, mark it and optionally switch
                if is_rate_limited and model_manager.has_next_model():
                    logging.warning(
                        f"Model {current_model} is rate limited (status {status_code}). "
                        f"Attempting to mark/switch to next available model."
                    )
                    if enable_switching:
                        switched = model_manager.mark_rate_limited(dry_run=dry_run)
                        if switched:
                            break  # Break inner loop to retry with new model
                        else:
                            logging.info("No switch performed (dry-run or exhausted models). Continuing retries for current model.")
                    else:
                        logging.info("Model switching disabled by configuration. Continuing retries for current model.")
                
                # Handle retries for the same model (for non-rate-limit errors or last model)
                if is_overloaded_error and attempt < MAX_RETRIES and not model_manager.has_next_model():
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
                import traceback
                logging.error(f"An unexpected error occurred: {type(e_unexp).__name__} - {e_unexp}\n{traceback.format_exc()}\nAttempt {attempt + 1}/{MAX_RETRIES + 1}.")
                return "Unexpected Error"
        else:
            # If we get here, we've exhausted retries for this model without switching
            logging.error(f"Exhausted all retries ({MAX_RETRIES + 1} attempts) for model {current_model}.")
            return "API Error - Max Retries Exceeded (General)"
