"""
Helper module for constructing API messages.
"""

def construct_messages(arliaiUrl, model, systemPrompt, userPrompt):
    """
    Constructs the messages list for the API payload.
    Merges system and user prompts if using Google API (OpenAI compatibility) with Gemma models.
    """
    # Check for Google API (OpenAI compatibility endpoint) and Gemma model
    target_url_prefix = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    
    is_google_openai = arliaiUrl.startswith(target_url_prefix)
    is_gemma = "gemma" in model.lower()
    
    if is_google_openai and is_gemma:
        new_content = (
            f"**SYSTEM INSTRUCTIONS:**\n{systemPrompt}\n\n"
            f"**USER REQUEST:**\n{userPrompt}"
        )
        return [
            {
                "role": "user",
                "content": new_content
            }
        ]
    
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