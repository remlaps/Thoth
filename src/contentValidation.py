import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

def word_count(text):
    return len(text.split())

def isTooShort(text):
    minWords=config.getint('CONTENT', 'MIN_WORDS')
    return word_count(text) < minWords