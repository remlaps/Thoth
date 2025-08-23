import configparser
import re
import os
import time
from datetime import datetime

import aiIntro
import utils  # From the thoth package
import aiCurator # From the thoth package
import postHelper # From the thoth package
from configValidator import ConfigValidator

from steem.blockchain import Blockchain
from steem import Steem

# Create ONE high-quality RNG instance at module level with explicit entropy
_rng = utils.get_rng()

def initialize_steem_with_retry(node_api=None, max_retries=5, initial_delay=1.0):
    """
    Initializes the Steem instance with a retry mechanism for connection errors.
    """
    for attempt in range(max_retries):
        try:
            if node_api:
                s = Steem(node=node_api)
            else:
                s = Steem()

            # The Steem() constructor implicitly calls get_dynamic_global_properties(),
            # which is where the UnboundLocalError from the traceback can occur.
            # If we reach here, the connection was successful.
            if node_api:
                print(f"Successfully connected to Steem node: {node_api}")
            else:
                print("Successfully connected to default Steem node.")
            return s
        except UnboundLocalError as e:
            # This specific error from the traceback indicates a probable transient issue in steem-python http_client
            if "cannot access local variable 'error'" in str(e):
                wait_time = initial_delay * (2 ** attempt)
                print(f"Caught specific UnboundLocalError during Steem init (Attempt {attempt + 1}/{max_retries}). Retrying in {wait_time:.2f}s... Error: {e}")
                time.sleep(wait_time)
            else:
                # If it's a different UnboundLocalError, we don't want to retry, so re-raise.
                print(f"Caught an unexpected UnboundLocalError. This is not the target error for retry. Raising.")
                raise
        except Exception as e:
            wait_time = initial_delay * (2 ** attempt)
            print(f"Failed to initialize Steem (Attempt {attempt + 1}/{max_retries}). Retrying in {wait_time:.2f}s... Error: {e}")
            time.sleep(wait_time)

    print(f"FATAL: Could not initialize Steem after {max_retries} attempts.")
    return None

# Check if the UNLOCK environment variable exists
if "UNLOCK" in os.environ:
    # The variable is set
    print(f"UNLOCK is set.")
else:
    # The variable is not set
    print("UNLOCK is not set.  It is recommended to use the steem-python wallet.")

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

arliaiKey = os.getenv('LLMAPIKEY')
source_msg = "Using LLM API key from environment variable 'LLMAPIKEY'."

if not arliaiKey:
    source_msg = "LLMAPIKEY environment variable not set, falling back to config file."
    # Use fallback to prevent an error if the key is missing in the config.
    arliaiKey = config.get('ARLIAI', 'ARLIAI_KEY', fallback='')

# It's crucial to have a key. Exit if it's missing or empty.
if not arliaiKey.strip():
    print("FATAL: LLM API key is missing or empty. Please set LLMAPIKEY or configure ARLIAI_KEY in config.ini.")

print(source_msg)

# Clean the key. This handles comments from the config file (e.g., "key # comment")
# and also strips quotes or whitespace that might be included from an environment variable.
arliaiKey = arliaiKey.split('#', 1)[0].strip().strip('"\'')
arliaiModel=config.get('ARLIAI', 'ARLIAI_MODEL')
arliaiUrl=config.get('ARLIAI', 'ARLIAI_URL')

### Validate the config to avoid failures at posting time.
validator = ConfigValidator()
    
if validator.validate_config():
    print("Configuration is valid!")
    # Continue with your application logic
else:
    print("Configuration validation failed:")
    for error in validator.get_errors():
        print(f"  - {error}")
    exit(1)

steemApi=config.get('STEEM', 'STEEM_API')
streamType = config.get('STEEM', 'STREAM_TYPE')

maxSize=config.getint('BLOG', 'NUMBER_OF_REVIEWED_POSTS')

commentList = []
aiResponseList = []

earliest_timestamp = None
latest_timestamp = None

postCount=0
retry_count=0
max_retries = 5
retry_delay = 0.25  # Base delay in seconds

# File to store the last processed block
BLOCK_FILE = 'config/last_block.txt'
if os.path.exists(BLOCK_FILE):
    with open(BLOCK_FILE, 'r') as f:
        lastBlock = int(f.read().strip())
else:
    lastBlock = 0

steemdInstance = initialize_steem_with_retry(node_api=steemApi)
if not steemdInstance:
    exit(1) # Exit if Steem connection failed

blockchain = Blockchain(steemd_instance=steemdInstance)
print(f"Using blockchain with nodes: {steemdInstance.steemd.nodes}")

if ( streamType == 'RANDOM' ):
    streamFromBlock = _rng.integers(config.getint('STEEM', 'DEFAULT_START_BLOCK'), 
        steemdInstance.get_dynamic_global_properties()['last_irreversible_block_num'] - (20 * 60 * 24 * 30),
        endpoint=True)
elif ( streamType == 'ACTIVE' ):
    streamFromBlock = \
        max (steemdInstance.get_dynamic_global_properties()['last_irreversible_block_num'] - (20 * 60 * 24 * 6), lastBlock ) # 6 days or last processed
elif ( streamType == 'HISTORY'):
    # Read the last processed block number from file, if exists
    payoutBlock = steemdInstance.get_dynamic_global_properties()['last_irreversible_block_num'] - (20 * 60 * 24 * 30)
    
    if (lastBlock != 0 and lastBlock < payoutBlock ):
        streamFromBlock = lastBlock
    else:
        streamFromBlock = config.getint('STEEM', 'DEFAULT_START_BLOCK')
