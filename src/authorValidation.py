from steem import Steem
import math
import configparser
import datetime

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

### rep_log10 is straight from here - https://developers.steem.io/tutorials-python/account_reputation
def rep_log10(rep):
    """Convert raw steemd rep into a UI-ready value centered at 25."""
    def log10(string):
        leading_digits = int(string[0:4])
        log = math.log10(leading_digits) + 0.00000001
        num = len(string) - 1
        return num + (log - int(log))

    rep = str(rep)
    if rep == "0":
        return 25

    sign = -1 if rep[0] == '-' else 1
    if sign < 0:
        rep = rep[1:]

    out = log10(rep)
    out = max(out - 9, 0) * sign  # @ -9, $1 earned is approx magnitude 1
    out = (out * 9) + 25          # 9 points per magnitude. center at 25
    return round(out, 2)

def isBlacklisted(account):
    steemApi = config.get('STEEM', 'STEEM_API')
    if (steemApi):
        s = Steem(node=steemApi)
    else:
        s = Steem()
    registryAccount = config.get('CONTENT', 'REGISTRY_ACCOUNT')
    
    try:
        hideAccount = s.get_following(registryAccount, account, 'ignore', 1)
        if (len(hideAccount) > 0):
            return True
    except Exception as e:
        print(f"Error checking blacklist status for {account}: {e}")
        return False
    
    return False

def isAuthorScreened(comment):
    if ( isBlacklisted(comment['author']) ):
        return True

    if isFollowerCountTooLow(comment['author']):
        return True
    
    steemApi = config.get('STEEM', 'STEEM_API')
    if ( steemApi ):
        s=Steem(node=steemApi)
    else:
        s=Steem()
    accountInfo = s.get_account(comment['author'])

    if isRepTooLow(accountInfo['reputation']) :
        return True
    
    if isMonthlyFollowersTooLow(accountInfo, comment):
        return True
    
    return False

def isRepTooLow(reputation):
    return rep_log10(reputation) < config.getint('AUTHOR','MIN_REPUTATION')

def isFollowerCountTooLow(commentAuthor):
    s=Steem()
    followerCount = s.get_follow_count(commentAuthor)['follower_count']
    return followerCount < config.getint('AUTHOR','MIN_FOLLOWERS')

# If you used "import datetime"
def followersPerMonth(accountInfo, comment):
    s = Steem()
    followerCount = s.get_follow_count(comment['author'])['follower_count']
    accountCreated = datetime.datetime.strptime(accountInfo['created'], '%Y-%m-%dT%H:%M:%S')
    now = datetime.datetime.now()
    if accountCreated > now:
        raise ValueError("Account creation date is in the future")
    age = now - accountCreated
    return followerCount / (age.days / 30.0)

def isMonthlyFollowersTooLow (accountInfo, comment):
    return followersPerMonth(accountInfo, comment) < config.getint('AUTHOR','MIN_FOLLOWERS_PER_MONTH')

