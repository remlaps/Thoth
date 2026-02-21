import sys
import os
import time
import argparse

# --- Set up paths to run from the 'tools' directory ---
# Get the absolute path of the project's root directory (one level up from 'tools')
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Change the current working directory to the project root.
os.chdir(project_root)

# Add the 'src' directory to the Python path to allow importing modules from it.
sys.path.append('src')

import configparser
from steem import Steem
import authorValidation

def main():
    parser = argparse.ArgumentParser(description="Test Steem get_accounts batch size capabilities.")
    parser.add_argument("account", help="The Steem account to fetch followers for (source of account names).")
    parser.add_argument("--batch-size", type=int, default=1000, help="The batch size to test for get_accounts (default: 1000).")
    
    args = parser.parse_args()
    account_name = args.account.replace('@', '')
    batch_size = args.batch_size

    print(f"--- Testing get_accounts batch size of {batch_size} using followers of @{account_name} ---")

    # Load config to get the node URL
    config = configparser.ConfigParser()
    config_path = os.path.join('config', 'config.ini')
    if os.path.exists(config_path):
        config.read(config_path)
        steem_api = config.get('STEEM', 'STEEM_API', fallback=None)
    else:
        steem_api = None
    
    print(f"Connecting to Steem node: {steem_api if steem_api else 'Default'}")
    try:
        s = Steem(node=steem_api) if steem_api else Steem()
    except Exception as e:
        print(f"Error connecting to Steem: {e}")
        sys.exit(1)

    # Fetch followers to generate a list of accounts to query
    print(f"Fetching followers for {account_name} to build the test list...")
    try:
        # We use the existing helper to get a list of names
        followers_data = authorValidation.getAllFollowers(account_name, steem_instance=s)
        follower_names = [entry['follower'] for entry in followers_data]
        print(f"Found {len(follower_names)} followers.")
    except Exception as e:
        print(f"Error fetching followers: {e}")
        sys.exit(1)

    if len(follower_names) == 0:
        print("Account has no followers. Cannot perform test.")
        sys.exit(1)

    # Process all followers in batches
    print(f"Testing get_accounts() with batch size {batch_size} across {len(follower_names)} followers...")

    for i in range(0, len(follower_names), batch_size):
        batch = follower_names[i:i + batch_size]
        print(f"Batch {i // batch_size + 1}: Fetching {len(batch)} accounts...")
        
        start_time = time.time()
        try:
            accounts = s.get_accounts(batch)
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"  Success! Fetched {len(accounts)} accounts in {duration:.4f} seconds.")
            
            if len(accounts) != len(batch):
                print(f"  Warning: Requested {len(batch)} accounts, but received {len(accounts)}.")
        except Exception as e:
            print(f"  Failed to fetch batch starting at index {i}.")
            print(f"  Error: {e}")

if __name__ == "__main__":
    main()