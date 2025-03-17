from steem import Steem
import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

def isBlacklisted ( account ):
    s=Steem()
    registryAccount = config.get('CONTENT', 'REGISTRY_ACCOUNT')
    hideAccount=s.get_following(registryAccount, account, 'ignore', 1)
    if ( len(hideAccount) > 0 ):
        return True
    return False
    