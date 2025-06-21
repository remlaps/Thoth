from steem import Steem
import random
import string
import configparser
import time
import delegationInfo
import threading
import utils
import steembase.exceptions # Required for specific exception handling

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')
postingAccount=config.get('STEEM', 'POSTING_ACCOUNT')
postingAccountWeight=config.getint('BLOG','POSTING_ACCOUNT_WEIGHT')
curatedPostCount=config.getint('BLOG','NUMBER_OF_REVIEWED_POSTS')
curatedAuthorWeight=config.getint('BLOG','CURATED_AUTHOR_WEIGHT') * curatedPostCount
delegatorCount=config.getint('BLOG','NUMBER_OF_DELEGATORS_PER_POST')
delegatorWeight=config.getint('BLOG','DELEGATOR_WEIGHT')
post_tags_config_string = config.get("BLOG", "POST_TAGS", fallback="") # Add fallback for safety
parsed_tags = [tag.strip() for tag in post_tags_config_string.split(',') if tag.strip()]
taglist = parsed_tags # taglist is the list of all parsed tags

def create_beneficiary_list(beneficiary_list, curatedAuthorWeight, delegatorWeight):
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
    Retries upon failure, especially for vote timing errors.
    """
    initial_wait_seconds = 300  # 5 minutes
    retry_delay_seconds = 5     # Base retry delay for general errors
    vote_interval_retry_delay_base = 3 # Base delay for vote interval errors (Steem rule)
    max_retries = 20
    retries = 0

    print(f"Vote for @{postingAccount}/{permlink} scheduled. Waiting {initial_wait_seconds // 60} minutes before first attempt...")
    time.sleep(initial_wait_seconds)

    while retries < max_retries:
        try:
            # Using simple Steem() instantiation as per current design in this function
            s_instance = Steem()
            print(f"Attempting to vote for @{postingAccount}/{permlink} (Attempt {retries + 1}/{max_retries})...")
            s_instance.commit.vote(f"@{postingAccount}/{permlink}", voteWeight, postingAccount)
            print(f"Successfully voted for @{postingAccount}/{permlink}")
            break  # Exit loop on successful vote
        except steembase.exceptions.RPCError as rpc_e:
            retries += 1
            if "STEEM_MIN_VOTE_INTERVAL_SEC" in str(rpc_e) or "Can only vote once every 3 seconds" in str(rpc_e):
                # Add a small random jitter to the 3-second base to avoid thundering herd
                wait_time = vote_interval_retry_delay_base + random.uniform(0.1, 1.0)
                print(f"Vote for @{postingAccount}/{permlink} failed due to rate limit: {rpc_e}. Retrying in {wait_time:.2f} seconds (Attempt {retries}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"Vote for @{postingAccount}/{permlink} failed with RPCError: {rpc_e}. Retrying in {retry_delay_seconds} seconds (Attempt {retries}/{max_retries})...")
                time.sleep(retry_delay_seconds)
        except Exception as e:
            retries += 1
            print(f"Vote for @{postingAccount}/{permlink} failed with an unexpected error: {e}. Retrying in {retry_delay_seconds} seconds (Attempt {retries}/{max_retries})...")
            time.sleep(retry_delay_seconds)

    if retries >= max_retries:
        print(f"Failed to vote for @{postingAccount}/{permlink} after {max_retries} attempts.")

def postReply (comment_item, ai_response_item, item_index, thothAccount, thothPermlink):
    """
    Posts a single AI summary as a reply to the main Thoth curation post.

    :param comment_item: dict, the comment data for the post being summarized.
    :param ai_response_item: str, the AI-generated summary for the comment_item.
    :param item_index: int, the 0-based index of this item from the original list (for display purposes).
    :param thothAccount: str, the author of the main Thoth curation post to reply to.
    :param thothPermlink: str, the permlink of the main Thoth curation post to reply to.
    """
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
| <h6>Unlocking #lifetime-rewards for Steem's creators</h6> |
| --- |


This post was generated with the assistance of the following AI model: <i>{config.get('ARLIAI','ARLIAI_MODEL')}</i>
    """
    display_index = item_index + 1 # Convert 0-based index to 1-based for display

    body += '<table border="1">\n'
    body += '   <tr>\n'
    body += f'     <td><b>Original Post Reference #</b></td>\n'
    body += f'     <td><b>Title</b></td>\n'
    body += f'     <td><b>Author</b></td>\n'
    body += f'  </tr><tr>\n'
    body += f'     <td>{display_index}</td>\n'
    body += f'     <td><a href="/thoth/@{comment_item["author"]}/{comment_item["permlink"]}">{repr(comment_item["title"])}</a></td>\n'
    body += f'     <td>{comment_item["author"]}</td>\n'
    body += f'   </tr>\n'
    body += f'</table>'
    body += f'<table><tr><td>\n\n{ai_response_item}\n\n' # Use the single ai_response_item
    body += '</td></tr></table><br><br>\n'

    body += f"<br>This Thoth instance is operated by {config.get('BLOG', 'THOTH_OPERATOR')}<br>\n"
    body += "<br>\n\nYou can contribute to Thoth or download your own copy of the code, [here](https://github.com/remlaps/Thoth)"

    # --- Beneficiary Calculation ---
    # For a single reply, there's always 1 author.
    num_authors_in_this_reply = 1
    
    # Calculate how many author slots (from the main post's potential count) are "freed up".
    # curatedPostCount and delegatorCount are module-level globals read from config.
    freed_author_slots = max(0, curatedPostCount - num_authors_in_this_reply)
    
    # Determine the total number of delegators to include for this reply.
    total_delegators_to_include_for_reply = delegatorCount + freed_author_slots
    
    all_delegators_list = []
    try:
        delegations = delegationInfo.get_delegations(postingAccount)
        if delegations: # Only shuffle if there are actual delegations
            all_delegators_list = delegationInfo.shuffled_delegators_by_weight(delegations)
    except Exception as e:
        print(f"Warning: Could not retrieve or shuffle delegators for reply: {e}")
        # all_delegators_list will remain empty

    adjustedDelegatorWeight = int( ( delegatorCount * delegatorWeight ) / min( total_delegators_to_include_for_reply, len(all_delegators_list) ))

    selected_delegators = all_delegators_list[:min(total_delegators_to_include_for_reply, len(all_delegators_list))]
    
    raw_beneficiaries_input = [postingAccount, f"a-{comment_item['author']}"] # Bot and original author
    for delegator_name in selected_delegators:
        raw_beneficiaries_input.append(f"d-{delegator_name}") # Add selected delegators
        
    beneficiaryList = create_beneficiary_list(raw_beneficiaries_input, curatedAuthorWeight, adjustedDelegatorWeight)
    author_account = [comment_item['author']]
    # selected_delegators is already defined above
    body += utils.generate_beneficiary_display_html(
        beneficiary_list=beneficiaryList,
        author_accounts=author_account,
        delegator_accounts=selected_delegators,
        thoth_account=postingAccount
    )

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

    # Generate a unique permlink for the reply before the retry loop
    # randValue is already generated at the beginning of the function
    sanitized_thoth_account_for_permlink = thothAccount.replace('@','').replace('.', '-').lower()
    reply_permlink = f"re-{sanitized_thoth_account_for_permlink}-{thothPermlink}-{randValue}"
    # A more descriptive title for logging purposes
    log_display_title = f"AI summary reply for post #{display_index} (to @{thothAccount}/{thothPermlink}, permlink: {reply_permlink})"

    print (f"Body: {body}")
    print (f"Body length:  {len(body)}")
    print (f"Tags: {taglist}")
    print (f"Beneficiaries: {beneficiaryList}")

    replyDone=False
    retryCount = 0
    while not replyDone and retryCount < 3:
        title = "" # Title for a reply is typically empty
        print(f"Attempting to post {log_display_title}")
        print(body)
        with open('data/fakepost.html', 'w', encoding='utf-8') as f:
            print(f"{body}", file=f)
        try:
            s.commit.post(title, body, postingAccount, permlink=reply_permlink, tags=taglist,
                comment_options=comment_options, json_metadata=metadata,
                beneficiaries=beneficiaryList, reply_identifier=f"@{thothAccount}/{thothPermlink}")
            replyDone = True
        except Exception as E:
            print (E)
            print ("Sleeping 1 minute before retry...")
            time.sleep(60)
            retryCount += 1
    if ( not replyDone ):
        print (f"Posting {log_display_title} failed after multiple retries. Exiting reply process.")
        return False
    
    # Vote on the newly created reply, not the parent post
    voting_thread = threading.Thread(target=vote_in_background, args=(postingAccount, reply_permlink, 100))
    voting_thread.daemon = True  # Allow main program to exit even if this thread is sleeping
    voting_thread.start()
    print (f"Reply {log_display_title} posted and vote scheduled in background.")
    return voting_thread # Return the thread object so it can be joined later