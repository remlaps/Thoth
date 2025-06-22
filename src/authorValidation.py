from steem import Steem
import math
import configparser
from datetime import datetime
import requests
import json

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

def isBlacklisted(account, steem_instance=None):
    steemApi = config.get('STEEM', 'STEEM_API')
    # Use provided Steem instance or create a new one
    s = steem_instance or Steem(node=steemApi if steemApi else None)
    registryAccount = config.get('CONTENT', 'REGISTRY_ACCOUNT')
    
    try:
        hideAccount = s.get_following(registryAccount, account, 'ignore', 1)
        if (len(hideAccount) > 0):
            return True
    except Exception as e:
        print(f"Error checking blacklist status for {account}: {e}")
        return False
    
    return False

def isAuthorWhitelisted(account):
    whiteListFile = config.get('CONTENT', 'AUTHOR_WHITELIST_FILE')
    try:
        with open(whiteListFile, 'r') as wlf:
            # Read lines, strip whitespace from each, and filter out empty lines
            whiteList = {line.strip() for line in wlf if line.strip()}
    except FileNotFoundError:
        # Handle the case where the whitelist file doesn't exist
        # You might want to log this or return False by default
        print(f"Warning: Whitelist file '{whiteListFile}' not found.")
        return False
    
    return account in whiteList

def isAuthorScreened(comment):
    steemApi = config.get('STEEM', 'STEEM_API')
    # Create a single Steem instance to be reused by all validation functions
    s = Steem(node=steemApi if steemApi else None)

    if ( isBlacklisted(comment['author'], steem_instance=s) ):
        return True
    
    if ( isAuthorWhitelisted(comment['author']) ):
        return False
    
    if isHiveActivityTooRecent(comment['author']):
        return True

    if isFollowerCountTooLow(comment['author'], steem_instance=s):
        return True
       
    accountInfo = s.get_account(comment['author'])
     
    if isInactive(accountInfo, steem_instance=s) :
        return True
        
    if isRepTooLow(accountInfo['reputation']) :
        return True
    
    if isMonthlyFollowersTooLow(accountInfo, comment, steem_instance=s):
        return True
    
    if isAdjustedMonthlyFollowersTooLow ( accountInfo, comment, steem_instance=s):
        return True

    median_rep = getMedianFollowerRep(comment['author'], steem_instance=s)
    if median_rep is not None and median_rep < config.getint('AUTHOR', 'MIN_FOLLOWER_MEDIAN_REP'):
        return True
        
    return False

def isRepTooLow(reputation):
    return rep_log10(reputation) < config.getint('AUTHOR','MIN_REPUTATION')

def isFollowerCountTooLow(commentAuthor, steem_instance=None):
    s = steem_instance or Steem()
    followerCount = s.get_follow_count(commentAuthor)['follower_count']
    return followerCount < config.getint('AUTHOR','MIN_FOLLOWERS')

def followersPerMonth(accountInfo, comment, steem_instance=None):
    s = steem_instance or Steem()
    followerCount = s.get_follow_count(comment['author'])['follower_count']
    accountCreated = datetime.strptime(accountInfo['created'], '%Y-%m-%dT%H:%M:%S')
    now = datetime.now()
    if accountCreated > now:
        raise ValueError("Account creation date is in the future")
    age = now - accountCreated
    return 30.44 * followerCount / age.days

import math

def adjustedFollowersPerMonth(accountInfo, comment, halfLife=365.25 * 1, steem_instance=None):
    s = steem_instance or Steem()
    followerCount = s.get_follow_count(comment['author'])['follower_count']
    accountCreated = datetime.strptime(accountInfo['created'], '%Y-%m-%dT%H:%M:%S')
    now = datetime.now()
    if accountCreated > now:
        raise ValueError("Account creation date is in the future")
    age = now - accountCreated

    ## halflife formula - https://www.calculator.net/half-life-calculator.html
    adjustedHalfLife = max ( age.days - halfLife, 1 )  ## Give them one halving cycle for free
    adjustedFollowerCount = followerCount * (0.5 ** (age.days / adjustedHalfLife))  
    adjustedFollowersPerMonth = 30.44 * adjustedFollowerCount / age.days
    
    return adjustedFollowersPerMonth

def isMonthlyFollowersTooLow (accountInfo, comment, steem_instance=None):
    return followersPerMonth(accountInfo, comment, steem_instance=steem_instance) < config.getint('AUTHOR','MIN_FOLLOWERS_PER_MONTH')

def isAdjustedMonthlyFollowersTooLow (accountInfo, comment, steem_instance=None):
    halfLife = config.getint('AUTHOR','FOLLOWER_HALFLIFE_YEARS')
    if ( halfLife ):
        return \
            adjustedFollowersPerMonth(accountInfo, comment, halfLife * 365.25, steem_instance=steem_instance) < \
                config.getint('AUTHOR','MIN_ADJUSTED_FOLLOWERS_PER_MONTH')
    else:
        return \
            adjustedFollowersPerMonth(accountInfo, comment, steem_instance=steem_instance) < \
                config.getint('AUTHOR','MIN_ADJUSTED_FOLLOWERS_PER_MONTH')

