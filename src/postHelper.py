from steem import Steem
import random
import string
import configparser
import datetime
import time
import contentValidation
import delegationInfo
import threading

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')
postingAccount=config.get('STEEM', 'POSTING_ACCOUNT')
postingAccountWeight=config.getint('BLOG','POSTING_ACCOUNT_WEIGHT')
curatedPostCount=config.getint('BLOG','NUMBER_OF_REVIEWED_POSTS')
curatedAuthorWeight=config.getint('BLOG','CURATED_AUTHOR_WEIGHT')
delegatorCount=config.getint('BLOG','NUMBER_OF_DELEGATORS_PER_POST')
delegatorWeight=config.getint('BLOG','DELEGATOR_WEIGHT')
taglist = config.get("BLOG","POST_TAGS")
thothCategory=taglist.split(',')[0]

def create_beneficiary_list(beneficiary_list):
    # Initialize empty dictionary to track accounts and their weights
    account_weights = {}
    
    # Process each account in the list
    totalWeight=0
    for account in beneficiary_list:
        if account == 'null':                ### Reward burning
            account_weights[account] = \
                10000 - ( postingAccountWeight + (curatedPostCount * curatedAuthorWeight) + (delegatorCount * delegatorWeight))
            totalWeight += account_weights[account]
        elif account == postingAccount:      ### Account submitting the post
            account_weights[account] = postingAccountWeight
            totalWeight += postingAccountWeight
        else:
            print(f"Account: {account}")
            accountType=account.split('-')[0]
            tmpAccount='-'.join(account.split('-')[1:])
            if accountType == 'a':
                account_weights[tmpAccount] = account_weights.get(tmpAccount, 0) + curatedAuthorWeight
                totalWeight += curatedAuthorWeight
            elif accountType == 'd':
                account_weights[tmpAccount] = account_weights.get(tmpAccount, 0) + delegatorWeight
                totalWeight += delegatorWeight

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

def vote_in_background(postingAccount, permlink, voteWeight=100):
    time.sleep(300)
    Steem().commit.vote(f"@{postingAccount}/{permlink}", voteWeight, postingAccount)

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
| |
| --- |
| <h6>Unlocking permanent rewards for your Steem content</h6> |

This post was generated with the assistance of the following AI model: <i>{config.get('ARLIAI','ARLIAI_MODEL')}</i>
    """

    body+='<div class=pull-right>\n\n[![](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)<h6><sup>Image by AI</sup></h6>\n\n</div>\n\n'

    body+=f"""
Named after the ancient Egyptian god of writing, science, art, wisdom, judgment, and magic, <i>Thoth</i> is an Open Source curation bot that is intended to align incentives for authors and investors towards the production and support of creativity that attracts human eyeballs to the Steem blockchain.<br><br>

This will be done by:
1. Identifying attractive posts on the blockchain - past and present;
2. Highlighting those posts for curators;
3. Deliver beneficiary rewards to the creators who are producing blockchain content with lasting value; and
4. Deliver beneficiary rewards to the delegators who support the curation initiative.<br><br>

If the highlighted post has already paid out, you can upvote this post in order to send rewards to the included authors.  If it is still eligible for payout, you can also click through and vote on the orginal post.  Either way, you may also wish to click through and engage with the original author!<br><br>

