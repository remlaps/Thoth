import sys
import os

# --- Set up paths to run from the 'tools' directory ---
# Get the absolute path of the project's root directory (one level up from 'tools')
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Change the current working directory to the project root.
# This ensures that all relative paths in other modules (like 'config/config.ini')
# are resolved correctly from the project root.
os.chdir(project_root)

# Add the 'src' directory to the Python path to allow importing modules from it.
# Now that CWD is the project root, a relative path is fine.
sys.path.append('src')

# Now we can import our modules
import configparser
from datetime import datetime
from steem import Steem

import authorValidation
import walletValidation
import utils

def main():
    """
    Runs a series of validation checks against a specified Steem author.
    """
    # --- Configuration and Setup ---
    config = configparser.ConfigParser()
    # Since CWD is now the project root, this relative path is correct.
    config_path = os.path.join('config', 'config.ini')
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at '{config_path}'")
        print("Please copy 'config/config.template' to 'config/config.ini' and fill it out.")
        sys.exit(1)
    config.read(config_path)

    if len(sys.argv) < 2:
        print("Usage: python checkValidation.py <author_name>")
        sys.exit(1)

    author_name = sys.argv[1].replace('@', '') # Remove @ if present

    print(f"--- Running Validation Checks for @{author_name} ---")

    # --- Steem and Account Info Setup ---
    try:
        steem_api = config.get('STEEM', 'STEEM_API', fallback=None)
        s = Steem(node=steem_api) if steem_api else Steem()
        account_info = s.get_account(author_name)
        if not account_info:
            print(f"Error: Could not find Steem account for '{author_name}'")
            sys.exit(1)
        # Create a dummy comment object required by some validation functions
        comment = {'author': author_name, 'timestamp': datetime.utcnow()} 
    except Exception as e:
        print(f"Error connecting to Steem or getting account info: {e}")
        sys.exit(1)

    # --- Run Individual Validation Checks ---
    
    # Whitelist/Blacklist checks
    print("\n--- General Screening ---")
    is_whitelisted = authorValidation.isAuthorWhitelisted(author_name)
    print(f"Is Whitelisted: {is_whitelisted}")
    
    is_blacklisted = authorValidation.isBlacklisted(author_name, steem_instance=s)
    print(f"Is Blacklisted: {is_blacklisted}")

    # If whitelisted, other checks are skipped by the main logic.
    if is_whitelisted:
        print("\nNOTE: Author is whitelisted. The main screening process would stop here and accept the post.")
        print("Continuing with other checks for informational purposes only.")
    
    # Author checks from authorValidation.py
    print("\n--- Author Validation ---")
    
    # Reputation
    min_rep = config.getint('AUTHOR', 'MIN_REPUTATION')
    author_rep = authorValidation.rep_log10(account_info['reputation'])
    rep_too_low = authorValidation.isRepTooLow(account_info['reputation'])
    print(f"Reputation: {author_rep:.2f} (Min: {min_rep}, Is Too Low: {rep_too_low})")

    # Inactivity
    max_inactive_days = config.getint('AUTHOR', 'MAX_INACTIVITY_DAYS')
    days_inactive = authorValidation.inactiveDays(author_name, steem_instance=s)
    is_inactive = authorValidation.isInactive(account_info, steem_instance=s)
    print(f"Days Inactive: {days_inactive} (Max: {max_inactive_days}, Is Inactive: {is_inactive})")

    # Hive Activity
    last_hive_age = config.getint('AUTHOR', 'LAST_HIVE_ACTIVITY_AGE')
    hive_too_recent = authorValidation.isHiveActivityTooRecent(author_name)
    print(f"Hive Activity Too Recent (less than {last_hive_age} days ago): {hive_too_recent}")

    # Follower counts
    min_followers = config.getint('AUTHOR', 'MIN_FOLLOWERS')
    follower_count = s.get_follow_count(author_name)['follower_count']
    followers_too_low = authorValidation.isFollowerCountTooLow(author_name, steem_instance=s)
    print(f"Follower Count: {follower_count} (Min: {min_followers}, Is Too Low: {followers_too_low})")

    # Monthly followers
    min_monthly_followers = config.getint('AUTHOR', 'MIN_FOLLOWERS_PER_MONTH')
    monthly_followers = authorValidation.followersPerMonth(account_info, comment, steem_instance=s)
    monthly_too_low = authorValidation.isMonthlyFollowersTooLow(account_info, comment, steem_instance=s)
    print(f"Followers/Month: {monthly_followers:.2f} (Min: {min_monthly_followers}, Is Too Low: {monthly_too_low})")

    # Adjusted monthly followers
    min_adj_monthly_followers = config.getint('AUTHOR', 'MIN_ADJUSTED_FOLLOWERS_PER_MONTH')
    half_life_years = config.getfloat('AUTHOR', 'FOLLOWER_HALFLIFE_YEARS')
    adj_monthly_followers = authorValidation.adjustedFollowersPerMonth(account_info, comment, halfLife=half_life_years * 365.25, steem_instance=s)
    adj_monthly_too_low = authorValidation.isAdjustedMonthlyFollowersTooLow(account_info, comment, steem_instance=s)
    print(f"Adjusted Followers/Month (Half-life: {half_life_years} yrs): {adj_monthly_followers:.2f} (Min: {min_adj_monthly_followers}, Is Too Low: {adj_monthly_too_low})")

    # Active followers
    min_active_followers = config.getint('AUTHOR', 'MIN_ACTIVE_FOLLOWERS')
    print(f"Checking for at least {min_active_followers} active followers... (this may take a while)")
    active_followers_too_low = authorValidation.isActiveFollowerCountTooLow(author_name, steem_instance=s)
    print(f"Active Follower Count Too Low: {active_followers_too_low}")

    # Median follower rep
    min_median_rep = config.getint('AUTHOR', 'MIN_FOLLOWER_MEDIAN_REP')
    print(f"Calculating median follower reputation... (this may take a while)")
    median_rep = authorValidation.getMedianFollowerRep(author_name, steem_instance=s)
    if median_rep is not None:
        median_rep_too_low = median_rep < min_median_rep
        if median_rep_too_low:
            print(f"DEBUG: isAuthorScreened({comment['author']}) -> median follower rep {median_rep} < MIN_FOLLOWER_MEDIAN_REP {config.getint('AUTHOR', 'MIN_FOLLOWER_MEDIAN_REP')}: True")
            print(f"Median Follower Rep: {median_rep:.2f} (Min: {min_median_rep}, Is Too Low: {median_rep_too_low})")
        else:
            print(f"Median Follower Rep: {median_rep:.2f} (Min: {min_median_rep}, Is Too Low: {median_rep_too_low})")
    else:
        print(f"Median Follower Rep: Could not calculate for {author_name}.  (no followers).")
    # if median_rep_raw is not None:
    #     median_rep_ui = authorValidation.rep_log10(median_rep_raw)
    #     median_rep_too_low = median_rep_ui < min_median_rep.real
    #     print(f"Median Follower Rep: {median_rep_ui:.2f} (Min: {min_median_rep}, Is Too Low: {median_rep_too_low})")
    # else:
    #     print("Median Follower Rep: Could not calculate (no followers).")

    # Wallet checks from walletValidation.py
    print("\n--- Wallet Validation ---")
    wallet_passes = walletValidation.check_author_wallet(author_name)
    print(f"Passes Basic Wallet Screen (delegation % & undelegated SP): {wallet_passes}")

    wallet_screened = walletValidation.walletScreened(author_name)
    print(f"Is Screened by Voting Service Delegation: {wallet_screened}")

    # Overall screening result from utils.screenPost (which calls authorValidation and walletValidation)
    print("\n--- Overall Result from utils.screenPost ---")
    # We need a more complete comment object for screenPost
    # Let's get a recent post from the author to test with
    try:
        posts = s.get_discussions_by_author_before_date(author_name, None, datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'), 1)
        if posts:
            full_comment_object = posts[0]
            print(f"Using post '{full_comment_object['title']}' for full screening test.")
            # The timestamp in the object from get_discussions_by_author_before_date is a string
            # but isEdit expects a datetime object. Let's fix that.
            full_comment_object['timestamp'] = datetime.strptime(full_comment_object['created'], '%Y-%m-%dT%H:%M:%S')
            
            screen_result = utils.screenPost(full_comment_object)
            print(f"utils.screenPost result: '{screen_result}'")
        else:
            print("Could not retrieve a recent post for the author to run a full screenPost test.")
            print("Running author-only screening via isAuthorScreened...")
            if authorValidation.isAuthorScreened(comment):
                 print("isAuthorScreened result: Screened (FAIL)")
            else:
                 print("isAuthorScreened result: Not Screened (PASS)")

    except Exception as e:
        print(f"Error during full screenPost test: {e}")

if __name__ == "__main__":
    main()