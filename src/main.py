import configparser
import re

import utils  # From the thoth package
import aiCurator # From the thoth package
import postHelper # From the thoth package

from steem.blockchain import Blockchain

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
stream = blockchain.stream(node=steemApi)

commentList = []
aiResponseList = []

postCount=0
for operation in stream:
    if ( postCount >= maxSize ):
        break    
    if 'type' in operation and operation['type'] == 'comment':
        comment = operation
        tmpBody = utils.remove_formatting(comment['body'])
        if 'parent_author' in comment and comment['parent_author'] == '':
            if utils.screenPost(comment):
                print(f"Comment by {comment['author']}: {comment['title']}\n{tmpBody[:100]}...")
                aiResponse = aiCurator.aicurate(arliaiKey, arliaiModel, arliaiUrl, comment['author'],
                                                comment['permlink'], comment['title'], tmpBody)
                if ( not re.search("DO NOT CURATE", aiResponse)):
                    commentList.append(comment)
                    aiResponseList.append(aiResponse)
                    postCount=postCount + 1
                else:
                    print (f"{postCount}: {operation['author']}/{operation['permlink']}: disqualified by AI.")
            else:
                print(f"{postCount}: {operation['author']}/{operation['permlink']}: excluded by screening.")
        else:
            print(f"{postCount}: {operation['author']}/{operation['permlink']}: is a reply.")
    else:
        print(f"{postCount}: {operation['type']}")
                      
postHelper.postCuration(commentList, aiResponseList)
