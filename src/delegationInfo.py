import requests
import numpy as np
from decimal import Decimal, getcontext
import utils

# Create ONE high-quality RNG instance at module level with explicit entropy
_rng = utils.get_rng()

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
    Uses module-level numpy RNG for consistent entropy across calls.
    
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
    weights = [float(d[1]) for d in delegations]  # numpy needs float
    
    # Normalize weights to probabilities
    total_weight = sum(weights)
    probabilities = [w / total_weight for w in weights]
    
    # Select using module-level RNG
    selected_delegator = _rng.choice(delegators, p=probabilities)
    
    return selected_delegator

def shuffled_delegators_by_weight(delegations):
    """
    Returns delegators in random order, with probability of each position proportional to delegation size.
    Uses module-level numpy RNG for consistent high-quality entropy.
    
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
    
    # Convert VESTS values to Decimal for precise arithmetic, but keep a working copy for numpy
    remaining = [(d[0], Decimal(str(d[1])), float(d[1])) for d in delegations]  # (delegator, decimal_vests, float_vests)
    result = []
    
    while remaining:
        # Extract data for numpy operations
        delegators = [d[0] for d in remaining]
        float_weights = [d[2] for d in remaining]  # Use float weights for numpy
        
        # Normalize weights to probabilities
        total_weight = sum(float_weights)
        probabilities = np.array(float_weights) / total_weight
        
        # Use module-level RNG (consistent entropy across calls)
        selected_delegator = _rng.choice(delegators, p=probabilities)
        
        # Add the selected delegator to our result list
        result.append(selected_delegator)
        
        # Remove the selected delegator from the remaining list
        remaining = [d for d in remaining if d[0] != selected_delegator]
    
    return result