Here are the posts that are featured in this curation post:<br><br>
"""

    body+="<table>"
    for lcv, comment in enumerate(commentList):
        steemPost=s.get_content(comment['author'],comment['permlink'])
        tags = contentValidation.getTags(steemPost)
        tagString=""
        for index, tag in enumerate(tags):
            if ( tag != "" ):
                tagString+=f"<A HREF='/hot/{tag}'>{tag}</A>"
                if ( index < len(tags)-1):
                    tagString +=", "
        body += "<tr>\n"
        body += f'   <td><b>{lcv + 1}</b>: </td>\n'
        body += f'   <td><A HREF="/thoth/@{comment["author"]}/{comment["permlink"]}" target="_blank">{repr(comment["title"])}</A>'
        body += f'      <hr>\n'
        body += f'      <b>Tags</b>: {tagString}</td>\n'
        body += f'   <td>@{commentList[lcv]["author"]}'
        body += f'      <hr>\n'
        body += f'      <b>Created</b>: {steemPost["created"]}</td>\n'
        body += '</tr>\n'

    body += "</table><br><br>And here is the AI response for each post:<br><br><hr>"

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
        body += f'<table><tr><td>{aiResponse}\n\n'
        body += '</td></tr></table><br><br>\n'  ## Whitespace needed by Steemit/Upvu web sites.  No idea wy.

    body += "<br><br>Obviously, inclusion in this list does not imply endorsement of the author's ideas.  The list was built by AI and other automated tools, so the results may contain halucinations, errors, or controversial opinions.  If you see content that should be filtered in the future, please let the operator know.\n"
    body += f"<br><br>This Thoth instance is operated by {config.get('BLOG', 'THOTH_OPERATOR')}\n"
    body += "<br><br>\n\nYou can contribute to Thoth or download your own copy of the code, [here](https://github.com/remlaps/Thoth)"

    beneficiaryList = ['null', postingAccount ]
    # The "a/d account types is a kludge"
    for comment in commentList:
        beneficiaryList.append(f"a-{comment['author']}")
    delegatorList = delegationInfo.shuffled_delegators_by_weight(delegationInfo.get_delegations(postingAccount))
    for delegator in delegatorList[:delegatorCount]:
        beneficiaryList.append(f"d-{delegator}")
        
    beneficiaryList = create_beneficiary_list ( beneficiaryList )
    body += f"\n\n<br><br>Beneficiaries:<br><br>"
    body += "<table>"
    
    # Define the number of columns
    columns = 2
    for i, beneficiary in enumerate(beneficiaryList):
        if i % columns == 0:  # Start a new row for every 'columns' items
            body += "<tr>\n"
        body += f'   <td>{beneficiary["account"]} / {beneficiary["weight"] / 100}%</td>\n'
        if (i + 1) % columns == 0:  # Close the row after 'columns' items
            body += "</tr>\n"
    
    # Fill remaining cells in the last row, if necessary
    remaining_cells = columns - (len(beneficiaryList) % columns)
    if remaining_cells != columns:  # Only add if the last row isn't full
        for _ in range(remaining_cells):
            body += "   <td></td>\n"  # Add empty cells
        body += "</tr>\n"
    
    body += "</table><br><br>\n"

    permlink = f"thoth{randValue}"

    # taglist=[thothCategory, 'test1', 'test2', 'test3', 'test4']
    metadata = {
        "app": "Thoth/0.0.1"
    }

    comment_options = {
        'max_accepted_payout': '1000000.000 SBD',
        'percent_steem_dollars': 0,
        'allow_votes': True,
        'allow_curation_rewards': True,
        'extensions': [[0, { }]]
    }

    print (f"Body: {body}")
    print (f"Body length:  {len(body)}")
    print (f"Tags: {taglist}")
    print (f"Beneficiaries: {beneficiaryList}")
    postDone=False
    retryCount = 0
    while not postDone and retryCount < 3:
        now = datetime.datetime.now(datetime.timezone.utc)
        timeStamp = now.strftime("%Y-%m-%d %H:%M")
        title = f"Curated by Thoth - {timeStamp}Z"
        print(f"Posting: {title}")
        print(body)
        with open('data/fakepost.html', 'w', encoding='utf-8') as f:
            print(f"{body}", file=f)
        try:
            s.commit.post(title, body, postingAccount, permlink=permlink, tags=taglist,
                comment_options=comment_options, json_metadata=metadata, 
                beneficiaries=beneficiaryList)
            postDone=True
        except Exception as E:
            print (E)
            print ("Sleeping 1 minute before retry...")
            time.sleep(60)
            retryCount += 1
    if ( not postDone ):
        print (f"Post {title} failed.  Exiting.")
        return False
    
    voting_thread = threading.Thread(target=vote_in_background, args=(postingAccount, permlink, 100))
    voting_thread.start()
    print (f"Post completed and vote for {title} scheduled.")