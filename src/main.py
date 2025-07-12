import configparser
import re
import os
import time
import random
from datetime import datetime

import aiIntro
import utils  # From the thoth package
import aiCurator # From the thoth package
import postHelper # From the thoth package

from steem.blockchain import Blockchain
from steem import Steem

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

arliaiKey=config.get('ARLIAI', 'ARLIAI_KEY').split()[0]  # Eliminate comments after the key
arliaiModel=config.get('ARLIAI', 'ARLIAI_MODEL')
arliaiUrl=config.get('ARLIAI', 'ARLIAI_URL')

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

if steemApi:
    steemdInstance = Steem(node=steemApi)
    print (f"Using Steem: {steemApi}")
else:
    steemdInstance = Steem()
    print (f"Using Steem: default")

if steemApi:
    blockchain = Blockchain(steemd_instance=steemdInstance)
    print(f"Using blockchain: {steemApi}")
else:
    blockchain = Blockchain()
    print(f"Using blockchain: default")


if ( streamType == 'RANDOM' ):
    streamFromBlock = random.randint(config.getint('STEEM', 'DEFAULT_START_BLOCK'), 
        steemdInstance.get_dynamic_global_properties()['last_irreversible_block_num'] - (20 * 60 * 24 * 30) )
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
            jitter = random.uniform(0.1, 0.5)
            wait_time = (retry_delay * (2 ** (retry_count-1))) + jitter
            
            print(f"Rate limit exceeded. Retry {retry_count}/{max_retries} after {wait_time:.2f} seconds...")
            time.sleep(wait_time)

        else:
            # If not a rate limit error, re-raise
            print(f"Unexpected error: {e}")
            if retry_count >= max_retries:
                raise
            time.sleep(retry_delay)

if earliest_timestamp and latest_timestamp:
    # The timestamps from the stream are already datetime objects.
    print(f"Posts processed ranged from {earliest_timestamp.strftime('%Y-%m-%dT%H:%M:%S')} to {latest_timestamp.strftime('%Y-%m-%dT%H:%M:%S')}")

    aiIntroString = aiIntro.aiIntro(arliaiKey, arliaiModel, arliaiUrl,
                                    earliest_timestamp, latest_timestamp,
                                    "\n\n".join(aiResponseList))
    postHelper.postCuration(commentList, aiResponseList, aiIntroString)
    print("Posting finished.")
else:
    print("No posts were found to curate in the specified block range. Exiting.")