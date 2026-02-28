import configparser
import json
from steem import Steem
from datetime import datetime

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

def word_count(text):
    return len(text.split())

def isTooShort(text_or_count):
    minWords=config.getint('CONTENT', 'MIN_WORDS')
    count = text_or_count if isinstance(text_or_count, int) else word_count(text_or_count)
    return count < minWords

def isTooShortHard(text_or_count):
    minWords=config.getint('CONTENT', 'MIN_WORDS_HARD', fallback=0)
    if minWords == 0:
        return False
    count = text_or_count if isinstance(text_or_count, int) else word_count(text_or_count)
    return count < minWords

def isEdit(comment, steem_instance=None, latest_content=None):
    if (comment['body'][:2] == '@@'):  ## Edited post (better check needed)
        return True
    
    if latest_content:
        content = latest_content
    else:
        s = steem_instance or Steem()
        content = s.get_content(comment['author'], comment['permlink'])
        
    postCreated = datetime.strptime(content['created'], '%Y-%m-%dT%H:%M:%S')
    if ( postCreated != comment['timestamp'] ):
        return True
    
    return False

def hasBlacklistedTag(comment):
    excludedTags=getTagBlacklist()
    if comment.get('json_metadata', None):
        metadataString=comment['json_metadata']
        metadataJson=json.loads(metadataString)
        if ( metadataJson.get('tags', None) != None):
            tags=metadataJson['tags']
            for tag in tags:
                if tag in excludedTags:
                    return True

    if comment.get('category', None) in excludedTags:
        return True

    return False
    
def getTagBlacklist():
    tags = config.get('CONTENT', 'EXCLUDE_TAGS')
    return [tag.strip() for tag in tags.split(',')]


def count_hashtag_words(comment):
    """
    Counts the number of words in a string that begin with a '#' (hash/pound) sign.

    Args:
        text (str): The input string to analyze.

    Returns:
        int: The number of words starting with '#'.
    """
    
    post_metadata = json.loads(comment['json_metadata'])
    tags = post_metadata['tags']

    hashtag_count = len(tags) if isinstance(tags, list) else 0
            
    return hashtag_count

def hasTooManyTags ( comment ):
    maxTags = config.getint('CONTENT', 'MAX_TAG_COUNT')
    return count_hashtag_words(comment) > maxTags

def hasRequiredTag(comment):
    requiredTags=getIncludeTagList()
    if ( not requiredTags ):
        return True
    
    if comment.get('json_metadata', None):
        metadataString=comment['json_metadata']
        metadataJson=json.loads(metadataString)
        if ( metadataJson.get('tags', None) != None):
            tags=metadataJson['tags']
            for tag in tags:
                if tag in requiredTags:
                    return True

    if comment.get('category', None) in requiredTags:
        return True

    return False

def getIncludeTagList():
    tagsString = config.get('CONTENT', 'INCLUDE_TAGS', fallback='')
    tagsList = [tag.strip() for tag in tagsString.split(',') if tag.strip()] # Filters out empty strings
    return tagsList

def getTags(comment):
    """
    Extracts tags from a Steem comment, ensuring no duplicates.

    Args:
        comment (dict): The Steem comment data.

    Returns:
        list: A list of unique tags.
    """
    tags = set()  # Use a set to automatically handle duplicates

    if comment.get('json_metadata', None):
        metadata_string = comment['json_metadata']
        try:
            metadata_json = json.loads(metadata_string)
            if metadata_json.get('tags', None) is not None:
                tags.update(metadata_json['tags'])  # Add tags to the set
        except json.JSONDecodeError:
            print(f"Error decoding JSON metadata: {metadata_string}")

    if comment.get('category', None):
        tags.add(comment['category'])  # Add category to the set

    return sorted(list(tags))  # Convert the set to a sorted list for the return value
