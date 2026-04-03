from datetime import datetime
import requests
import json
import re
import time
import random
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


def aiIntro(llmKey, llmModel, llmUrl, startTime, endTime, combinedComment, maxTokens=8192, model_manager=None, enable_switching=False, dry_run=False, score_data=None):
    """
    Generate an introduction for a blog post using the AI API.
    
    Args:
        llmKey: API key for the LLM service
        llmModel: Model name (can be comma-separated list; will be handled by model_manager)
        llmUrl: URL for the LLM API
        startTime: Start time of the articles
        endTime: End time of the articles
        combinedComment: Combined summaries of articles
        maxTokens: Maximum tokens for the response
        model_manager: Optional ModelManager instance for handling multiple models
        score_data: Optional list of score results for curated posts
        
    Returns:
        str: The AI-generated introduction or error message
    """
    today = datetime.now()
    
    # Use provided model_manager or create one from the model string
    if model_manager is None:
        model_manager = ModelManager(llmModel)
    
    loc = Localization()
    modelPrefix = model_manager.get_model_prefix()
    
    config = configparser.ConfigParser()
    config.read('config/config.ini')
    output_language = config.get('LLM', 'OUTPUT_LANGUAGE', fallback='English')

    ensurePromptFileExists('config/introSystemPrompt.txt', f'config/introSystemPromptTemplate_{modelPrefix}.txt', "Intro System")
    ensurePromptFileExists('config/introUserPrompt.txt', f'config/introUserPromptTemplate_{modelPrefix}.txt', "Intro User")

    today_str = today.strftime('%Y-%m-%d')
    start_str = startTime.strftime('%Y-%m-%d')
    end_str = endTime.strftime('%Y-%m-%d')

    if start_str == end_str:
        datePrompt = f"{loc.get('today_is', date=today_str)} {loc.get('articles_published_on', date=start_str)}"
    else:
        datePrompt = f"{loc.get('today_is', date=today_str)}\n\n{loc.get('articles_published_between', start_date=start_str, end_date=end_str)}"
    
    # Add score summary to the date prompt if available
    if score_data and len(score_data) > 0:
        avg_score = sum(score['total_score'] for score in score_data) / len(score_data)
        score_summary = f"\n\n{loc.get('curated_posts_average_score', avg_score=round(avg_score, 1))}"
        datePrompt += score_summary
    
    # Context token management for ArliAI's 12K limit
    if llmUrl.startswith("https://api.arliai.com"):
        if maxTokens > 4096:
            maxTokens = 4096
        max_chars = 30000
        if len(combinedComment) > max_chars:
            logging.warning(f"Combined comments exceed safe limit for ArliAI 12K context. Truncating from {len(combinedComment)} to {max_chars} characters.")
            combinedComment = combinedComment[:max_chars] + "\n...[TRUNCATED FOR LENGTH]..."

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
    
    payloadDict = {
        "temperature": 0.3,
        "top_p": 0.85,
        "max_tokens": maxTokens,
        "stream": False,
        "stop": ["END_OF_CURATION_REPORT"]
    }

    if llmUrl.startswith("https://api.arliai.com"):      ## VLLM API/models
        payloadDict["repetition_penalty"] = 1.1
        payloadDict["top_k"] = 40
        payloadDict["frequency_penalty"] = 0.3
        payloadDict["presence_penalty"] = 0.3
        payloadDict["min_p"] = 0.0

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {llmKey}"
    }

    max_retries = int(config.get('LLM', 'MAX_RETRIES', fallback=5))
    initial_backoff = float(config.get('LLM', 'INITIAL_BACKOFF_SECONDS', fallback=2.0))
    jitter_factor = float(config.get('LLM', 'JITTER_FACTOR', fallback=0.2))
    
    # Try models in sequence if rate limiting occurs
    while True:
        current_model = model_manager.current_model
        
        payloadDict["model"] = current_model
        payloadDict["messages"] = construct_messages(llmUrl, current_model, systemPrompt, userPrompt)
        payload = json.dumps(payloadDict)

        for attempt in range(max_retries):
            try:
                logging.debug(f"Attempt {attempt + 1}/{max_retries} to call AI API for intro: {llmUrl} with model {current_model}")
                response = requests.post(llmUrl, headers=headers, data=payload)
                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                data = response.json()
                if isinstance(data, list):
                    data = data[0] if len(data) > 0 else {}
                rawResponse = data.get('choices', [{}])[0].get('message', {}).get('content') or ''

                # Post-process to remove any <think>...</think> blocks that the model might still include.
                cleanedResponse = re.sub(r'<think>.*?</think>', '', str(rawResponse), flags=re.DOTALL).strip()
                cleanedResponse = re.sub(r'<thought>.*?</thought>', '', str(rawResponse), flags=re.DOTALL).strip()

                print(f"Intro Response before cleaning: {rawResponse}")
                print(f"Intro Response after cleaning: {cleanedResponse}")

                return cleanedResponse # Success, so we exit the function
                
            except requests.exceptions.HTTPError as e:
                is_rate_limited = False
                status_code = e.response.status_code if e.response is not None else "Unknown"
                
                # Check for rate limiting
                if status_code in [429, 500, 502, 503, 504]:
                    is_rate_limited = True
                
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
                    backoff_time = initial_backoff * (2 ** attempt)
                    actual_wait_time = backoff_time + random.uniform(0, jitter_factor * backoff_time)
                    logging.info(f"Retrying in {actual_wait_time:.2f} seconds...")
                    time.sleep(actual_wait_time)
                    
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logging.error(f"Error during AI Intro generation (Attempt {attempt + 1}/{max_retries}): {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    logging.error(f"Response body: {response.text}")
                
                if attempt < max_retries - 1:
                    backoff_time = initial_backoff * (2 ** attempt)
                    actual_wait_time = backoff_time + random.uniform(0, jitter_factor * backoff_time)
                    logging.info(f"Retrying in {actual_wait_time:.2f} seconds...")
                    time.sleep(actual_wait_time)
            except Exception as e:
                logging.error(f"Unexpected error during AI Intro generation (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    backoff_time = initial_backoff * (2 ** attempt)
                    actual_wait_time = backoff_time + random.uniform(0, jitter_factor * backoff_time)
                    logging.info(f"Retrying in {actual_wait_time:.2f} seconds...")
                    time.sleep(actual_wait_time)
        else:
            # If we exhaust retries for this model, log and exit
            logging.error(f"Exhausted all retries for model {current_model}.")
            return loc.get('error_intro_generation')