def isActiveFollowerCountTooLow(accountName, steem_instance=None):
    """
    Checks if an account has too few recently active followers.
    This function is optimized to terminate as soon as the threshold is met.

    Args:
        accountName (str): The account name whose followers are to be checked.
        steem_instance (Steem, optional): An existing Steem instance to reuse. Defaults to None.

    Returns:
        bool: True if the active follower count is too low or an error occurs.
              False if the account has enough active followers.
    """
    try:
        max_inactivity_days = config.getint('AUTHOR', 'MAX_FOLLOWER_INACTIVITY_DAYS')
        min_followers_needed = config.getint('AUTHOR', 'MIN_ACTIVE_FOLLOWERS')
        
        s = steem_instance or Steem()
        followers_data = getAllFollowers(accountName, steem_instance=s)
        active_followers_found = 0

        for follower_entry in followers_data:
            print(f"Checking activity time for {accountName} -> {follower_entry}: {active_followers_found}/{min_followers_needed}")
            follower_account_name = follower_entry['follower']
            try:
                days_inactive = inactiveDays(follower_account_name, steem_instance=s)
                if days_inactive is not None and days_inactive <= max_inactivity_days:
                    active_followers_found += 1
                    if active_followers_found >= min_followers_needed:
                        # Success: enough active followers found. Count is NOT too low.
                        print(f"DEBUG: isActiveFollowerCountTooLow({accountName}) -> has_enough_active_followers: True. Result (is_too_low): False")
                        return False
            except Exception as e:
                # This handles errors for a single follower (e.g., account deleted)
                # We just log it and continue checking other followers.
                print(f"Warning: Could not determine inactivity for follower {follower_account_name}: {e}")
        
        # If the loop completes without reaching the threshold, the count is too low.
        has_enough = active_followers_found >= min_followers_needed
        is_too_low = not has_enough
        print(f"DEBUG: isActiveFollowerCountTooLow({accountName}) -> has_enough_active_followers: {has_enough}. Result (is_too_low): {is_too_low}")
        return is_too_low

    except Exception as e:
        # This catches errors from config.getint, getAllFollowers, etc.
        print(f"Error during active follower check for {accountName}: {e}")
        print(f"DEBUG: isActiveFollowerCountTooLow({accountName}) -> Exception occurred. Returning True.")
        return True # Fail safe: if we can't check, screen the author (i.e., count is "too low").

def isInactive(accountInfo, steem_instance=None):
    return inactiveDays(accountInfo['name'], steem_instance=steem_instance) > config.getint('AUTHOR','MAX_INACTIVITY_DAYS')

def inactiveDays(accountName, steem_instance=None):
    s = steem_instance or Steem()
    account_data = s.get_account(accountName)
    lastPost = account_data['last_post']
    lastVote = account_data['last_vote_time']

    lastPostTime = datetime.strptime(lastPost, '%Y-%m-%dT%H:%M:%S')
    lastVoteTime = datetime.strptime(lastVote, '%Y-%m-%dT%H:%M:%S')
    mostRecentActivity = max(lastPostTime, lastVoteTime)
    today = datetime.now()
    inactiveDays = (today - mostRecentActivity).days

    return inactiveDays

def getAllFollowers(account, account_type='blog', steem_instance=None):
   """
   Retrieve all followers for a specific account.
   
   Args:
       account (str): The account name to get followers for
       account_type (str): The type of account (default: 'blog')
       
   Returns:
       list: A list of all follower data
   """
   s = steem_instance or Steem()
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

def getMedianFollowerRep(author, steem_instance=None):
   """
   Calculate the median reputation from a list of follower data.
   
   Args:
       followers_data (list): List of follower data dictionaries
       
   Returns:
       float: The median reputation value
   """
   followersData = getAllFollowers(author, steem_instance=steem_instance)
   
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

def isHiveActivityTooRecent(account):
    hiveInactivity = hiveInactiveDays(account)
    if ( hiveInactivity != None ):
        if ( hiveInactivity < config.getint('AUTHOR','LAST_HIVE_ACTIVITY_AGE') ):
            return True
    return False

def hiveInactiveDays(account):
    """
    Calculate the number of days since the last activity for a Hive account.
    
    Args:
        account (str): The Hive account name to query
        
    Returns:
        int: Number of days since last activity, or None if the activity date couldn't be retrieved
    """
    lastHiveActivity = getLastHiveActivityDate(account)
    
    if not lastHiveActivity:
        return None
    
    # Convert string date to datetime object
    lastHiveActivityDt = datetime.strptime(lastHiveActivity, "%Y-%m-%d %H:%M:%S")
    
    # Get current datetime
    now = datetime.now()
    
    # Calculate the difference in days
    daysPassed = (now - lastHiveActivityDt).days
    
    return daysPassed

import requests
import json
from datetime import datetime

def getLastHiveActivityDate(account):
    """
    Query the Hive API for an account and return the last activity date.
    
    Args:
        account (str): The Hive account name to query
        
    Returns:
        str: The last activity date as a formatted date string, or None if the API call fails
    """
    url = "https://api.hive.blog"
    payload = {
        "jsonrpc": "2.0", 
        "method": "condenser_api.get_accounts", 
        "params": [[account]], 
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        data = response.json()
        
        # Check if we got a valid response with results
        if "result" in data and data["result"] and len(data["result"]) > 0:
            account_data = data["result"][0]
            
            # Extract the last_post and last_vote_time fields
            lastHivePostTime = account_data.get("last_post")
            lastHiveVoteTime = account_data.get("last_vote_time")
            
            # Convert string dates to datetime objects
            lastHivePostTime = datetime.fromisoformat(lastHivePostTime.replace("Z", "+00:00")) if lastHivePostTime else None
            lastHiveVoteTime = datetime.fromisoformat(lastHiveVoteTime.replace("Z", "+00:00")) if lastHiveVoteTime else None
            
            # Find the most recent date
            if lastHivePostTime and lastHiveVoteTime:
                lastHiveActivityTime = max(lastHivePostTime, lastHiveVoteTime)
            elif lastHivePostTime:
                lastHiveActivityTime = lastHivePostTime
            elif lastHiveVoteTime:
                lastHiveActivityTime = lastHiveVoteTime
            else:
                return None
                
            return lastHiveActivityTime.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error querying API: {e}")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error processing response: {e}")
        return None