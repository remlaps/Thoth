from steem import Steem
import random
import string
import configparser
import datetime
import time
import contentValidation
import delegationInfo
import threading
import utils

import replyHelper # From the thoth package

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
post_tags_config_string = config.get("BLOG", "POST_TAGS", fallback="") # Add fallback for safety
parsed_tags = [tag.strip() for tag in post_tags_config_string.split(',') if tag.strip()]
taglist = parsed_tags # taglist is the list of all parsed tags
initialWaitSeconds = config.getint('BLOG', 'VOTE_DELAY_SECONDS', fallback=600) # Default to 5 minutes if not set
votePercent = config.getint('BLOG', 'VOTE_PERCENT', fallback=100) # Default to 100% if not set

def create_beneficiary_list(beneficiary_list):
    # Initialize empty dictionary to track accounts and their weights
    account_weights = {}
    
    # Process each account in the list
    totalWeight=0
    for account in beneficiary_list:
        if account == postingAccount and postingAccountWeight != 0:      ### Account submitting the post
            account_weights[account] = postingAccountWeight
            totalWeight += postingAccountWeight
        elif account != 'null':
            print(f"Account: {account}")
            accountType=account.split('-')[0]
            tmpAccount='-'.join(account.split('-')[1:])
            if accountType == 'a':
                if curatedAuthorWeight != 0:
                    account_weights[tmpAccount] = account_weights.get(tmpAccount, 0) + curatedAuthorWeight
                    totalWeight += curatedAuthorWeight
            elif accountType == 'd':
                if delegatorWeight != 0:
                    account_weights[tmpAccount] = account_weights.get(tmpAccount, 0) + delegatorWeight
                    totalWeight += delegatorWeight

    account_weights['null'] = max(0, 10000 - totalWeight)
    totalWeight += account_weights['null']

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
    """
    Waits for an initial period, then attempts to vote in a loop until successful.
    Retries every 3 seconds upon any failure.
    """
    s_vote = Steem()
    retry_delay_seconds = 3

    print(f"Waiting {initialWaitSeconds // 60} minutes before attempting to vote for @{postingAccount}/{permlink}...")
    time.sleep(initialWaitSeconds)
    max_retries=20
    retries=0

    while retries < max_retries:
        try:
            print(f"Attempting to vote for @{postingAccount}/{permlink}...")
            s_vote.commit.vote(f"@{postingAccount}/{permlink}", voteWeight, postingAccount)
            print(f"Successfully voted for @{postingAccount}/{permlink}")
            break  # Exit loop on successful vote
        except Exception as e:
            print(f"Vote for @{postingAccount}/{permlink} failed: {e}. Retrying in {retry_delay_seconds} seconds...")
            time.sleep(retry_delay_seconds)
            retries += 1

