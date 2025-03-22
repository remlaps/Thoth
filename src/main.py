import configparser
import re
import os
import time
import random

import utils  # From the thoth package
import aiCurator # From the thoth package
import postHelper # From the thoth package

from steem.blockchain import Blockchain

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

arliaiKey=config.get('ARLIAI', 'ARLIAI_KEY')
arliaiModel=config.get('ARLIAI', 'ARLIAI_MODEL')
arliaiUrl=config.get('ARLIAI', 'ARLIAI_URL')

steemApi=config.get('STEEM', 'STEEM_API')

maxSize=config.getint('BLOG', 'NUMBER_OF_REVIEWED_POSTS')

blockchain = Blockchain()

commentList = []
aiResponseList = []

postCount=0
retry_count=0
max_retries = 5
retry_delay = 0.25  # Base delay in seconds

# File to store the last processed block
BLOCK_FILE = 'config/last_block.txt'

# Read the last processed block number from file, if exists
if os.path.exists(BLOCK_FILE):
    with open(BLOCK_FILE, 'r') as f:
        streamFromBlock = int(f.read().strip())
else:
    streamFromBlock = 3250000

print(f"Starting from block {streamFromBlock}")

while retry_count <= max_retries:
    try:
        if steemApi:
            blockchain = Blockchain(steemApi)
        else:
            stream = blockchain.stream(start_block=streamFromBlock, filter_by=['comment'])

        for operation in stream:
            streamFromBlock = operation['block_num'] + 1
            
            # Save the current block number to file
            with open(BLOCK_FILE, 'w') as f:
                f.write(str(streamFromBlock))
                
            print(streamFromBlock)
            retry_count = 0
            if (postCount >= maxSize):
                break    
            if 'type' in operation and operation['type'] == 'comment':
                comment = operation
                tmpBody = utils.remove_formatting(comment['body'])
                if 'parent_author' in comment and comment['parent_author'] == '':
                    if utils.screenPost(comment):
                        print(f"Comment by {comment['author']}: {comment['title']}\n{tmpBody[:100]}...")
                        aiResponse = aiCurator.aicurate(arliaiKey, arliaiModel, arliaiUrl, tmpBody)

                        print (f"\n\nAI Response: {aiResponse}\n")

                        if (not re.search("DO NOT CURATE", aiResponse)):
                            commentList.append(comment)
                            aiResponseList.append(aiResponse)
                            postCount = postCount + 1
                        else:
                            print(f"{postCount}: {operation['author']}/{operation['permlink']}: disqualified by AI.")
                    else:
                        print(f"{postCount}: {operation['author']}/{operation['permlink']}: excluded by screening.")
                else:
                    print(f"{postCount}: {operation['author']}/{operation['permlink']}: is a reply.")
            else:
                print(f"{postCount}: {operation['type']}")
        
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
                      
postHelper.postCuration(commentList, aiResponseList)
print("Posting finished.")