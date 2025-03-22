from steem import Steem
import random
import string
import configparser
import datetime
import time

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')
postingAccount=config.get('BLOG', 'POSTING_ACCOUNT')
postingAccountWeight=config.getint('BLOG','POSTING_ACCOUNT_WEIGHT')
curatedPostCount=config.getint('BLOG','NUMBER_OF_REVIEWED_POSTS')
curatedAuthorWeight=config.getint('BLOG','CURATED_AUTHOR_WEIGHT')

def create_beneficiary_list(beneficiary_list):
    # Initialize empty dictionary to track accounts and their weights
    account_weights = {}
    
    # Process each account in the list
    totalWeight=0
    for account in beneficiary_list:
        if account == 'null':                ### Reward burning
            account_weights[account] = 10000 - ( postingAccountWeight + (curatedPostCount * curatedAuthorWeight))
            totalWeight += account_weights[account]
        elif account == postingAccount:      ### Account submitting the post
            account_weights[account] = 500
            totalWeight += 500
        else:
            # Regular accounts get 500, add if the account appears multiple times
            account_weights[account] = account_weights.get(account, 0) + 500
            totalWeight += 500

    if ( totalWeight != 10000 ):
        print (f"Total Weight: {totalWeight}")
        print (f"Account Weights: {account_weights}")
        print (f"Posting Account Weight: {postingAccountWeight}")
        print (f"Curated Post Count: {curatedPostCount}")
        print (f"Curated Author Weight: {curatedAuthorWeight}")
        print ("Something went wrong with the benficiaries.  Exiting.")
        exit()
    
    # Convert to list of dictionaries and sort alphabetically by account
    beneficiary_dicts = [{"account": account, "weight": weight} 
                         for account, weight in account_weights.items()]
    beneficiary_dicts.sort(key=lambda x: x["account"])
    
    # Return the beneficiaries list to be inserted into extensions
    return beneficiary_dicts

def postCuration (commentList, aiResponseList):
    postingKey=config.get('STEEM', 'POSTING_KEY')
    steemApi=config.get('STEEM', 'STEEM_API')

    # Connect to the STEEM blockchain
    randValue = ''.join(random.choices(string.ascii_lowercase, k=10))
    if ( steemApi and postingKey):
        s = Steem(keys=[postingKey], nodes=[steemApi])
    elif ( steemApi ):
        s = Steem(nodes=[steemApi])
    elif ( postingKey ):
        s = Steem(keys=[postingKey])
    else:
        s = Steem()

    body='AI Curation by [Thoth](https://github.com/remlaps/Thoth)<br><br>'
    body=body + '<div class=pull-right>\n\n[![](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)<h6><sup>Image by AI</sup></h6>\n\n</div>\n\n'

    for lcv, aiResponse in enumerate(aiResponseList):
        body += f'\n___Post number___: {lcv + 1} - '
        body += f'[{repr(commentList[lcv]["title"])}](/thoth/@{commentList[lcv]["author"]}/{commentList[lcv]["permlink"]})\n'
        body += f'Author: @{commentList[lcv]["author"]}\n\n'
        body += f'\n\n{aiResponse}\n'

    beneficiaryList = ['null', postingAccount ]
    for comment in commentList:
        beneficiaryList.append(comment['author'])
        
    beneficiaryList = create_beneficiary_list ( beneficiaryList )

    comment_options = {
        'max_accepted_payout': '1000000.000 SBD',
        'percent_steem_dollars': 10000,
        'allow_votes': True,
        'allow_curation_rewards': True,
        'extensions': [[0, { }]]
}

    permlink = f"thoth{randValue}"
    taglist="['test', 'test1', 'test2', test3', 'test4']"

    print (f"Body: {body}")
    print (f"Body length:  {len(body)}")
    print (f"Tags: {taglist}")
    print (f"Beneficiaries: {beneficiaryList}")
    postDone=False
    while not postDone:
        try:
            now = datetime.datetime.now()
            timeStamp = now.strftime("%Y-%m-%d %H:%M")
            title = f"Curated by Thoth - {timeStamp}"
            print(f"Posting: {title}")
            s.commit.post(title, body, postingAccount, permlink=permlink, comment_options=comment_options, tags=taglist, beneficiaries=beneficiaryList)
            print(body)
            postDone=True
        except Exception as E:
            print (E)
            time.sleep(60)