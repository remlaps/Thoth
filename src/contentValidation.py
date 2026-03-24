import configparser
import json
from steem import Steem
from datetime import datetime
import re
import requests
import time
import logging

# Create a ConfigParser object
config = configparser.ConfigParser()

logger = logging.getLogger(__name__)

# Read the config.ini file
config.read('config/config.ini')

def word_count(text):
    # Find all sequences of alphanumeric characters.
    # Prevents markdown tables, dividers, and URLs from inflating the count.
    words = re.findall(r'\b\w+\b', text)
    return len(words)

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
    try:
        if comment.get('json_metadata', None):
            metadataString=comment['json_metadata']
            metadataJson=json.loads(metadataString)
            if isinstance(metadataJson, dict) and metadataJson.get('tags', None) is not None:
                tags=metadataJson['tags']
                for tag in tags:
                    if tag in excludedTags:
                        return True

        if comment.get('category', None) in excludedTags:
            return True

        return False
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error parsing metadata for {comment.get('author', 'unknown')}/{comment.get('permlink', 'unknown')}: {e}")
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
    
    try:
        if comment.get('json_metadata', None):
            metadataString=comment['json_metadata']
            metadataJson=json.loads(metadataString)
            if isinstance(metadataJson, dict) and metadataJson.get('tags', None) is not None:
                tags=metadataJson['tags']
                for tag in tags:
                    if tag in requiredTags:
                        return True

        if comment.get('category', None) in requiredTags:
            return True

        return False
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error parsing metadata for {comment.get('author', 'unknown')}/{comment.get('permlink', 'unknown')}: {e}")
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

    try:
        if comment.get('json_metadata', None):
            metadata_string = comment['json_metadata']
            try:
                metadata_json = json.loads(metadata_string)
                if isinstance(metadata_json, dict) and metadata_json.get('tags', None) is not None:
                    tags.update(metadata_json['tags'])  # Add tags to the set
            except json.JSONDecodeError:
                print(f"Error decoding JSON metadata: {metadata_string}")

        if comment.get('category', None):
            tags.add(comment['category'])  # Add category to the set

        return sorted(list(tags))  # Convert the set to a sorted list for the return value
    except Exception as e:
        print(f"Error extracting tags for {comment.get('author', 'unknown')}/{comment.get('permlink', 'unknown')}: {e}")
        return []

# Global cache for the DMCA list
_dmca_cache = set()
_dmca_fetched = False

def get_dmca_list():
    global _dmca_cache, _dmca_fetched

    # Use cached list if it has already been fetched this run
    if _dmca_fetched:
        return _dmca_cache

    # Fetch the raw JS file from Steemit Condenser
    url = "https://raw.githubusercontent.com/steemit/condenser/master/src/app/utils/DMCAList.js"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse all @author/permlink patterns. This handles both full URLs and raw paths.
        matches = re.findall(r'@([a-z0-9\-\.]+/[a-z0-9\-]+)', response.text)
        _dmca_cache = set(matches)
        logger.info(f"Successfully fetched and cached {len(_dmca_cache)} DMCA entries.")
    except Exception as e:
        logger.error(f"Failed to fetch DMCA list from GitHub: {e}")
        
    _dmca_fetched = True
            
    return _dmca_cache

def is_dmca(comment):
    author = comment.get('author')
    permlink = comment.get('permlink')
    if not author or not permlink:
        return False
        
    dmca_list = get_dmca_list()
    post_id = f"{author}/{permlink}"
    
    return post_id in dmca_list
