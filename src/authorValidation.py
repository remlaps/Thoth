from steem import Steem
import math
import configparser
from datetime import datetime

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
    
    if isInactive(accountInfo) :
        return True

    if ( getMedianFollowerRep ( comment['author'] ) < config.getint( 'AUTHOR', 'MIN_FOLLOWER_MEDIAN_REP' )):
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
    accountCreated = datetime.strptime(accountInfo['created'], '%Y-%m-%dT%H:%M:%S')
    now = datetime.now()
    if accountCreated > now:
        raise ValueError("Account creation date is in the future")
    age = now - accountCreated
    return followerCount / (age.days / 30.0)

def isMonthlyFollowersTooLow (accountInfo, comment):
    return followersPerMonth(accountInfo, comment) < config.getint('AUTHOR','MIN_FOLLOWERS_PER_MONTH')

def isInactive ( accountInfo ):
    return inactiveDays(accountInfo['name']) > config.getint('AUTHOR','MAX_INACTIVITY_DAYS')

def inactiveDays ( accountName ):
    s=Steem()
    lastPost = s.get_account(accountName)['last_post']
    lastVote = s.get_account(accountName)['last_vote_time']

    lastPostTime = datetime.strptime(lastPost, '%Y-%m-%dT%H:%M:%S')
    lastVoteTime = datetime.strptime(lastVote, '%Y-%m-%dT%H:%M:%S')
    mostRecentActivity = max(lastPostTime, lastVoteTime)
    today = datetime.now()
    inactiveDays = (today - mostRecentActivity).days

    return inactiveDays

def getAllFollowers(account, account_type='blog'):
   """
   Retrieve all followers for a specific account.
   
   Args:
       account (str): The account name to get followers for
       account_type (str): The type of account (default: 'blog')
       
   Returns:
       list: A list of all follower data
   """
   s=Steem()
   all_followers = []
   batch_size = 1000
   last_account = ''
   
   while True:
       # Get the next batch of followers
       followers_batch = s.get_followers(account, last_account, account_type, batch_size)
       
       # If we got no results or just the last one repeated, we're done
       if not followers_batch or (len(followers_batch) < 1001 and followers_batch[0]['follower'] == last_account):
           break
           
       # Add the followers to our result list (skip the first one if it's the last from previous batch)
       if last_account and followers_batch[0]['follower'] == last_account:
           all_followers.extend(followers_batch[1:])
       else:
           all_followers.extend(followers_batch)
           
       # Update the last account for the next query
       last_account = followers_batch[-1]['follower']
       
       # If we got fewer than the batch size, we've reached the end
       if len(followers_batch) < batch_size:
           break
   
   return all_followers

def getMedianFollowerRep(author):
   """
   Calculate the median reputation from a list of follower data.
   
   Args:
       followers_data (list): List of follower data dictionaries
       
   Returns:
       float: The median reputation value
   """
   followersData = getAllFollowers(author)
   
   # Extract reputation values from the data
   reputations = [follower['reputation'] for follower in followersData]
   
   # Sort the reputations
   reputations.sort()
   
   # Find the middle value
   n = len(reputations)
   if n == 0:
       return None  # Return None for empty lists
   
   # If odd number of elements, return the middle one
   if n % 2 == 1:
       return reputations[n // 2]
   # If even number of elements, return the average of the two middle values
   else:
       middle1 = reputations[(n // 2) - 1]
       middle2 = reputations[n // 2]
       return (middle1 + middle2) / 2