import requests
import json
import utils
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def aicurate(arliaiKey, arliaiModel, arliaiUrl, postBody, maxTokens=768):
    today = datetime.now()

# New prompt suggested by Gemini

    systemPrompt = f"""
You are an experienced content curator on the Steem blockchain. Your job is to evaluate content objectively, identifying high-quality, 
human written posts that deserve visibility while filtering out low-quality or inappropriate content.

Evaluate articles for
    quality (clarity, structure, grammar),
    originality (human perspective, unique insights, not AI/plagiarized),
    relevance, and
    reader value (actionable, evidence-backed, educational, surprising, entertaining, inspiring).
    
Prioritize depth, personal experience, and Bloom's taxonomy levels (add 1 for analysis/evaluation/synthesis, subtract 1 for remember/understand).

Exclude lists/tables, AI, plagiarism, and prohibited topics.

Use SEO-friendly language and markdown formatting in your replies.

Minimum quality score: 7/10 based on criteria. Today is {today}.
"""

# New prompt suggested by Gemini

    curationPrompt = """
Evaluate this article for
   curation: quality (writing, organization, readability),
   originality (unique, not AI/plagiarized),
   relevance, reader value,
   engagement (interesting, informative, thought-provoking), and
   topic appropriateness (excluding gambling, contests, crypto, prohibited content; avoid digests, long lists/tables;
   include author's experience/thoughts).

If the article is
   AI/plagiarized,
   poorly written (confusing, repetitive, disorganized),
   focuses on gambling/contests/giveaways,
   primarily discusses crypto (analysis, advice, promotion),
   lacks substance/originality, or
   uses repetitive phrases/lacks detail/has a disconnected conclusion,
respond ONLY with: "DO NOT CURATE." Then STOP.

Otherwise, provide a curation report with ONLY these three sections:

1. KEY TAKEAWAYS (3-4 bullet points)
2. TARGET AUDIENCE (Who and why)
3. CONVERSATION STARTERS (3 relevant questions for discussion)

VERY IMPORTANT:
- Do not add anything after these three sections.
- Use markdown, English, and refer to Steem users as "Steemizens" (not "Steemians").
- Remember to use SEO friendly language.
- Use Level 3 headers for each section title.
- Use bullet points for KEY TAKEAWAYS and CONVERSATION STARTERS.

Here is the article: 
    """
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
        "repetition_penalty": 1.1,
        "temperature": 0.6,
        "top_p": 0.9,
        "top_k": 40,
        "max_tokens": maxTokens,
        "stream": False,
        "frequency_penalty": 0.3,
        "presence_penalty": 0.3,
        "stop_sequences": ["\n\n\n", "END_OF_CURATION_REPORT", "DO NOT CURATE"]
    })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {arliaiKey}"
    }

    retryCount = 0
    aiResponseReceived = False
    while not aiResponseReceived and retryCount < 5:
        try:
            response = requests.post(arliaiUrl, headers=headers, data=payload)
            response.raise_for_status()
            aiResponse = response.json()['choices'][0]['message']['content']
            return aiResponse
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            print ("Sleeping for 30 minutes before retrying...")
            retryCount += 1
            time.sleep(1800)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}, response text: {response.text}")
            return "JSON Error"
        except KeyError as e:
            logging.error(f"KeyError: {e}, response json: {response.json()}")
            return "Response Error"
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return "Unexpected Error"