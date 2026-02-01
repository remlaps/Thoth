from datetime import datetime
import requests
import json
import re
import time
import configparser
import logging
from pathlib import Path
from modelManager import ModelManager
from promptHelper import construct_messages
from localization import Localization

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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


def aiIntro(arliaiKey, arliaiModel, arliaiUrl, startTime, endTime, combinedComment, maxTokens=8192, model_manager=None, enable_switching=False, dry_run=False):
    """
    Generate an introduction for a blog post using the AI API.
    
    Args:
        arliaiKey: API key for the LLM service
        arliaiModel: Model name (can be comma-separated list; will be handled by model_manager)
        arliaiUrl: URL for the LLM API
        startTime: Start time of the articles
        endTime: End time of the articles
        combinedComment: Combined summaries of articles
        maxTokens: Maximum tokens for the response
        model_manager: Optional ModelManager instance for handling multiple models
        
    Returns:
        str: The AI-generated introduction or error message
    """
    today = datetime.now()
    
    # Use provided model_manager or create one from the model string
    if model_manager is None:
        model_manager = ModelManager(arliaiModel)
    
    loc = Localization()
    modelPrefix = model_manager.get_model_prefix()
    
    config = configparser.ConfigParser()
    config.read('config/config.ini')
    output_language = config.get('ARLIAI', 'OUTPUT_LANGUAGE', fallback='English')

    ensurePromptFileExists('config/introSystemPrompt.txt', f'config/introSystemPromptTemplate_{modelPrefix}.txt', "Intro System")
    ensurePromptFileExists('config/introUserPrompt.txt', f'config/introUserPromptTemplate_{modelPrefix}.txt', "Intro User")

    today_str = today.strftime('%Y-%m-%d')
    start_str = startTime.strftime('%Y-%m-%d')
    end_str = endTime.strftime('%Y-%m-%d')

    if start_str == end_str:
        datePrompt = f"{loc.get('today_is', date=today_str)} {loc.get('articles_published_on', date=start_str)}"
    else:
        datePrompt = f"{loc.get('today_is', date=today_str)}\n\n{loc.get('articles_published_between', start_date=start_str, end_date=end_str)}"
    
    try:
        with open('config/introSystemPrompt.txt', 'r', encoding='utf-8') as f:
            systemPrompt = f.read().format(datePrompt=datePrompt, language=output_language)
        with open('config/introUserPrompt.txt', 'r', encoding='utf-8') as f:
            userPrompt = f.read().format(combinedComment=combinedComment, language=output_language)
    except FileNotFoundError as e:
        logging.error(f"Prompt file not found: {e}")
        return loc.get('error_prompt_missing')
    except Exception as e:
        logging.error(f"Error reading prompt file: {e}")
        return loc.get('error_prompt_error')
    
    if arliaiUrl.startswith("https://generativelanguage.googleapis.com"):  ## Google API/models
        stop_param_name = "stop"
    else:
        stop_param_name = "stop_sequences"

    payloadDict = {
        "temperature": 0.3,
        "top_p": 0.85,
        "max_tokens": maxTokens,
        "stream": False,
        stop_param_name: ["END_OF_CURATION_REPORT", "DO NOT CURATE"]
    }

    if arliaiUrl.startswith("https://api.arliai.com"):      ## ARLIAI API/models
        payloadDict["repetition_penalty"] = 1.1
        payloadDict["top_k"] = 40
        payloadDict["frequency_penalty"] = 0.8
        payloadDict["presence_penalty"] = 0.8
        payloadDict["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": False}
        }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {arliaiKey}"
    }

    max_retries = 5
    
    # Try models in sequence if rate limiting occurs
    while True:
        current_model = model_manager.current_model
        
        payloadDict["model"] = current_model
        payloadDict["messages"] = construct_messages(arliaiUrl, current_model, systemPrompt, userPrompt)
        payload = json.dumps(payloadDict)

        for attempt in range(max_retries):
            try:
                logging.debug(f"Attempt {attempt + 1}/{max_retries} to call AI API for intro: {arliaiUrl} with model {current_model}")
                response = requests.post(arliaiUrl, headers=headers, data=payload)
                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                data = response.json()
                if isinstance(data, list):
                    data = data[0]
                rawResponse = data['choices'][0]['message']['content']

                # Post-process to remove any <think>...</think> blocks that the model might still include.
                cleanedResponse = re.sub(r'<think>.*?</think>', '', rawResponse, flags=re.DOTALL).strip()

                print(f"Intro Response before cleaning: {rawResponse}")
                print(f"Intro Response after cleaning: {cleanedResponse}")

                return cleanedResponse # Success, so we exit the function
                
            except requests.exceptions.HTTPError as e:
                is_rate_limited = False
                status_code = e.response.status_code if e.response is not None else "Unknown"
                
                # Check for rate limiting
                if status_code == 429:
                    is_rate_limited = True
                elif status_code == 503:
                    try:
                        error_details = e.response.json()
                        if isinstance(error_details, list) and len(error_details) > 0 and \
                           isinstance(error_details[0], dict) and 'error' in error_details[0] and \
                           isinstance(error_details[0]['error'], dict) and \
                           "overloaded" in error_details[0]['error'].get('message', '').lower():
                            is_rate_limited = True
                    except (json.JSONDecodeError, KeyError, AttributeError):
                        pass
                
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
                
                # Otherwise, log error and continue retrying
                logging.error(f"Error during AI Intro generation (Attempt {attempt + 1}/{max_retries}): {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    logging.error(f"Response body: {response.text}")
                
                if attempt < max_retries - 1:
                    logging.info("Retrying in 60 seconds...")
                    time.sleep(60)
                    
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logging.error(f"Error during AI Intro generation (Attempt {attempt + 1}/{max_retries}): {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    logging.error(f"Response body: {response.text}")
                
                if attempt < max_retries - 1:
                    logging.info("Retrying in 60 seconds...")
                    time.sleep(60)
            except Exception as e:
                logging.error(f"Unexpected error during AI Intro generation (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logging.info("Retrying in 60 seconds...")
                    time.sleep(60)
        else:
            # If we exhaust retries for this model, log and exit
            logging.error(f"Exhausted all retries for model {current_model}.")
            return loc.get('error_intro_generation')