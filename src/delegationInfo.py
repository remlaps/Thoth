import requests
import random
from decimal import Decimal, getcontext

def get_delegations(account):
    """
    Get delegations for a Steem account.
    
    Args:
        account (str): The Steem account name to check delegations for
        
    Returns:
        list: A list of tuples (delegator, vests) showing all incoming delegations
    """
    url = f"https://sds1.steemworld.org/delegations_api/getIncomingDelegations/{account}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"API request failed with status code {response.status_code}")
    
    data = response.json()
    
    if data["code"] != 0:
        raise Exception(f"API returned error code {data['code']}")
    
    # Get column indices from the API response
    cols = data["result"]["cols"]
    from_index = cols["from"]
    vests_index = cols["vests"]
    
    delegations = []
    for row in data["result"]["rows"]:
        # Use the dynamically determined indices
        delegator = row[from_index]
        vests = row[vests_index]
        delegations.append((delegator, vests))
    
    return delegations

def random_delegator(delegations):
    """
    Randomly select a delegator with probability proportional to their delegated VESTS.
    
    Args:
        delegations (list): List of (delegator, vests) tuples returned by get_delegations()
        
    Returns:
        str: The randomly selected delegator account name
        
    Raises:
        ValueError: If the delegations list is empty
    """
    if not delegations:
        raise ValueError("No delegations available to select from")
    
    # Extract delegators and their VESTS
    delegators = [d[0] for d in delegations]
    vests = [d[1] for d in delegations]
    
    # Use random.choices with weights parameter for weighted random selection
    # This returns a list with one item, so we take the first element [0]
    selected_delegator = random.choices(
        population=delegators,
        weights=vests,
        k=1
    )[0]
    
    return selected_delegator

def shuffled_delegators_by_weight(delegations):
    """
    Returns delegators in random order, with probability of each position proportional to delegation size.
    
    Args:
        delegations (list): List of (delegator, vests) tuples returned by get_delegations()
        
    Returns:
        list: List of delegator account names in weighted random order
        
    Raises:
        ValueError: If the delegations list is empty
    """
    if not delegations:
        raise ValueError("No delegations available to shuffle")
    
    # Set precision high enough for our calculations
    getcontext().prec = 28
    
    # Convert VESTS values to Decimal for precise arithmetic
    remaining = [(d[0], Decimal(str(d[1]))) for d in delegations]
    result = []
    
    while remaining:
        # Calculate total VESTS of remaining delegations
        total_vests = sum(d[1] for d in remaining)
        
        # Generate a random point within the total VESTS range
        # Convert to float for random.uniform, then back to Decimal
        random_point = Decimal(str(random.uniform(0, float(total_vests))))
        
        # Find which delegator this point corresponds to
        cumulative = Decimal('0')
        selected_idx = 0
        
        for i, (_, vests) in enumerate(remaining):
            cumulative += vests
            if cumulative >= random_point:
                selected_idx = i
                break
        
        # Add the selected delegator to our result list
        result.append(remaining[selected_idx][0])
        
        # Remove the selected delegator from the remaining list
        remaining.pop(selected_idx)
    
    return result