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

def isTooShort(text):
    minWords=config.getint('CONTENT', 'MIN_WORDS')
    return word_count(text) < minWords

def isEdit(comment):
    if (comment['body'][:2] == '@@'):  ## Edited post (better check needed)
        return True
    
    s=Steem()
    postCreated=datetime.strptime(s.get_content(comment['author'],comment['permlink'])['created'], '%Y-%m-%dT%H:%M:%S')
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

