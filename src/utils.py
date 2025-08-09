import langdetect
import configparser
import re
import authorValidation
import contentValidation
import walletValidation

from steem import Steem

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

def detect_language(text):
    try:
        return langdetect.detect(text)
    except langdetect.lang_detect_exception.LangDetectException:
        return "Unable to detect language"

def screenPost(comment):
    if ( contentValidation.isEdit (comment)):
        return "Post edit"
    
    if ( contentValidation.hasBlacklistedTag(comment)):
        return "Blacklisted tag in original version"
    
    latestComment=Steem().get_content(comment['author'],comment['permlink'])

    if ( contentValidation.hasBlacklistedTag(latestComment)):
        return "Blacklisted tag in latest revision."
    
    if ( not contentValidation.hasRequiredTag(latestComment)):
        return "Required tag missing"
    
    targetLanguage = [lang.strip() for lang in config.get('CONTENT', 'LANGUAGE').split(',') if lang]
    tmpBody=remove_formatting(latestComment['body'])
    bodyLanguage = detect_language(tmpBody)
    titleLanguage = detect_language(latestComment['title'])
    if not ( bodyLanguage in targetLanguage and titleLanguage in targetLanguage ):
        return f"Not a target language - body: {bodyLanguage}, title: {titleLanguage}"

    if ( authorValidation.isAuthorScreened(comment)):
        return "Author screened"
      
    if ( authorValidation.isAuthorWhitelisted(comment['author'])):
        return "Accept"
    
    whiteListRequired = config.get('CONTENT', 'WHITELIST_REQUIRED')
    if ( whiteListRequired == "True"):
        return ("Non-whitelisted author")
        
    ### Additional checks for non-whitelisted authors
    if ( contentValidation.isTooShort (tmpBody)):
        return "Too short"
    
    if ( contentValidation.hasTooManyTags (latestComment)):
        return "Too many tags"
    
    ### This is slow.  Screen everything else first.
    if ( walletValidation.walletScreened(comment['author'])):
        return "Wallet screened"
    
    ### Do this separately and last because it is VERY slow.
    if ( authorValidation.isActiveFollowerCountTooLow(comment['author'])):
        return "Follower count too low"
           
    return "Accept"

def remove_formatting(text):
    # Remove markdown and HTML formatting
    # Regex by AI (Brave Leo --> Llama )
    text = re.sub(r'^#{1,6} (.*)$', r'\1', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)
    text = re.sub(r'\!\[\]\(.*?\)', '', text)
    text = re.sub(r'!\w+\.\w+', '', text)  # Remove image labels
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'<!--.*?-->', '', text)  # Remove HTML comments
    text = re.sub(r'<script>.*?</script>', '', text)  # Remove HTML scripts
    text = re.sub(r'<style>.*?</style>', '', text)  # Remove HTML styles
    return text

def generate_beneficiary_display_html(beneficiary_list, author_accounts, delegator_accounts, thoth_account, columns=2):
    """
    Generates an HTML block to display beneficiaries, categorized by role.

    Args:
        beneficiary_list (list): The final list of beneficiary dicts [{'account': name, 'weight': w}, ...].
        author_accounts (list): A list of author account names.
        delegator_accounts (list): A list of delegator account names.
        thoth_account (str): The name of the bot/operator account.
        columns (int): The number of columns for the tables.

    Returns:
        str: The generated HTML string.
    """
    
    # Create a lookup map for weights for easy access
    beneficiary_weights = {b['account']: b['weight'] for b in beneficiary_list}
    null_account = 'null'
    
    def _generate_table_html(title, accounts, weights_map, gratitude_message=""):
        """Nested helper to generate a single HTML table."""
        # Filter for accounts that are actually in the final beneficiary list and have a weight > 0
        display_items = []
        for acc in accounts:
            if acc in weights_map and weights_map[acc] > 0:
                display_items.append({'account': acc, 'weight': weights_map[acc]})

        if not display_items:
            return ""

        # Sort alphabetically by account name
        display_items.sort(key=lambda x: x['account'])

        html = f"<h4>{title}</h4>\n"
        if gratitude_message:
            html += f'<p><i>{gratitude_message}</i></p>\n'
        html += "<table>\n"
        
        for i, item in enumerate(display_items):
            if i % columns == 0:
                html += "<tr>\n"
            
            percentage = item['weight'] / 100.0
            formatted_percentage = f"{percentage:g}" # Use :g to remove trailing .0
            html += f'   <td>{item["account"]} / {formatted_percentage}%</td>\n'
            
            if (i + 1) % columns == 0:
                html += "</tr>\n"
                
        # Fill remaining cells in the last row if it's not full
        remaining_cells = len(display_items) % columns
        if remaining_cells != 0:
            for _ in range(columns - remaining_cells):
                html += "   <td></td>\n"
            html += "</tr>\n"
            
        html += "</table>\n"
        return html

    # Start building the main HTML string
    body = f"\n\n<br><br><h3>Beneficiaries</h3>"

    # 1. Thoth Operator
    if thoth_account in beneficiary_weights and beneficiary_weights[thoth_account] > 0:
        percentage = beneficiary_weights[thoth_account] / 100.0
        formatted_percentage = f"{percentage:g}"
        body += f'<h4>Thoth Operator</h4>\n<p>{thoth_account} / {formatted_percentage}%</p>\n' # No @ sign

    # 2. Curated Authors
    unique_authors = sorted(list(set(author_accounts)))
    if unique_authors:
        author_title = "Curated Author" if len(unique_authors) == 1 else "Curated Authors"
        author_gratitude = "Thank you for creating the content that makes Steem a vibrant and interesting place. Your creativity is the foundation of our social ecosystem."
        body += _generate_table_html(author_title, unique_authors, beneficiary_weights, gratitude_message=author_gratitude)

    # 3. Delegators
    if delegator_accounts:
        delegator_title = "Delegator" if len(delegator_accounts) == 1 else "Delegators"
        delegator_gratitude = "Delegator support is crucial for the Thoth project's ability to find and reward attractive content. Thank you for investing in the Steem ecosystem and the Thoth project."
        body += _generate_table_html(delegator_title, delegator_accounts, beneficiary_weights, gratitude_message=delegator_gratitude)

    # 4. Burn Account (@null)
    if null_account in beneficiary_weights and beneficiary_weights[null_account] > 0:
        percentage = beneficiary_weights[null_account] / 100.0
        formatted_percentage = f"{percentage:g}"
        body += f'<h4>Burn Account</h4>\n<p>{null_account} / {formatted_percentage}%</p>\n'

    body += "<br><br>\n"
    return body

def get_steem_per_mvest(s: Steem) -> float:
    """
    Calculates the STEEM per MVEST ratio from the blockchain's global properties.
    This value is used to convert VESTS to Steem Power.
    """
    try:
        props = s.get_dynamic_global_properties()
        total_vesting_fund_steem = float(props['total_vesting_fund_steem'].split()[0])
        total_vesting_shares = float(props['total_vesting_shares'].split()[0])
        
        if total_vesting_shares == 0:
            return 0.0
            
        # The ratio is STEEM / VESTS, and we want it per Million VESTS (MVESTS)
        steem_per_mvest = (total_vesting_fund_steem / (total_vesting_shares / 1_000_000))
        return steem_per_mvest
    except Exception as e:
        print(f"Error fetching global properties: {e}")
        return 0.0
