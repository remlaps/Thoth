import requests
import json
import utils

def aicurate(arliaiKey, arliaiModel, arliaiUrl, author, permlink, title, postBody):
    curationPrompt = """
    If the following article is boring, difficult to understand, seems plagiarized or seems like an AI wrote it then print: DO NOT CURATE. (and nothing else)

    Otherwise:
    1. Summarize this article in 3-5 bullet points.
    2. Describe the likely audience for the post.
    3. Offer 3 provocative discussion topics that might relate to the topic.
    """

    postBody = utils.remove_formatting(postBody)

    payload = json.dumps({
    "model": arliaiModel,
    "messages": [
        {"role": "system", "content": "You are a curator on the Steem blockchain.  You want to find valuable posts and help them get visibility."},
        {"role": "user", "content": "Hello!"},
        {"role": "curator", "content": "Hi!, how can I help you today?"},
        {"role": "user", "content": f"{curationPrompt} - {postBody}"}
    ],
    "repetition_penalty": 1.1,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_tokens": 1024,
    "stream": False
    })

    headers = {
    'Content-Type': 'application/json',
    'Authorization': f"Bearer {arliaiKey}"
    }

    try:
        response = requests.request("POST", arliaiUrl, headers=headers, data=payload)
    except requests.exceptions.InvalidSchema as e:
        print(f"Invalid URL: {arliaiUrl}")
        print(f"Error: {e}")
    aiResponse = response.json()['choices'][0]['message']['content']
    return aiResponse
