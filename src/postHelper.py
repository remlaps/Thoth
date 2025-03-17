from steem import Steem
import random
import string
import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

def create_beneficiary_list(beneficiary_list):
    # Initialize empty dictionary to track accounts and their weights
    account_weights = {}
    
    # Process each account in the list
    for account in beneficiary_list:
        if account == "null":
            # Special case for "null"
            account_weights[account] = 7000
        elif account == "social":
            # Special case for "social"
            account_weights[account] = 500
        else:
            # Regular accounts get 500, add if the account appears multiple times
            account_weights[account] = account_weights.get(account, 0) + 500
    
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
    s = Steem(keys=[postingKey], nodes=[steemApi])
    title = f"Curated by Thoth - {randValue}"
    author = 'social'

    body='AI Curation by [Thoth](https://github.com/remlaps)<br><br>'
    body=body + '<div class=pull-right>\n\n[![](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)<h6><sup>Image by AI</sup></h6>\n\n</div>'

    for lcv, aiResponse in enumerate(aiResponseList):
        body += f'\nPost number: {lcv + 1} - '
        body += f'[{commentList[lcv]["title"]}](/thoth/@{commentList[lcv]["author"]}/{commentList[lcv]["permlink"]})\n'
        body += f'Author: @{commentList[lcv]["author"]}\n\n'
        body += f'\n\n{aiResponse}\n'

    beneficiaryList = ['null', 'social']
    for comment in commentList:
        beneficiaryList.append(comment['author'])
        
    beneficiaryList = create_beneficiary_list ( beneficiaryList )

    comment_options = {
        'max_accepted_payout': '1000000.000 SBD',
        'percent_steem_dollars': 10000,
        'allow_votes': True,
        'allow_curation_rewards': True,
        'extensions': [[0, {
            'beneficiaries': beneficiaryList
        }]]
    }

    permlink = f"thoth{randValue}"
    taglist="['test', 'test1', 'test2', test3', 'test4']"

    print (f"Body: {body}")
    print (f"Tags: {taglist}")
    print (f"Beneficiaries: {beneficiaryList}")
    s.commit.post(title, body, author, permlink=permlink, comment_options=comment_options, tags=taglist, beneficiaries=None)