import requests
import json
import utils
from datetime import datetime

today=datetime.now()

def aicurate(arliaiKey, arliaiModel, arliaiUrl, postBody):
    curationPrompt = """
Evaluate the following article based on quality, originality, relevance, and value to readers. Analyze:

- Writing quality (grammar, organization, readability)
- Originality (unique perspectives, not AI-generated or plagiarized)
- Engagement potential (interesting, informative, thought-provoking)
- Appropriate subject matter (no gambling, prize contests, cryptocurrency, or prohibited topics)
- The inclusion of the authors own experience or thought process.

If ANY of these conditions are met, respond ONLY with: "DO NOT CURATE. Confidence: X%" where X is your confidence level.
- Content appears AI-generated or plagiarized
- Poor writing quality (confusing, repetitive, disorganized)
- Focuses on gambling, prize contests, giveaways, or any competitions involving rewards
- Contains cryptocurrency discussion, trading advice, or token promotion
- Contains a high portion of tabular or statistical analysis
- Lacks substance or original thinking
- Repetitive phrases, lack of specific examples, or a noticeable disconnect between topic and conclusion.

IMPORTANT: Sports competitions and athletic events are acceptable topics. Only reject posts about contests where participants can win prizes, money, or other rewards.

Otherwise, create a curation report with ONLY the following three sections and NOTHING else:

1. KEY TAKEAWAYS (2-3 bullet points summarizing the main insights using SEO-friendly keywords)

2. TARGET AUDIENCE (Who would find this content most valuable and why)

3. CONVERSATION STARTERS (3 thought-provoking questions that could spark discussion around this topic)

Here is the article: 
    """

    systemPrompt = f"""
You are an experienced content curator on the Steem blockchain. Your job is to evaluate content objectively, identifying high-quality, 
human written posts that deserve visibility while filtering out low-quality or inappropriate content. When evaluating posts:

- Focus on originality, clarity, relevance, and value to readers.
- High-quality posts demonstrate depth of understanding, offer actionable insights, and are supported by credible evidence or personal experience.
- Look for well-structured content with proper grammar and formatting.
- Prioritize posts that offer unique insights or perspectives, and personal human experience.
- Be vigilant about filtering out AI-generated content, plagiarism, and prohibited topics.
- Look for overly generic phrasing, lack of personal voice, or content that aligns with known AI writing patterns.
- Relevance is determined by the content's alignment with widespread discussions and interests. Value is assessed by the content's ability to educate, surprise, entertain, or inspire readers.
- All content must be written by a human, and reflect a human perspective.
- Content must meet a quality score of 7 out of 10 to be considered for curation. This score is based on the evaluation criteria.
- Follow the evaluation criteria in the curation prompt exactly.

Your assessments should be fair, consistent, and helpful to both content creators and readers. When recommending content,
provide clear reasons for your decision that highlight the post's strengths. Today is {today}.
"""

    postBody = utils.remove_formatting(postBody)

    payload = json.dumps({
    "model": arliaiModel,
    "messages" : [
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
    "max_tokens": 768,
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
