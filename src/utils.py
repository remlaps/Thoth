import langdetect
import configparser
import re
import authorValidation
import contentValidation

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

def detect_language(text):
    try:
        return langdetect.detect(text)
    except langdetect.lang_detect_exception.LangDetectException:
        return "Unable to detect language"

def screenPost(comment):
    if (comment['body'][:1] == '@@'):  ## Edited post (better check needed)
        return False
    
    tmpBody=remove_formatting(comment['body'])
    if ( contentValidation.isTooShort (tmpBody)):
        return False

    bodyLanguage = detect_language(tmpBody)
    titleLanguage = detect_language(comment['title'])
    if ( bodyLanguage == 'en' and titleLanguage == 'en'):
        language = 'en'
    else:
        language = 'other'
    if ( language != 'en' ):
        return False
    
    if ( authorValidation.isBlacklisted ( comment['author'] )):  # This is checked against muted accounts from REGISTER_ACCOUNT in config.
        return False
    
    return True

def remove_formatting(text):
    # Remove markdown and HTML formatting
    # Regex by AI (Brave Leo --> Llama )
    text = re.sub(r'^#{1,6} (.*)$', r'\1', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)
    text = re.sub(r'\!\[\]\(.*?\)', '', text)
    text = re.sub(r'!\w+\.\w+', '', text)  # Remove image labels
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'<!--.*?-->', '', text)  # Remove HTML comments
    text = re.sub(r'<script>.*?</script>', '', text)  # Remove HTML scripts
    text = re.sub(r'<style>.*?</style>', '', text)  # Remove HTML styles
    return text