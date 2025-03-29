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

    body=f"""
AI Curation by [Thoth](https://github.com/remlaps/Thoth)

This post was generated with the assistance of the following AI model: <i>{config.get('ARLIAI','ARLIAI_MODEL')}</i>
    """

    body+='<div class=pull-right>\n\n[![](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)<h6><sup>Image by AI</sup></h6>\n\n</div>\n\n'

    body+=f"""
Named after the ancient Egyptian god of writing, science, art, wisdom, judgment, and magic, <i>Thoth</i> is an Open Source curation bot that is intended to align incentives for authors and investors towards the production and support of creativity that attracts human eyeballs to the Steem blockchain.<br><br>

This will be done by:
1. Identifying attractive posts on the blockchain - past and present;
2. Highlighting those posts for curators; and
3. Using beneficiary rewards to deliver additional rewards to authors and delegators.<br><br>

If the highlighted post has passed payout, you can upvote this post in order to reward to the included authors.  If it is still eligible for payout, you can also click through and vote on the orginal post.  Either way, you may also wish to click through and engage with the original author!<br><br>

Here are the posts that are featured in this curation post:<br><br>
"""

    body+="<table>"
    for lcv, comment in enumerate(commentList):
        body += "<tr>\n"
        body += f'<td><b>{lcv + 1}</b>: </td>\n'
        body += f'<A HREF="/thoth/@{comment["author"]}/{comment["permlink"]}" target="_blank">{repr(comment["title"])}</A></td>\n'
        body += f'<td>@{commentList[lcv]["author"]}</td>\n'
        body += '</tr>\n'

    body += "</table><br><br>And here is the AI response for each post:<br><br>"

    for lcv, aiResponse in enumerate(aiResponseList):
        body += '<table border="1">\n'
        body += '   <tr>\n'
        body += f'     <td><b>Post #</b></td>\n'
        body += f'     <td><b>Title</b></td>\n'
        body += f'     <td><b>Author</b></td>\n'
        body += f'  </tr><tr>\n'
        body += f'     <td>{lcv + 1}</td>\n'
        body += f'     <td><a href="/thoth/@{commentList[lcv]["author"]}/{commentList[lcv]["permlink"]}">{repr(commentList[lcv]["title"])}</a></td>\n'
        body += f'     <td>@{commentList[lcv]["author"]}</td>\n'
        body += f'   </tr>\n'
        body += f'</table>'
        body += f'<blockquote>{aiResponse}</blockquote><br><br>\n'

    body += "You can contribute to the project or download your own copy of the code, [here](https://github.com/remlaps/Thoth)"

    beneficiaryList = ['null', postingAccount ]
    for comment in commentList:
        beneficiaryList.append(comment['author'])
        
    beneficiaryList = create_beneficiary_list ( beneficiaryList )

    comment_options = {
        'max_accepted_payout': '1000000.000 SBD',
        'percent_steem_dollars': 0,
        'allow_votes': True,
        'allow_curation_rewards': True,
        'extensions': [[0, { }]]
    }

    permlink = f"thoth{randValue}"
    taglist="['test', 'test1', 'test2', 'test3', 'test4']"

    print (f"Body: {body}")
    print (f"Body length:  {len(body)}")
    print (f"Tags: {taglist}")
    print (f"Beneficiaries: {beneficiaryList}")
    postDone=False
    while not postDone:
        now = datetime.datetime.now()
        timeStamp = now.strftime("%Y-%m-%d %H:%M")
        title = f"Curated by Thoth - {timeStamp}"
        print(f"Posting: {title}")
        print(body)
        with open('data/fakepost.html', 'w', encoding='utf-8') as f:
            print(f"{body}", file=f)
        try:
            s.commit.post(title, body, postingAccount, permlink=permlink, comment_options=comment_options, tags=taglist, beneficiaries=beneficiaryList)
            postDone=True
        except Exception as E:
            print (E)
            time.sleep(60)