def postCuration (commentList, aiResponseList, aiIntroString, model_manager=None, full_delegations=None):
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

    # Get the model that was actually used (from model_manager if provided, otherwise use config)
    if model_manager:
        models_used = model_manager.get_models_used()
        used_model = ", ".join(models_used) if len(models_used) > 1 else models_used[0] if models_used else "unknown"
    else:
        used_model = config.get('ARLIAI','ARLIAI_MODEL')

    body=f"""
AI Curation by [Thoth](https://github.com/remlaps/Thoth)
| <h6>Unlocking #lifetime-rewards for Steem's creators and #passive-rewards for delegators</h6> |
| --- |


This post was generated with the assistance of the following AI model(s): <i>{used_model}</i>
    """

    body+='<div class=pull-right>\n\n[![](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)](https://cdn.steemitimages.com/DQmWzfm1qyb9c5hir4cC793FJCzMzShQr1rPK9sbUY6mMDq/image.png)<h6><sup>Image by AI</sup></h6>\n\n</div>\n\n'

    body += f'\n\n{aiIntroString}\n\n<hr>'

    body+=f"""
Here are the articles that are featured in this curation post:<br><br>
"""

    body+="<hr><table>"
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

    body +="</table><hr>"
    
    body += "<br>Obviously, inclusion in this list does not imply endorsement of the author's ideas.  The list was built by AI and other automated tools, so the results may contain halucinations, errors, or controversial opinions.  If you see content that should be filtered in the future, please let the operator know.<br>\n"
    body += "<br>If the highlighted post has already paid out, you can upvote this post in order to send rewards to the included authors.  If it is still eligible for payout, you can also click through and vote on the orginal post.  Either way, you may also wish to click through and engage with the original author!<br><hr>\n"

    body+=f"""
### About <b><i>Thoth</i></b>:

Named after the ancient Egyptian god of writing, science, art, wisdom, judgment, and magic, <b><i>Thoth</i></i> is an Open Source curation bot that is intended to align incentives for authors and investors towards the production and support of creativity that attracts human eyeballs to the Steem blockchain.<br><br>

This will be done by:
1. Identifying attractive posts on the blockchain - past and present;
2. Highlighting those posts for curators;
3. Delivering beneficiary rewards to the creators who are producing blockchain content with lasting value; and
4. Delivering beneficiary rewards to the delegators who support the curation initiative.<br><br>
   - No rate of return is guaranteed or implied.
   - Reward amounts are entirely determined by blockchain consensus.
   - Delegator beneficiaries are randomly selected for inclusion in each post and reply with a weighting based on the amount of Steem Power delegated.

"""

    body += f"<br>This Thoth instance is operated by {config.get('BLOG', 'THOTH_OPERATOR')}<br>\n"
    body += "<br>\n\nYou can contribute to Thoth or download your own copy of the code, [here](https://github.com/remlaps/Thoth)"

    beneficiaryList = ['null', postingAccount ]
    # The "a/d account types is a kludge"
    for comment in commentList:
        beneficiaryList.append(f"a-{comment['author']}")

    # Get all delegations, filter out excluded accounts, and select beneficiaries
    try:
        # Use provided delegations when available to avoid duplicate RPC calls
        if full_delegations is None:
            full_delegations = delegationInfo.get_delegations(postingAccount)

        # Get lists of delegators to exclude from config
        pro_bono_delegators = [d.strip() for d in config.get('BLOG', 'PRO_BONO_DELEGATORS', fallback='').split(',') if d.strip()]
        ineligible_delegators = [d.strip() for d in config.get('BLOG', 'INELIGIBLE_DELEGATORS', fallback='').split(',') if d.strip()]
        all_excluded = pro_bono_delegators + ineligible_delegators

        # Filter the delegations using the new function
        eligible_delegations = delegationInfo.removeExcludedDelegators(full_delegations, all_excluded)

        # Shuffle the remaining delegators by weight and select the top ones
        if eligible_delegations:
            delegatorList = delegationInfo.shuffled_delegators_by_weight(eligible_delegations)
            selected_delegators = delegatorList[:delegatorCount]
            for delegator in selected_delegators:
                beneficiaryList.append(f"d-{delegator}")
        else:
            selected_delegators = []
            delegatorList = []

    except Exception as e:
        print(f"Could not process delegator beneficiaries due to an error: {e}")
        selected_delegators = []
        delegatorList = []

    beneficiaryList = create_beneficiary_list(beneficiaryList)
    author_accounts = [c['author'] for c in commentList]
    body += utils.generate_beneficiary_display_html(
        beneficiary_list=beneficiaryList,
        author_accounts=author_accounts,
        delegator_accounts=selected_delegators,
        thoth_account=postingAccount
    )

    permlink = f"thoth{randValue}"

    metadata = {
        "app": "Thoth/0.0.1"
    }

    comment_options = {
        'max_accepted_payout': '1000000.000 SBD',
        'percent_steem_dollars': 10000,
        'allow_votes': True,
        'allow_curation_rewards': True,
        'extensions': [[0, { }]]
    }

    print (f"Body: {body}")
    print (f"Body length:  {len(body)}")
    print (f"Tags: {taglist}")
    print (f"Beneficiaries: {beneficiaryList}")
    print(f"Delegator list (shuffled): {delegatorList}")
    print(f"Selected delegator(s): {selected_delegators}")
    
    active_voting_threads = [] # List to keep track of all voting threads
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
            postDone = True

            # After the main curation post is successful, post individual AI summary replies
            print(f"Main curation post '{title}' successful. Now posting individual AI summary replies...")
            for idx, (cmt_item, ai_resp_item) in enumerate(zip(commentList, aiResponseList)):
                print(f"Preparing to post AI summary reply for item {idx + 1} (Original author: @{cmt_item['author']})...")
                try:
                    # Call the modified postReply for each item
                    # postingAccount is the author of the main Thoth post (thothAccount for the reply)
                    # permlink is the permlink of the main Thoth post (thothPermlink for the reply)
                    reply_voting_thread = replyHelper.postReply(
                        comment_item=cmt_item,
                        ai_response_item=ai_resp_item,
                        item_index=idx, # 0-based index
                        thothAccount=postingAccount, # The account that made the main curation post
                        thothPermlink=permlink,       # The permlink of the main curation post
                        model_manager=model_manager,
                        full_delegations=full_delegations
                    )
                    if reply_voting_thread: # If a thread was successfully started by postReply
                        active_voting_threads.append(reply_voting_thread)
                        
                    # Wait for 6 seconds between posting replies to avoid API rate limits or other issues
                    print(f"Waiting 6 seconds before posting next reply...")
                    time.sleep(6)
                except Exception as e_reply:
                    print(f"Error occurred while trying to post AI summary reply for item {idx + 1} (Original author: @{cmt_item['author']}): {e_reply}")
                    print(f"Waiting 6 seconds before attempting next reply, if any...")
                    time.sleep(6) # Also wait if an error occurs before trying the next one
        except Exception as E:
            print (E)
            print ("Sleeping 1 minute before retry...")
            time.sleep(60)
            retryCount += 1
    if ( not postDone ):
        print (f"Post {title} failed.  Exiting.")
        return False
    
    voting_thread = threading.Thread(target=vote_in_background, args=(postingAccount, permlink, votePercent))
    voting_thread.daemon = True  # Allow main program to exit even if this thread is sleeping
    voting_thread.start()
    active_voting_threads.append(voting_thread) # Add the main post's voting thread
    print (f"All content posted. Main post vote for '{title}' scheduled in background.")

    if active_voting_threads:
        print(f"\nWaiting for all {len(active_voting_threads)} background votes to be cast (this may take several minutes)...")
        print("Press Ctrl-C to interrupt and exit if needed.")
        for i, thread_to_join in enumerate(active_voting_threads):
            while thread_to_join.is_alive(): # Loop to allow join to be interrupted by Ctrl-C
                thread_to_join.join(timeout=1.0) # Wait for 1 second, then check again
            print(f"Vote thread {i + 1}/{len(active_voting_threads)} has completed.")
        print("All background vote processing finished.")
    return True