else:
    print (f"Invalid CONFIG -> STREAM_TYPE setting: {streamType}")
    exit()
    
print(f"Starting from block {streamFromBlock}")

# Ensure the 'data' directory exists
os.makedirs('data', exist_ok=True)

# Empty and initialize the output file
with open('data/output.html', 'w', encoding='utf-8') as f:
    print(f"Starting from block {streamFromBlock}\n\n", file=f)

while retry_count <= max_retries:
    try:
        stream = blockchain.stream(start_block=streamFromBlock, filter_by=['comment'])

        for operation in stream:
            streamFromBlock = operation['block_num'] + 1
            
            # Save the current block number to file
            with open(BLOCK_FILE, 'w') as f:
                f.write(str(streamFromBlock))
                
            retry_count = 0
            if (postCount >= maxSize):
                break    
            if 'type' in operation and operation['type'] == 'comment':
                comment = operation

                if 'parent_author' in comment and comment['parent_author'] == '': # top-level posts only
                    current_timestamp = comment['timestamp']
                    # The timestamp from the stream is a datetime object.
                    if earliest_timestamp is None or current_timestamp < earliest_timestamp:
                        earliest_timestamp = current_timestamp
                    
                    if latest_timestamp is None or current_timestamp > latest_timestamp:
                        latest_timestamp = current_timestamp

                    screenResult = utils.screenPost(comment)
                    if screenResult == "Accept": 
                        ### Retrieve the latest version of the post
                        latestPostVersion=steemdInstance.get_content(comment['author'],comment['permlink'])
                        tmpBody = utils.remove_formatting(latestPostVersion['body'])
                        print(f"Comment by {comment['author']}/{comment['permlink']}: {comment['title']}\n{tmpBody[:100]}...")

                        ### Get the AI Evaluation
                        aiResponse = aiCurator.aicurate(arliaiKey, arliaiModel, arliaiUrl, tmpBody)
                        with open('data/output.html', 'a', encoding='utf-8') as f:
                            print(f"URL: https://steemit.com/@{comment['author']}/{comment['permlink']}")
                            print(f"Title: {latestPostVersion['title']}")
                            print(f"Body (first 200 chars): {tmpBody[:200]}...\n\nAI Response: {aiResponse}\n", file=f)
                        print (f"\n\nAI Response: {aiResponse}\n")

                        MIN_AI_RESPONSE_LENGTH = 100 # Define a reasonable minimum length
                        if (re.search("DO NOT CURATE", aiResponse) or (aiResponse == "Content Error - Empty Body" )):
                            print(f"{streamFromBlock}/{postCount}: @{operation['author']}/{operation['permlink']}: disqualified by AI.")
                        elif aiResponse.startswith("API Error") or \
                             aiResponse == "JSON Error" or \
                             aiResponse == "Response Error" or \
                             aiResponse == "Unexpected Error":
                            # aiCurator has already attempted retries for relevant API errors.
                            # Log the failure and continue with the next post.
                            print(f"{streamFromBlock}/{postCount}: AI Curation for @{operation['author']}/{operation['permlink']} failed. AI System Response: '{aiResponse}'. Skipping this post.")
                        elif len(aiResponse) < MIN_AI_RESPONSE_LENGTH:
                            print(f"{streamFromBlock}/{postCount}: @{operation['author']}/{operation['permlink']}: disqualified by AI (response too short: '{aiResponse}').")
                        else:
                            commentList.append(comment)
                            aiResponseList.append(aiResponse)
                            postCount = postCount + 1
                    else:
                        print(f"{streamFromBlock}/{postCount}: @{operation['author']}/{operation['permlink']}: excluded by screening: {screenResult}.")
                # else:
                    # print(f"{postCount}: {operation['type']}")
        
        # If we get here without exceptions, break out of the retry loop
        break
        
    except Exception as e:
        retry_count += 1
        
        if "this method is limited by 10r/s per ip" in str(e).lower():
            # Exponential backoff with jitter
            jitter = _rng.uniform(0.1, 0.5)
            wait_time = (retry_delay * (2 ** (retry_count-1))) + jitter
            
            print(f"Rate limit exceeded. Retry {retry_count}/{max_retries} after {wait_time:.2f} seconds...")
            time.sleep(wait_time)

        else:
            # If not a rate limit error, re-raise
            print(f"Unexpected error: {e}")
            if retry_count >= max_retries:
                raise
            time.sleep(retry_delay)
            
time.sleep(60)  # Give some time for rate limiting between AI Queries
if earliest_timestamp and latest_timestamp:
    # The timestamps from the stream are already datetime objects.
    print(f"Posts processed ranged from {earliest_timestamp.strftime('%Y-%m-%dT%H:%M:%S')} to {latest_timestamp.strftime('%Y-%m-%dT%H:%M:%S')}")

    aiIntroString = aiIntro.aiIntro(arliaiKey, arliaiModel, arliaiUrl,
                                    earliest_timestamp, latest_timestamp,
                                    "\n\n".join(aiResponseList), 16384)
    postHelper.postCuration(commentList, aiResponseList, aiIntroString)
    print("Posting finished.")
else:
    print("No posts were found to curate in the specified block range. Exiting.")