import configparser
import re
import os
import time
from datetime import datetime
import math
import io
import sys
import logging

import aiIntro
import utils  # From the thoth package
import aiCurator # From the thoth package
import postHelper # From the thoth package
import delegationInfo
from configValidator import ConfigValidator
from hybridScreening import HybridScreening
from modelManager import ModelManager
from statsTracker import StatsTracker
from steemHelpers import initialize_steem_with_retry
import version

from steem.blockchain import Blockchain
from steem import Steem

# Create ONE high-quality RNG instance at module level with explicit entropy
_rng = utils.get_rng()

# Reconfigure stdout and stderr to use UTF-8 encoding, especially for Windows,
# to prevent 'charmap' codec errors when printing non-ASCII characters.
if sys.stdout.encoding.lower().replace('-', '') != 'utf8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception as e:
        print(f"Warning: Could not reconfigure stdout/stderr to UTF-8: {e}")

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

llmKey = os.getenv('LLMAPIKEY')
source_msg = "Using LLM API key from environment variable 'LLMAPIKEY'."

if not llmKey:
    source_msg = "LLMAPIKEY environment variable not set, falling back to config file."
    # Use fallback to prevent an error if the key is missing in the config.
    llmKey = config.get('LLM', 'LLM_API_KEY', fallback='')

# It's crucial to have a key. Exit if it's missing or empty.
if not llmKey.strip():
    print("FATAL: LLM API key is missing or empty. Please set LLMAPIKEY or configure LLM_API_KEY in config.ini.")

print(source_msg)

# Clean the key. This handles comments from the config file (e.g., "key # comment")
# and also strips quotes or whitespace that might be included from an environment variable.
llmKey = llmKey.split('#', 1)[0].strip().strip('"\'')
llmModel=config.get('LLM', 'LLM_MODEL')
llmUrl=config.get('LLM', 'LLM_URL')

# Initialize the ModelManager for handling multiple models and rate limiting
model_manager = ModelManager(llmModel)
print(f"Initialized model manager with models: {model_manager.models}")

# Feature flag: enable model switching and optional dry-run
try:
    enable_model_switching = config.getboolean('LLM', 'LLM_ENABLE_MODEL_SWITCHING', fallback=False)
except Exception:
    enable_model_switching = config.get('LLM', 'LLM_ENABLE_MODEL_SWITCHING', fallback='False').lower() in ('1', 'true', 'yes', 'on')

try:
    model_switching_dry_run = config.getboolean('LLM', 'LLM_MODEL_SWITCHING_DRY_RUN', fallback=False)
except Exception:
    model_switching_dry_run = config.get('LLM', 'LLM_MODEL_SWITCHING_DRY_RUN', fallback='False').lower() in ('1', 'true', 'yes', 'on')

try:
    skip_ai_curation = config.getboolean('LLM', 'SKIP_AI_CURATION', fallback=False)
except Exception:
    skip_ai_curation = config.get('LLM', 'SKIP_AI_CURATION', fallback='False').lower() in ('1', 'true', 'yes', 'on')

print(f"Model switching enabled: {enable_model_switching}. Dry run: {model_switching_dry_run}. Skip AI curation: {skip_ai_curation}")

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
scoreList = []  # Track scores for each curated post

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

# Initialize the statistics tracker
stats_tracker = StatsTracker()

