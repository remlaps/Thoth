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
    if ( contentValidation.isEdit (comment)):
        return True
    
    if ( contentValidation.hasBlacklistedTag(comment)):
        return True
    
    if ( not contentValidation.hasRequiredTag(comment)):
        return True
    
    tmpBody=remove_formatting(comment['body'])
    if ( contentValidation.isTooShort (tmpBody)):
        return True

    targetLanguage = [lang.strip() for lang in config.get('CONTENT', 'LANGUAGE').split(',') if lang]
    bodyLanguage = detect_language(tmpBody)
    titleLanguage = detect_language(comment['title'])
    if not ( bodyLanguage in targetLanguage and titleLanguage in targetLanguage ):
        return True
    
    if ( authorValidation.isAuthorScreened(comment)):
        return True
    
    return False

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