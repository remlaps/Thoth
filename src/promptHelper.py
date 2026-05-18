"""
Helper module for constructing API messages.
"""

def construct_messages(llmUrl, model, systemPrompt, userPrompt):
    """
    Constructs the messages list for the API payload using standard system and user roles.
    """
    return [
        {
            "role": "system",
            "content": systemPrompt
        },
        {
            "role": "user",
            "content": userPrompt
        }
    ]