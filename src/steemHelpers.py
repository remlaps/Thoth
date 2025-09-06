import time
import requests
import configparser

from steem import Steem
from steem.blockchain import Blockchain

# Read the config.ini file
config = configparser.ConfigParser()
config.read('config/config.ini')

def initialize_steem_with_retry(node_api=None, max_retries=5, initial_delay=1.0):
    """
    Initializes the Steem instance with a retry mechanism for connection errors.
    """
    for attempt in range(max_retries):
        try:
            if node_api:
                s = Steem(node=node_api)
            else:
                s = Steem()

            # The Steem() constructor implicitly calls get_dynamic_global_properties(),
            # which is where the UnboundLocalError from the traceback can occur.
            # If we reach here, the connection was successful.
            if node_api:
                print(f"Successfully connected to Steem node: {node_api}")
            else:
                print("Successfully connected to default Steem node.")
            return s
        except UnboundLocalError as e:
            # This specific error from the traceback indicates a probable transient issue in steem-python http_client
            if "cannot access local variable 'error'" in str(e):
                wait_time = initial_delay * (2 ** attempt)
                print(f"Caught specific UnboundLocalError during Steem init (Attempt {attempt + 1}/{max_retries}). Retrying in {wait_time:.2f}s... Error: {e}")
                time.sleep(wait_time)
            else:
                # If it's a different UnboundLocalError, we don't want to retry, so re-raise.
                print(f"Caught an unexpected UnboundLocalError. This is not the target error for retry. Raising.")
                raise
        except Exception as e:
            wait_time = initial_delay * (2 ** attempt)
            print(f"Failed to initialize Steem (Attempt {attempt + 1}/{max_retries}). Retrying in {wait_time:.2f}s... Error: {e}")
            time.sleep(wait_time)

    print(f"FATAL: Could not initialize Steem after {max_retries} attempts.")
    return None

try:
    SDS_API = config.get('STEEM', 'SDS_API')
except (configparser.NoSectionError, configparser.NoOptionError):
    SDS_API = None
    print("SDS_API is not configured.")

def get_resteem_count(author, permlink):
    """
    Fetch the resteem count for a given post using the SDS/SteemWorld API.

    Args:
        author (str): The author of the post.
        permlink (str): The permlink of the post.

    Returns:
        int: The number of resteems for the post, or -1 if an error occurs.
    """

    if not SDS_API:
        print("SDS_API is not configured.")
        return 0
    
    url = f"{SDS_API}/post_resteems_api/getResteems/{author}/{permlink}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data["code"] == 0:
                return len(data["result"]["rows"])
            else:
                print(f"Error: API returned code {data['code']}")
        else:
            print(f"Error: HTTP {response.status_code} for {url}")
    except Exception as e:
        print(f"Error fetching resteem count: {e}")
    return 0