# Initialize the Hybrid Screening system for quality-based curation
hybrid_screening = HybridScreening(steemdInstance, validator, stats_tracker=stats_tracker)
print("Hybrid screening system initialized.")

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

                    # Use hybrid screening system (rule-based first, then score-based)
                    try:
                        screening_result = hybrid_screening.screen_content(comment, included_posts=commentList)
                        status = screening_result['status']
                        reason = screening_result['reason']
                        
                        logging.info(f"Comment by {comment['author']}/{comment['permlink']}: {comment['title']}")
                        logging.info(f"Screening Status: {status} ({reason})")
                        
                        if screening_result['score_result']:
                            total_score = screening_result['total_score']
                            quality_tier = screening_result['quality_tier']
                            ai_intensity = screening_result['ai_intensity']
                            logging.info(f"Score: {total_score} ({quality_tier}) - AI Intensity: {ai_intensity}")
                            logging.info(f"Components: Author={screening_result['score_result']['components']['author']}, Content={screening_result['score_result']['components']['content']}, Engagement={screening_result['score_result']['components']['engagement']}")
                        else:
                            logging.info("No score available (rejected by rule-based screening)")
                    except Exception as e:
                        print(f"Error in hybrid screening for {comment['author']}/{comment['permlink']}: {e}")
                        continue
                    
                    # Determine if content should be curated based on hybrid screening
                    should_curate = hybrid_screening.should_curate(screening_result)
                    ai_intensity = hybrid_screening.get_ai_analysis_intensity(screening_result)
                    
                    if should_curate and ai_intensity != 'none':
                        ### Retrieve the latest version of the post
                        latestPostVersion=steemdInstance.get_content(comment['author'],comment['permlink'])
                        tmpBody = utils.remove_formatting(latestPostVersion['body'])
                        logging.info(f"Content accepted for curation with {ai_intensity} AI analysis.")

                        ### Get the AI Evaluation with score context
                        logging.info(f"[{streamFromBlock}/{postCount}] Starting AI Curation evaluation for @{operation['author']}/{operation['permlink']}...")
                        if skip_ai_curation:
                            logging.info(f"Skipping AI Curation API call for @{operation['author']}/{operation['permlink']} (SKIP_AI_CURATION is enabled).")
                            aiResponse = f"[SKIP_AI_CURATION ENABLED] Mock AI curation summary for post by @{operation['author']}. This placeholder text ensures the minimum response length requirement is met without calling the LLM API. {'=' * 50}"
                        else:
                            aiResponse = aiCurator.aicurate(
                                llmKey, llmModel, llmUrl, tmpBody,
                                model_manager=model_manager,
                                enable_switching=enable_model_switching,
                                dry_run=model_switching_dry_run,
                                author=operation['author'],
                                permlink=operation['permlink']
                            )
                        with open('data/output.html', 'a', encoding='utf-8') as f:
                            print(f"URL: https://steemit.com/@{comment['author']}/{comment['permlink']}")
                            print(f"Title: {latestPostVersion['title']}")
                            if screening_result['score_result']:
                                print(f"Score: {screening_result['total_score']} ({screening_result['quality_tier']})")
                            print(f"Body (first 200 chars): {tmpBody[:200]}...\n\nAI Response: {aiResponse}\n", file=f)
                        logging.info(f"[{streamFromBlock}/{postCount}] Finished AI Curation for @{operation['author']}/{operation['permlink']}.")
                        logging.info(f"AI Response:\n{aiResponse}\n")

                        MIN_AI_RESPONSE_LENGTH = 100 # Define a reasonable minimum length
                        if (re.search("DO NOT CURATE", aiResponse) or (aiResponse == "Content Error - Empty Body" )):
                            logging.info(f"{streamFromBlock}/{postCount}: @{operation['author']}/{operation['permlink']}: disqualified by AI.")
                        elif aiResponse.startswith("API Error") or \
                             aiResponse == "JSON Error" or \
                             aiResponse == "Response Error" or \
                             aiResponse == "Unexpected Error":
                            # aiCurator has already attempted retries for relevant API errors.
                            # Log the failure and continue with the next post.
                            logging.error(f"{streamFromBlock}/{postCount}: AI Curation for @{operation['author']}/{operation['permlink']} failed. AI System Response: '{aiResponse}'. Skipping this post.")
                        elif len(aiResponse) < MIN_AI_RESPONSE_LENGTH:
                            logging.warning(f"{streamFromBlock}/{postCount}: @{operation['author']}/{operation['permlink']}: disqualified by AI (response too short: '{aiResponse}').")
                        else:
                            commentList.append(comment)
                            aiResponseList.append(aiResponse)
                            # Track scores for each curated post (only if scoring was performed)
                            if screening_result['score_result']:
                                scoreList.append(screening_result['score_result'])
                            else:
                                # Create a minimal score entry for rejected posts
                                scoreList.append({
                                    'total_score': 0.0,
                                    'quality_tier': 'rejected',
                                    'components': {'author': 0.0, 'content': 0.0, 'engagement': 0.0}
                                })
                            postCount = postCount + 1
                            logging.info(f"Content curated successfully! ({postCount}/{maxSize})")
                    else:
                        reason = screening_result['reason']
                        logging.info(f"{streamFromBlock}/{postCount}: @{operation['author']}/{operation['permlink']}: excluded by hybrid screening ({reason})")
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

    if skip_ai_curation:
        logging.info("Skipping AI Intro generation (SKIP_AI_CURATION is enabled).")
        aiIntroString = f"[SKIP_AI_CURATION ENABLED] Mock AI Intro summary. This placeholder text is generated because the AI API calls are bypassed in the configuration. {'=' * 50}"
    else:
        logging.info("Starting AI Intro generation...")
        aiIntroString = aiIntro.aiIntro(
            llmKey, llmModel, llmUrl,
            earliest_timestamp, latest_timestamp,
            "\n\n".join(aiResponseList), 16384,
            model_manager=model_manager,
            enable_switching=enable_model_switching,
            dry_run=model_switching_dry_run,
            score_data=scoreList
        )
        logging.info("Finished AI Intro generation.")
    # Retrieve delegations once and pass into postHelper to avoid duplicate RPC calls
    postingAccount_main = config.get('STEEM', 'POSTING_ACCOUNT')
    try:
        full_delegations = delegationInfo.get_delegations(postingAccount_main)
    except Exception as e:
        print(f"FATAL: Could not fetch delegations in main: {e}")
        exit(1)

    postHelper.postCuration(commentList, aiResponseList, aiIntroString, model_manager=model_manager, full_delegations=full_delegations)
    print("Posting finished.")

    # Generate and print statistics report
    stats_report = stats_tracker.generate_report()
    print(stats_report)
    with open('data/output.html', 'a', encoding='utf-8') as f:
        # Use <pre> for preformatted text in HTML
        print(f"\n<hr>\n<h2>Run Statistics</h2>\n<pre>{stats_report}</pre>", file=f)
else:
    print("No posts were found to curate in the specified block range. Exiting.")
    # Also print stats here, in case some posts were evaluated but none were accepted.
    stats_report = stats_tracker.generate_report()
    print(stats_report)
    with open('data/output.html', 'a', encoding='utf-8') as f:
        print(f"\n<hr>\n<h2>Run Statistics</h2>\n<pre>{stats_report}</pre>", file=f)