import configparser
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