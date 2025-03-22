import requests
import json
import utils

def aicurate(arliaiKey, arliaiModel, arliaiUrl, postBody):
    curationPrompt = """
Evaluate the following article based on quality, originality, and value to readers. Analyze:

- Writing quality (grammar, organization, readability)
- Originality (unique perspectives, not AI-generated or plagiarized)
- Engagement potential (interesting, informative, thought-provoking)
- Appropriate content (no gambling, prize contests, cryptocurrency, or prohibited topics)

If ANY of these conditions are met, respond ONLY with: "DO NOT CURATE."
- Content appears AI-generated or plagiarized
- Poor writing quality (confusing, repetitive, disorganized)
- Focuses on gambling, prize contests, giveaways, or any competitions involving rewards
- Contains cryptocurrency discussion, trading advice, or token promotion
- Lacks substance or original thinking

IMPORTANT: Sports competitions and athletic events are acceptable topics. Only reject posts about contests where participants can win prizes, money, or other rewards.

Otherwise, create a curation report with ONLY the following three sections and NOTHING else:

1. KEY TAKEAWAYS (3-5 bullet points summarizing the main insights using SEO-friendly keywords)

2. TARGET AUDIENCE (Who would find this content most valuable and why)

3. CONVERSATION STARTERS (3 thought-provoking questions that could spark discussion around this topic)

DO NOT add any additional comments, conclusions, or sections beyond these three. Your response must end after the third section.

Here is the article: 
    """

    postBody = utils.remove_formatting(postBody)

    payload = json.dumps({
    "model": arliaiModel,
    "messages" : [
        {
            "role": "system", 
            "content": "You are an experienced content curator on the Steem blockchain. Your job is to evaluate content objectively, identifying high-quality posts that deserve visibility while filtering out low-quality or inappropriate content. When evaluating posts: focus on originality, clarity, and value to readers; look for well-structured content with proper grammar and formatting; prioritize posts that offer unique insights or perspectives; be vigilant about filtering out AI-generated content, plagiarism, and prohibited topics; follow the evaluation criteria in the curation prompt exactly. Your assessments should be fair, consistent, and helpful to both content creators and readers. When recommending content, provide clear reasons for your decision that highlight the post's strengths."
        },
        {
            "role": "user", 
            "content": f"{curationPrompt} - {postBody}"
        }
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
