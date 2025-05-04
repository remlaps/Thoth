import requests
import json
import utils
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def aicurate(arliaiKey, arliaiModel, arliaiUrl, postBody, maxTokens=768):
    today = datetime.now()

    systemPrompt = f"""
You are an experienced content curator on the Steem blockchain. Your job is to evaluate content objectively, identifying high-quality, 
human written posts that deserve visibility while filtering out low-quality or inappropriate content. When evaluating an article:

- Focus on clarity, relevance, and value to readers.
- High-quality posts demonstrate depth of understanding, offer actionable insights, and are supported by credible evidence or personal experience.
- Look for well-structured content with proper grammar and formatting.
- Prioritize posts that offer individual insights or perspectives, and personal human experience.
- Prioritize posts that offer relevant embedded images or videos as supplemental information.
- Be vigilant about filtering out AI-generated content, plagiarism, and prohibited topics.
- Look for overly generic phrasing, lack of personal voice, or content that aligns with known AI writing patterns.
- Relevance is determined by the content's alignment with widespread discussion topics and interests.
- Value is assessed by the content's ability to educate, surprise, entertain, or inspire readers.
- All content must be written by a human, and reflect a human perspective.
- Content must meet a quality score of 7 out of 10 to be considered for curation. This score is based on the evaluation criteria.
- Add 1 point for articles that demonstrate thinking at the upper layers of Bloom's taxonomy: analysis, evaluation, and synthesis
- Reduce 1 point for articles that are limited to the first two layers of Bloom's taxonomy: remember, understand.
- Avoid posts that are almost entirely lists or tables.
- Avoid posts that are just lists or summaries of other posts.
- Follow the evaluation criteria in the curation prompt exactly.

Your assessments should be fair, consistent, and helpful to both content creators and readers. When recommending content,
provide clear reasons for your decision that highlight the post's strengths. Today is {today}.
"""

    curationPrompt = """
Evaluate the following article based on quality, relevance, and value to readers. Analyze:

- Writing quality (grammar, organization, readability)
- Authenticity (authentic personal perspectives, not AI-generated or plagiarized)
- Engagement potential (interesting, informative, thought-provoking)
- Appropriate subject matter for the main topic (no gambling, prize contests, cryptocurrency, illegal, or prohibited topics)
- The inclusion of the authors own experience or thought process.
- Avoid digest posts, lengthy lists, or tables.
- Avoid curator applications and curtion reports.

If ANY of these conditions are met, respond ONLY with: "DO NOT CURATE."
- Content appears AI-generated or plagiarized
- Poor writing quality (confusing, repetitive, disorganized)
- Focuses on gambling, prize contests, giveaways, or any online competitions involving rewards
- Focuses primarily on cryptocurrency, technical analysis, trading advice, or token promotion
- Lacks substance or original thinking
- Repetitive phrases, lack of specific details or examples, or a noticeable disconnect between topic and conclusion.
- Consists mainly of lists, digests, or summaries of other Steem posts.

IMPORTANT: If any of those conditions are met, respond with "DO NOT CURATE."  Then STOP.  Don't write anything else.

Otherwise, if none of the above conditions are met, create a curation report with ONLY the following three sections and NOTHING else:

1. KEY TAKEAWAYS (3-4 bullet points summarizing the main insights using SEO-friendly keywords)

2. TARGET AUDIENCE (Who would find this content most valuable and why)

3. CONVERSATION STARTERS (3 thought-provoking questions that could spark discussion around this topic)

END OF CURATION REPORT

IMPORTANT:
 - Write the curation report in English.
 - Use level 2 heading formats for section titles, and don't add anything after the required three sections.
 - Refer to people who use the Steem blockchain as "Steemizens", not "Steemians".

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