#!/usr/bin/env python3
"""
Diagnostic tool to check if Thoth would accept/reject a specific author or post.
Rewritten to use the modern Hybrid Screening and Scoring system.
"""
import sys
import os
import logging
import argparse
from datetime import datetime, timezone

# --- Path Configuration ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(project_root)
sys.path.append('src')

# Import project modules
from configValidator import ConfigValidator
from hybridScreening import HybridScreening
from authorValidation import isBlacklisted, isAuthorWhitelisted, isHiveActivityTooRecent, isBlurtActivityTooRecent, inactiveDays, isRepTooLow, rep_log10
from walletValidation import walletScreened
from steemHelpers import initialize_steem_with_retry

# Configure logging to be informative but clean
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Suppress noisy library logs
logging.getLogger('steem.http_client').setLevel(logging.CRITICAL)
logging.getLogger('steem.steemd').setLevel(logging.CRITICAL)
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)

def main():
    parser = argparse.ArgumentParser(description="Check if Thoth would curate a specific author or post.")
    parser.add_argument("target", help="Target to check: '@author' or '@author/permlink'")
    args = parser.parse_args()

    target = args.target.replace('@', '').strip()
    author = ""
    permlink = ""

    if '/' in target:
        author, permlink = target.split('/', 1)
    else:
        author = target

    # 1. Load and Validate Configuration
    validator = ConfigValidator()

    # Diagnostic tools don't need private keys or API keys to evaluate rules/scores.
    # Inject dummy environment variables to satisfy strict config validation.
    os.environ.setdefault('UNLOCK', 'diagnostic_dummy_value')
    os.environ.setdefault('LLMAPIKEY', 'diagnostic_dummy_value')

    if not validator.validate_config():
        print("\n[!] FATAL: Configuration validation failed:")
        for error in validator.get_errors():
            print(f"  - {error}")
        sys.exit(1)

    # 2. Initialize Steem connection
    steem_api = validator.config.get('STEEM', 'STEEM_API', fallback=None)
    print(f"Connecting to Steem node: {steem_api if steem_api else 'Default'}...")
    s = initialize_steem_with_retry(node_api=steem_api)
    if not s:
        print("\n[!] FATAL: Could not connect to Steem blockchain.")
        sys.exit(1)

    # 3. Retrieve Post Content
    try:
        if not permlink:
            print(f"Fetching latest post for @{author}...")
            # Fetch most recent post to perform a full check (including engagement/content rules)
            posts = s.get_discussions_by_author_before_date(author, None, datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'), 1)
            if not posts:
                print(f"Error: No posts found for user @{author}.")
                sys.exit(1)
            post = posts[0]
            permlink = post['permlink']
        else:
            print(f"Fetching post @{author}/{permlink}...")
            post = s.get_content(author, permlink)
            if not post or not post.get('author'):
                print(f"Error: Could not find post @{author}/{permlink}.")
                sys.exit(1)

        # Construct simulated stream data (required for hybrid screening)
        post_data = {
            'author': post['author'],
            'permlink': post['permlink'],
            'timestamp': datetime.strptime(post['created'], '%Y-%m-%dT%H:%M:%S'),
            'title': post['title'],
            'body': post['body'],
            'net_votes': post.get('net_votes', 0),
            'children': post.get('children', 0),
            'pending_payout_value': post.get('pending_payout_value', '0.000 SBD'),
            'total_payout_value': post.get('total_payout_value', '0.000 SBD')
        }

    except Exception as e:
        print(f"\n[!] Error retrieving blockchain data: {e}")
        sys.exit(1)

    # 4. Initialize the modern Hybrid Screening system
    print("Initializing Hybrid Screening engine...")
    hybrid_screening = HybridScreening(s, validator)
    
    print(f"\n{'='*60}")
    print(f" THOTH DIAGNOSTIC REPORT: @{author}/{permlink}".center(60))
    print(f"{'='*60}\n")
    
    # 5. Execute Screening (Rule-based then Score-based)
    # Use None for included_posts to ignore author daily limits for this test
    result = hybrid_screening.screen_content(post_data, latest_content=post, included_posts=None)
    
    # 6. Display Detailed Results
    status = result['status'].upper()
    reason = result['reason']
    rule_type = result['rule_type']
    
    # 5b. Detailed Author Status (Independent of this specific post)
    print(f"--- Author Status Summary (@{author}) ---")
    
    # Curation History usage
    daily_limit = validator.get_int('HISTORY', 'MAX_AUTHOR_PER_DAY', 1)
    daily_count = hybrid_screening.curation_history.get_author_curation_count(author, days=1)
    weekly_limit = validator.get_int('HISTORY', 'MAX_AUTHOR_PER_WEEK', 2)
    weekly_count = hybrid_screening.curation_history.get_author_curation_count(author, days=7)
    
    # Fetch account data for live status checks
    account_data = s.get_account(author)
    raw_rep = account_data.get('reputation', 0)
    rep_val = rep_log10(raw_rep)
    min_rep = validator.get_int('AUTHOR', 'MIN_REPUTATION', 0)
    
    status_bl  = isBlacklisted(author, steem_instance=s)
    status_wl  = isAuthorWhitelisted(author)
    status_rep = isRepTooLow(raw_rep)
    days_inact = inactiveDays(author, steem_instance=s)
    max_inact  = validator.get_int('AUTHOR', 'MAX_INACTIVITY_DAYS', 0)
    hive_act   = isHiveActivityTooRecent(author)
    blurt_act  = isBlurtActivityTooRecent(author)
    wallet_flg = walletScreened(author, steem_instance=s)

    print(f"  Blacklisted      : {'FAIL' if status_bl else 'PASS'}")
    print(f"  Whitelisted      : {'YES' if status_wl else 'NO'}")
    print(f"  Reputation       : {rep_val:.2f} (Min: {min_rep}) -> {'PASS' if not status_rep else 'FAIL'}")
    print(f"  Steem Inactivity : {days_inact} days (Max: {max_inact}) -> {'PASS' if max_inact == 0 or days_inact <= max_inact else 'FAIL'}")
    print(f"  Hive Activity    : {'FAIL (Too Recent)' if hive_act else 'PASS'}")
    print(f"  Blurt Activity   : {'FAIL (Too Recent)' if blurt_act else 'PASS'}")
    print(f"  Wallet Screening : {'FAIL (Flagged)' if wallet_flg else 'PASS'}")
    print(f"  Curation History : Daily {daily_count}/{daily_limit}, Weekly {weekly_count}/{weekly_limit}")
    
    # Broad eligibility calculation
    # Whitelisted authors pass unless blacklisted. 
    # Regular authors must pass all checks and be within history limits.
    author_eligible = not status_bl and (status_wl or (not status_rep and (max_inact == 0 or days_inact <= max_inact) and not hive_act and not blurt_act and not wallet_flg and daily_count < daily_limit and weekly_count < weekly_limit))
    
    print(f"  AUTHOR ELIGIBLE  : {'YES' if author_eligible else 'NO'}")
    print(f"{'-'*40}\n")

    # 6. Display Specific Post Result
    print(f"DECISION        : {status}")
    print(f"REASON          : {reason}")
    print(f"RULE CATEGORY   : {rule_type}")
    
    if result.get('score_result'):
        score = result['score_result']
        print(f"QUALITY TIER    : {result['quality_tier'].upper()}")
        print(f"TOTAL SCORE     : {result['total_score']:.2f} / 100.00")
        
        print(f"\nCOMPONENT BREAKDOWN:")
        print(f"  - Author Quality    : {score['components']['author']:.2f}")
        print(f"  - Content Quality   : {score['components']['content']:.2f}")
        print(f"  - Engagement Quality: {score['components']['engagement']:.2f}")
        
        print(f"\nMETRICS SUMMARY:")
        details = score['details']
        print(f"  - Net Votes         : {details.get('net_votes', 'N/A')}")
        print(f"  - Comments          : {details.get('children', 'N/A')}")
        print(f"  - Payout Value      : {details.get('pending_payout_value', 'N/A')} (pending) / {details.get('total_payout_value', 'N/A')} (total)")
        print(f"  - Tags              : {', '.join(details.get('tags', []))}")
        print(f"  - Created           : {details.get('created', 'N/A')}")
    else:
        print("\n[!] NOTE: Scoring was bypassed.")
        print("This post was rejected (or whitelisted) by a rule-based constraint before")
        print("it could be evaluated by the scoring engine.")

    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()