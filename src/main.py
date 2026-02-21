import configparser
import re
import os
import time
from datetime import datetime
import math

import aiIntro
import utils  # From the thoth package
import aiCurator # From the thoth package
import postHelper # From the thoth package
import delegationInfo
from configValidator import ConfigValidator
from modelManager import ModelManager
from steemHelpers import initialize_steem_with_retry
import version

from steem.blockchain import Blockchain
from steem import Steem

# Create ONE high-quality RNG instance at module level with explicit entropy
_rng = utils.get_rng()

print(f"Starting Thoth v{version.__version__} ({version.__status__})")

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

# Initialize the ModelManager for handling multiple models and rate limiting
model_manager = ModelManager(arliaiModel)
print(f"Initialized model manager with models: {model_manager.models}")

# Feature flag: enable model switching and optional dry-run
try:
    enable_model_switching = config.getboolean('ARLIAI', 'ARLIAI_ENABLE_MODEL_SWITCHING', fallback=False)
except Exception:
    enable_model_switching = config.get('ARLIAI', 'ARLIAI_ENABLE_MODEL_SWITCHING', fallback='False').lower() in ('1', 'true', 'yes', 'on')

try:
    model_switching_dry_run = config.getboolean('ARLIAI', 'ARLIAI_MODEL_SWITCHING_DRY_RUN', fallback=False)
except Exception:
    model_switching_dry_run = config.get('ARLIAI', 'ARLIAI_MODEL_SWITCHING_DRY_RUN', fallback='False').lower() in ('1', 'true', 'yes', 'on')

print(f"Model switching enabled: {enable_model_switching}. Dry run: {model_switching_dry_run}")

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

# Time-bias weight used by TIME_WEIGHTED_RANDOM stream type; 0 = uniform, >0 favors recent blocks
try:
    stream_time_weight = float(config.get('STEEM', 'STREAM_TIME_WEIGHT', fallback='1.0'))
except Exception:
    stream_time_weight = 1.0

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

defaultStartBlockStr = config.get('STEEM', 'DEFAULT_START_BLOCK').split()[0]
defaultStartBlock = int(defaultStartBlockStr)

if ( streamType == 'RANDOM' ):
    streamFromBlock = _rng.integers(defaultStartBlock,
        steemdInstance.get_dynamic_global_properties()['last_irreversible_block_num'] - (20 * 60 * 24 * 30),
        endpoint=True)
elif ( streamType == 'TIME_WEIGHTED_RANDOM' ):
    # Choose a block randomly but favor more recent blocks.
    # We define the available range from defaultStartBlock .. payoutBlock (30 days earlier than tip).
    last_irreversible = steemdInstance.get_dynamic_global_properties()['last_irreversible_block_num']
    oneDayOld = last_irreversible - (20 * 60 * 24 * 1)
    if oneDayOld <= defaultStartBlock:
        # Fallback to uniform if range is invalid
        streamFromBlock = _rng.integers(defaultStartBlock, last_irreversible, endpoint=True)
    else:
        a = defaultStartBlock
        b = oneDayOld
        # Generate a uniform sample u in [0,1). If stream_time_weight <= 0 -> uniform.
        # Else apply complementary power transform to bias towards 1 (recent blocks):
        #   t = 1 - (1 - u) ** (1 + stream_time_weight)
        # Map continuous t in [0,1) to an inclusive integer in [a, b] by using
        # N = (b - a + 1) and idx = floor(t * N), so indices are 0..N-1 -> a..b.
        u = _rng.random()
        if stream_time_weight <= 0:
            t = u
        else:
            t = 1.0 - (1.0 - u) ** (1.0 + stream_time_weight)

        N = (b - a) + 1
        idx = int(math.floor(t * N))
        # defensive clamp
        if idx < 0:
            idx = 0
        elif idx >= N:
            idx = N - 1
        streamFromBlock = a + idx
elif ( streamType == 'ACTIVE' ):
    streamFromBlock = \
        max (steemdInstance.get_dynamic_global_properties()['last_irreversible_block_num'] - (20 * 60 * 24 * 6),
              lastBlock ) # 6 days or last processed
elif ( streamType == 'HISTORY'):
    # Read the last processed block number from file, if exists
    payoutBlock = steemdInstance.get_dynamic_global_properties()['last_irreversible_block_num'] - (20 * 60 * 24 * 30)
    
    if (lastBlock != 0 and lastBlock < payoutBlock ):
        streamFromBlock = lastBlock
    else:
        streamFromBlock = defaultStartBlock
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

                    screenResult = utils.screenPost(comment, included_posts=commentList, steem_instance=steemdInstance)
                    if screenResult == "Accept": 
                        ### Retrieve the latest version of the post
                        latestPostVersion=steemdInstance.get_content(comment['author'],comment['permlink'])
                        tmpBody = utils.remove_formatting(latestPostVersion['body'])
                        print(f"Comment by {comment['author']}/{comment['permlink']}: {comment['title']}\n{tmpBody[:100]}...")

                        ### Get the AI Evaluation
                        aiResponse = aiCurator.aicurate(
                            arliaiKey, arliaiModel, arliaiUrl, tmpBody,
                            model_manager=model_manager,
                            enable_switching=enable_model_switching,
                            dry_run=model_switching_dry_run
                        )
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

    aiIntroString = aiIntro.aiIntro(
        arliaiKey, arliaiModel, arliaiUrl,
        earliest_timestamp, latest_timestamp,
        "\n\n".join(aiResponseList), 16384,
        model_manager=model_manager,
        enable_switching=enable_model_switching,
        dry_run=model_switching_dry_run
    )
    # Retrieve delegations once and pass into postHelper to avoid duplicate RPC calls
    postingAccount_main = config.get('STEEM', 'POSTING_ACCOUNT')
    try:
        full_delegations = delegationInfo.get_delegations(postingAccount_main)
    except Exception as e:
        print(f"Warning: could not fetch delegations in main: {e}")
        full_delegations = []

    postHelper.postCuration(commentList, aiResponseList, aiIntroString, model_manager=model_manager, full_delegations=full_delegations)
    print("Posting finished.")
else:
    print("No posts were found to curate in the specified block range. Exiting.")