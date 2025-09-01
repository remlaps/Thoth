from steemHelpers import initialize_steem_with_retry
import configparser

# Read the config.ini file
config = configparser.ConfigParser()
config.read('config/config.ini')

validationApi=config.get('STEEM', 'STEEM_API')
steem = initialize_steem_with_retry(node_api=validationApi)
if not steem:
    exit(1) # Exit if Steem connection failed

commentMin = config.getint('ENGAGEMENT', 'COMMENT_MIN')
commentMax = config.getint('ENGAGEMENT', 'COMMENT_MAX')
commentWeight = config.getint('ENGAGEMENT', 'COMMENT_WEIGHT')
resteemMin = config.getint('ENGAGEMENT', 'RESTEEM_MIN')
resteemMax = config.getint('ENGAGEMENT', 'RESETEEM_MAX')
resteemWeight = config.getint('ENGAGEMENT', 'RESTEEM_WEIGHT')
valueMin = config.getfloat('ENGAGEMENT', 'VALUE_MIN')
valueMax = config.getfloat('ENGAGEMENT', 'VALUE_MAX')
valueWeight = config.getint('ENGAGEMENT', 'VALUE_WEIGHT')
voteCountMin = config.getint('ENGAGEMENT', 'VOTE_COUNT_MIN')
voteCountMax = config.getint('ENGAGEMENT', 'VOTE_COUNT_MAX')
voteCountWeight = config.getint('ENGAGEMENT', 'VOTE_COUNT_WEIGHT')
engagementThreshold = config.getfloat('ENGAGEMENT', 'ENGAGEMENT_THRESHOLD')

def scale(value, min_val, max_val):
    print (f"Scaling value: {value} with min: {min_val}, max: {max_val}")
    """Scale a value to a 0-100 range based on provided min and max."""
    if value <= min_val:
        return 0
    elif value >= max_val:
        return 100
    else:
        score = 100.0 * (value - min_val) / (max_val - min_val)
        print (f"  Scaled score: {score}")
        return int ( score )
    
def hasLowEngagement(comment):
    """Determine if a comment has low engagement based on configured thresholds."""

    fullComment = steem.get_content(comment['author'], comment['permlink'])

    voteCountScore = scale(fullComment['net_votes'], voteCountMin, voteCountMax) * voteCountWeight
    commentScore = scale(fullComment['children'], commentMin, commentMax) * commentWeight
    # Not sure how to get resteem count from the Steem python api.  The resteemedb_by field is empty.
    resteemScore = scale(fullComment['reblogged_by'] and len(fullComment['reblogged_by']) or 0, resteemMin, resteemMax) * resteemWeight
    postValue = float(fullComment["pending_payout_value"].split()[0])
    if ( postValue == 0.0 ):
        postValue = 2 * float(fullComment['curator_payout_value'].split()[0])

    valueScore = scale(postValue, valueMin, valueMax) * valueWeight
    valueScore = max(valueScore, 0 )

    print (f"Engagement for post {comment['author']}/{comment['permlink']}: "
           f"Votes: {fullComment['net_votes']} (Score: {voteCountScore}), "
           f"Comments: {fullComment['children']} (Score: {commentScore}), "
              f"Resteems: {fullComment['reblogged_by'] and len(fullComment['reblogged_by']) or 0} (Score: {resteemScore}), "
                f"Value: {postValue} (Score: {valueScore})")
    totalWeight = voteCountWeight + commentWeight + resteemWeight + valueWeight

    print (f"  Total Engagement Score: {(voteCountScore + commentScore + resteemScore + valueScore) / totalWeight:.2f} (Threshold: {engagementThreshold})") 

    if totalWeight == 0:
        return False # Avoid division by zero; consider no engagement if no weights are set
    else:
        engagementScore = int(0.5 + (voteCountScore + commentScore + resteemScore + valueScore) / totalWeight)

    return engagementScore < engagementThreshold