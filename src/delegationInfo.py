import requests
import time
import random
import numpy as np
from decimal import Decimal, getcontext
import utils

# Create ONE high-quality RNG instance at module level with explicit entropy
_rng = utils.get_rng()

def removeExcludedDelegators(delegations, excluded_accounts):
    """
    Removes delegations from a list where the delegator is in the excluded list.

    Args:
        delegations (list): A list of (delegator, vests) tuples.
        excluded_accounts (list): A list of account names to exclude.

    Returns:
        list: A new list of delegations with excluded accounts removed.
    """
    if not excluded_accounts:
        return delegations
    
    # Use a set for efficient O(1) average time complexity lookups
    excluded_set = set(excluded_accounts)
    
    return [(delegator, vests) for delegator, vests in delegations if delegator not in excluded_set]

def get_delegations(account):
    """
    Get delegations for a Steem account.
    
    Args:
        account (str): The Steem account name to check delegations for
        
    Returns:
        list: A list of tuples (delegator, vests) showing all incoming delegations
    """
    url = f"https://sds1.steemworld.org/delegations_api/getIncomingDelegations/{account}"

    max_retries = 5
    initial_backoff = 1.0

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=10)

            # Retry on server errors or rate limiting
            if response.status_code == 429 or (500 <= response.status_code < 600):
                raise requests.exceptions.HTTPError(f"Server returned status {response.status_code}", response=response)

            if response.status_code != 200:
                # For other client errors, do not retry
                raise Exception(f"API request failed with status code {response.status_code}")

            data = response.json()
            break

        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            if attempt == max_retries:
                raise Exception(f"Failed to fetch delegations after {max_retries} attempts: {e}")
            backoff = initial_backoff * (2 ** (attempt - 1))
            # add jitter
            backoff = backoff + random.uniform(0, backoff * 0.1)
            print(f"get_delegations: request failed (attempt {attempt}/{max_retries}): {e}. Retrying in {backoff:.1f}s...")
            time.sleep(backoff)
            continue
    
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