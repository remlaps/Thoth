from steem import Steem
from decimal import Decimal
import configparser

import utils

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config.ini file
config.read('config/config.ini')

steemApi = config.get('STEEM', 'STEEM_API')
s = Steem(node=steemApi) if steemApi else Steem()

screenedDelegateeFile = config.get('WALLET', 'SCREENED_DELEGATEE_FILE')
uncountedDelegateeFile = config.get('WALLET', 'UNCOUNTED_DELEGATEE_FILE')

def _get_thoth_incoming_delegations(author: str, steem_instance=None) -> list:
    """
    Fetches incoming delegations to a Thoth author.

    Args: the Steem account name of the author

    TechDebt: At some point, this should be changed to happen only once per program execution.

    Returns the total amount of vesting shares delegated to Thoth by the author.
    If the author makes no delegations, returns 0.
    """
    steemApi = config.get('STEEM', 'STEEM_API')
    s = steem_instance or (Steem(node=steemApi) if steemApi else Steem())
    thothAccount = config.get('STEEM', 'POSTING_ACCOUNT')
                              
    last_delegatee = None
    batch_size = 100
    is_first_batch = True
                              
    incomingVests = Decimal('0')

    while True:
        data = s.get_vesting_delegations(author, last_delegatee, batch_size)
        if not data:
            break

        start_idx = 0 if is_first_batch else 1
        is_first_batch = False

        for delegation in data[start_idx:]:
            delegatee = delegation['delegatee']
            vests_str = delegation['vesting_shares'].split(' ')[0]
            if delegatee == thothAccount:
                incomingVests = Decimal(vests_str) 
                break
            last_delegatee = delegatee

        if len(data) < batch_size:
            break

    print (f"Total incoming VESTS to Thoth from {author}: {incomingVests}")
    return incomingVests

def _get_account_vesting_info(author: str, steem_instance=None) -> tuple[float | None, float | None, float | None]:
    """
    Fetches and parses an account's total, delegated, and received vesting shares.

    Args:
        author: The Steem account name.

    Returns:
        A tuple of (vesting_shares, delegated_vesting_shares, received_vesting_shares) as floats,
        or (None, None, None) if the account is not found or data is missing.
    """
    steemApi = config.get('STEEM', 'STEEM_API')
    s = steem_instance or (Steem(node=steemApi) if steemApi else Steem())

    try:
        account = s.get_account(author)
        if not account:
            print(f"Warning: Account '{author}' not found.")
            return None, None, None

        vesting_shares = float(account.get('vesting_shares', '0.0 ').split()[0])
        delegated_vesting_shares = float(account.get('delegated_vesting_shares', '0.0 ').split()[0])
        received_vesting_shares = float(account.get('received_vesting_shares', '0.0 ').split()[0])

        thothDelegation = _get_thoth_incoming_delegations(author, steem_instance=s)
        delegated_vesting_shares -= float(thothDelegation)

        return vesting_shares, delegated_vesting_shares, received_vesting_shares

    except Exception as e:
        print(f"Error fetching vesting info for {author}: {e}")
        return None, None, None

def walletScreened(account, steem_instance=None):
    if not check_author_wallet(account, steem_instance=steem_instance):
        return True
    
    if _isPowerDownTooHigh(account, steemInstance=steem_instance):
        return True
    
    maxScreenedDelegationPct = config.getfloat('WALLET', 'MAX_SCREENED_DELEGATION_PCT')
    vesting_shares, _, _ = _get_account_vesting_info(account, steem_instance=steem_instance)
    if vesting_shares is None:
        # Account not found, cannot be screened.
        return True

    # The config value is a percentage (e.g., 15.0 for 15%).
    # The logic is to check if the percentage of screened delegations to total SP exceeds the threshold.
    screenedVests = totalScreenedOrIgnoredDelegations(account, delegateeFile=screenedDelegateeFile, steem_instance=steem_instance)
    
    # Avoid ZeroDivisionError if account has 0 SP.
    if vesting_shares == 0.0:  # Minimum vesting_shares was already checked by check_author_wallet.  At this point, 0 is ok.
        return False

    screened_percentage = (screenedVests / vesting_shares) * 100

    print (f"Vesting Shares: {vesting_shares:,.6f} VESTS")
    print (f"Screened Delegations: {screenedVests:,.6f} VESTS")
    print (f"Percentage screened: {screened_percentage:.2f}%")
    return screened_percentage > maxScreenedDelegationPct

