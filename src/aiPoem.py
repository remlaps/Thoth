import requests
import json
import utils
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def aiPoem(arliaiKey, arliaiModel, arliaiUrl, commentList, maxTokens=1500):
    today = datetime.now()

    systemPrompt = f"""
You are a writer of short stories.  Today is {today}.
"""

    curationPrompt = """
    Synthesize a short story - less than 1000 words - that combines themes from the comments below.
    
    The story should be entertaining, engaging, original, and reflect a human perspective.
    
    The story should be written in a style that is appropriate for a public blog post.

    VERY IMPORTANT:
    - Do not include any comments, explanations, introduction or conclusion.
    - Just include the title and the story.
    - The poem should be original and not copied or otherwise plagiarized.
    - The poem should be shorter than 5 stanzas.
    - Incorporate ideas from all of the comments.
    - Make the story SEO friendly.

    Here are the comments: 
    """

    for comment in commentList:
        curationPrompt += f"\n\n{comment['body']}\n\n"

    payload = json.dumps({
        "model": arliaiModel,
        "messages": [
            {
                "role": "system",
                "content": systemPrompt
            },
            {
                "role": "user",
                "content": f"{curationPrompt}"
            }
        ],
        "repetition_penalty": 1.1,
        "temperature": 0.6,
        "top_p": 0.9,
        "top_k": 40,
        "max_tokens": maxTokens,
        "stream": False,
        "frequency_penalty": 0.3,
        "presence_penalty": 0.3,
        "stop_sequences": ["\n\n\n"]
    })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {arliaiKey}"
    }

    aiResponseReceived = False
    while not aiResponseReceived:
        try:
            response = requests.post(arliaiUrl, headers=headers, data=payload)
            response.raise_for_status()
            aiPoem = response.json()['choices'][0]['message']['content']
            return aiPoem
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            print ("In aiPoem: Sleeping for 15 minutes before retrying...")
            time.sleep(900)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}, response text: {response.text}")
            return "JSON Error"
        except KeyError as e:
            logging.error(f"KeyError: {e}, response json: {response.json()}")
            return "Response Error"
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return "Unexpected Error"
        
