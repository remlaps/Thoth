import langdetect
import configparser
import re
import authorValidation
import contentValidation

from steem import Steem


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
        return "Post edit"
    
    if ( contentValidation.hasBlacklistedTag(comment)):
        return "Blacklisted tag in original version"
    
    latestComment=Steem().get_content(comment['author'],comment['permlink'])

    if ( contentValidation.hasBlacklistedTag(latestComment)):
        return "Blacklisted tag in latest revision."
    
    if ( not contentValidation.hasRequiredTag(latestComment)):
        return "Required tag missing"
    
    tmpBody=remove_formatting(latestComment['body'])
    if ( contentValidation.isTooShort (tmpBody)):
        return "Too short"

    if ( authorValidation.isAuthorScreened(comment)):
        return "Author screening"
    
    targetLanguage = [lang.strip() for lang in config.get('CONTENT', 'LANGUAGE').split(',') if lang]
    bodyLanguage = detect_language(tmpBody)
    titleLanguage = detect_language(latestComment['title'])
    if not ( bodyLanguage in targetLanguage and titleLanguage in targetLanguage ):
        return "Not a target language"
    
    return "Accept"

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