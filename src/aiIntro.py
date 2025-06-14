from datetime import datetime
import requests
import json

def aiIntro(arliaiKey, arliaiModel, arliaiUrl, combinedComment, maxTokens=1024):
    today = datetime.now()
    systemPrompt = f"""
    You are a Thoth, an influencer and curator on the Steem blockchain.

    Today is {today.strftime('%Y-%m-%d')}.
    """
    userPrompt = f"""
    
    Read the following text.  Do not assume that any authors are still active on the blockchain and
       do not assume that the posts are recent.  They might be up to 10 years old.

       Use markdown to create a short SEO-friendly blog post to introduce it.
       
       Each of the entries in the text will be posted later, as separate replies.
       
       Refer to people on the Steem blockchain as "steemizens", not "steemians".

       Optionally, include a relevant riddle at the end of the blog post.
       
       Here is the text: {combinedComment}
    """

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
                "content": userPrompt
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
        payloadDict["frequency_penalty"] = 0.8
        payloadDict["presence_penalty"] = 0.8

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {arliaiKey}"
    }

    payload = json.dumps(payloadDict)

    response = requests.request("POST", arliaiUrl, headers=headers, data=payload)
    aiResponse = response.json()['choices'][0]['message']['content']
    print(aiResponse)
    return aiResponse