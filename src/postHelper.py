from steem import Steem
import random
import string
import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

def create_beneficiary_list(beneficiary_list):
    # Define the weights for each account
    account_weights = {
        'null': 4000,
        'social': 1000
    }
    
    # Initialize a dictionary to store the combined weights
    combined_weights = {}
    
    # Combine the weights
    for account in beneficiary_list:
        if account == "null":
            combined_weights[account] = 4000
        elif account == "social":
            combined_weights[account] = 1000
        elif account in combined_weights:
            combined_weights[account] += 1000
        else:
            combined_weights[account] = 1000
    
    # Convert the combined weights dictionary to a list of dictionaries
    result = [{'account': account, 'weight': weight} for account, weight in combined_weights.items()]
    
    return {'beneficiaries': result}


def postCuration (commentList, aiResponseList):
    postingKey=config.get('STEEM', 'POSTING_KEY')
    steemApi=config.get('STEEM', 'STEEM_API')

    # Connect to the STEEM blockchain
    randValue = ''.join(random.choices(string.ascii_lowercase, k=10))
    s = Steem(keys=[postingKey], nodes=[steemApi])
    title = f"Curated by THOTH - {randValue}"
    author = 'social'

    body='AI Curation by [Thoth](https://github.com/remlaps)'
    for lcv, aiResponse in enumerate(aiResponseList):
        body += f'\nPost number: {lcv + 1} - '
        body += f'[{commentList[lcv]["title"]}](/thoth/@{commentList[lcv]["author"]}/{commentList[lcv]["permlink"]})\n'
        body += f'Author: @{commentList[lcv]["author"]}\n\n'
        body += f'\n\n{aiResponse}\n'

    beneficiaryList = ['null', 'social']
    for comment in commentList:
        beneficiaryList.append(comment['author'])
        
    beneficiaryList = sorted(beneficiaryList)
    beneficiaryList = create_beneficiary_list ( beneficiaryList )

    comment_options = {
        'max_accepted_payout': '1000000.000 SBD',
        'percent_steem_dollars': 10000,
        'allow_votes': True,
        'allow_curation_rewards': True,
        'extensions': [[0, {
            'beneficiaries': beneficiaryList }
        ]]
    }

    permlink = f"thoth{randValue}"
    taglist="['test', 'test1', 'test2', test3', 'test4']"

    print (f"Body: {body}")
    print (f"Tags: {taglist}")
    print (f"Beneficiaries: {beneficiaryList}")
    s.commit.post(title, body, author, permlink=permlink, comment_options=comment_options, tags=taglist, beneficiaries=None)