def totalScreenedOrIgnoredDelegations (delegator, delegateeFile=screenedDelegateeFile, steem_instance=None) -> float:
    # Optimization: If the user has no delegated shares at all, we can exit early.
    _, delegated_vests_total, _ = _get_account_vesting_info(delegator, steem_instance=steem_instance)
    if delegated_vests_total is None or delegated_vests_total == 0.0:
        return 0.0
    
    steemApi = config.get('STEEM', 'STEEM_API')
    s = steem_instance or (Steem(node=steemApi) if steemApi else Steem())

    try:
        with open(delegateeFile, 'r') as f:
            screenedDelegatees = {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        print(f"Warning: Screened delegatee file not found at '{delegateeFile}'. Returning 0.")
        return 0.0

    total_vests = Decimal('0')
    last_delegatee = None
    batch_size = 100
    is_first_batch = True

    while True:
        data = s.get_vesting_delegations(delegator, last_delegatee, batch_size)
        if not data:
            break

        # For batches after the first, skip the first record (already seen)
        start_idx = 0 if is_first_batch else 1
        is_first_batch = False

        for delegation in data[start_idx:]:
            delegatee = delegation['delegatee']
            vests_str = delegation['vesting_shares'].split(' ')[0]
            if delegatee in screenedDelegatees:
                total_vests += Decimal(vests_str)
            last_delegatee = delegatee

        if len(data) < batch_size:
            break

    print (f"Delegator: {delegator}, total_vests: {total_vests}")
    return float(total_vests)

def _isPowerDownTooHigh(author: str, steemInstance=None) -> bool:
    """
    Checks if the author's yearly powerdown percentage exceeds the configured maximum.

    Args: 
        author: The Steem account name of the author

    Returns:
        True if the author's yearly powerdown percentage is above the limit, False otherwise.
    """

    maxPowerdownYearlyPct = config.getfloat('WALLET', 'MAX_POWERDOWN_YEARLY_PCT')

    if ( not steemInstance ):
        steemApi = config.get('STEEM', 'STEEM_API')
        s = Steem(node=steemApi) if steemApi else Steem()
    else:
        s = steemInstance

    try:
        authorAccountJson = s.get_account(author)
        if not authorAccountJson:
            print(f"Warning: Account '{author}' not found.")
            return False

        totalVests = float(authorAccountJson['vesting_shares'].split()[0])
        withdrawRate=float(authorAccountJson['vesting_withdraw_rate'].split()[0])

        yearlyPowerdownRate = 100 * withdrawRate * 52 / totalVests if totalVests > 0 else 0.0

        print(f"Yearly Powerdown Percentage for @{author}: {yearlyPowerdownRate:.2f}%")
        if yearlyPowerdownRate > maxPowerdownYearlyPct:
            print(f"FAIL: Yearly powerdown percentage ({yearlyPowerdownRate:.2f}%) exceeds max ({maxPowerdownYearlyPct:.2f}%).")
            return True

        print("PASS: Yearly powerdown percentage is below the limit.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while checking powerdown percentage: {e}")

    return False

def check_author_wallet(author: str, steem_instance=None) -> bool:
    """
    Checks an author's holdings against delegation and undelegated SP thresholds.

    Args:
        author: The Steem account name of the author.

    Returns:
        True if the author passes the screening, False otherwise.
    """
    try:
        max_delegation_pct = config.getfloat('WALLET', 'MAX_DELEGATION_PCT')
        min_undelegated_sp = config.getfloat('WALLET', 'MIN_UNDELEGATED_SP')
                
        # 1. Get account details using the new helper function
        vesting_shares, delegated_vesting_shares, _ = _get_account_vesting_info(author, steem_instance=steem_instance)
        if vesting_shares is None:
            # Error already printed in helper function
            return False

        unCountedVests = totalScreenedOrIgnoredDelegations(delegator=author, delegateeFile=uncountedDelegateeFile, steem_instance=steem_instance)
        delegationPenalty = delegated_vesting_shares - unCountedVests

        print(f"\n--- Checking author: @{author} ---")
        print(f"Vesting Shares: {vesting_shares:,.6f} VESTS")
        print(f"Delegated Vesting Shares: {delegated_vesting_shares:,.6f} VESTS")
        print(f"Uncounted Delegations: {unCountedVests:,.6f} VESTS")
        print(f"Delegation Penalty (after uncounted): {delegationPenalty:,.6f} VESTS")

        # 2. Calculate delegation percentage
        if vesting_shares > 0:
            delegation_percentage = (delegationPenalty / vesting_shares) * 100
        else:
            delegation_percentage = 0.0
        
        print(f"Delegation Percentage: {delegation_percentage:.2f}%")

        # 3. Calculate undelegated Steem Power (SP)
        steem_per_mvest = utils.get_steem_per_mvest(steem_instance)
        if steem_per_mvest == 0.0:
            return False # Stop if we can't get the conversion rate
            
        print(f"Current STEEM per MVEST: {steem_per_mvest:.6f}")

        undelegated_vests = vesting_shares - delegated_vesting_shares
        undelegated_sp = (undelegated_vests / 1_000_000) * steem_per_mvest
        print(f"Undelegated SP: {undelegated_sp:,.3f}")

        # 4. Screen based on the criteria
        print(f"\n--- Screening Criteria ---")
        print(f"Max Delegation Pct Threshold: {max_delegation_pct:.2f}%")
        print(f"Min Undelegated SP Threshold: {min_undelegated_sp:,.3f}")

        passes_screen = True
        if delegation_percentage > max_delegation_pct:
            print(f"FAIL: Delegation ({delegation_percentage:.2f}%) exceeds max ({max_delegation_pct:.2f}%).")
            passes_screen = False
        
        if undelegated_sp < min_undelegated_sp:
            print(f"FAIL: Undelegated SP ({undelegated_sp:,.3f}) is below min ({min_undelegated_sp:,.3f}).")
            passes_screen = False

        if passes_screen:
            print("\nPASS: Author meets all criteria.")
        
        return passes_screen

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
