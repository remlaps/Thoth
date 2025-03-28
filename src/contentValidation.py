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