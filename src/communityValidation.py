import json
import logging
import urllib.request
import urllib.error
from steem import Steem

logger = logging.getLogger(__name__)

# SDS API endpoint for community queries
SDS_API_URL = "https://sds.steemworld.org"

def is_community_post(post):
    """
    Check if a post is in a community (category/first tag starts with 'hive-').
    
    In Steem, a post is in a community if its category (the first tag) starts with 'hive-'.
    The category is stored in the post's 'category' field.
    
    Args:
        post (dict): The post data from Steem API
        
    Returns:
        bool: True if the post is in a community, False otherwise
    """
    try:
        return get_community_category(post) is not None
    except Exception as e:
        logger.error(f"Error checking if post is in community: {e}")
        return False

def get_community_category(post):
    """
    Get the community category from a post if it's in a community.
    
    A post is in a community if its category (first tag) starts with 'hive-'.
    
    Args:
        post (dict): The post data from Steem API
        
    Returns:
        str or None: The community category if the post is in a community, None otherwise
    """
    try:
        # First check the 'category' field directly (this is the primary source)
        category = post.get('category', '')
        if category and category.startswith('hive-'):
            return category
        
        # Fallback: Check the first tag in json_metadata if category field is not set
        if post.get('json_metadata'):
            if isinstance(post['json_metadata'], dict):
                tags = post['json_metadata'].get('tags', [])
            elif isinstance(post['json_metadata'], str):
                try:
                    metadata = json.loads(post['json_metadata'])
                    tags = metadata.get('tags', [])
                except json.JSONDecodeError:
                    tags = []
            else:
                tags = []
            
            # Check if the first tag starts with 'hive-'
            if tags and tags[0].startswith('hive-'):
                return tags[0]
        
        return None
    except Exception as e:
        logger.error(f"Error extracting community category: {e}")
        return None

def get_community_members(community_tag, steem_instance=None):
    """
    Get community members for a given community tag using the SDS API.
    
    Args:
        community_tag (str): The community tag (e.g., 'hive-12345')
        steem_instance (Steem, optional): Steem instance to use (not used for SDS API)
        
    Returns:
        set: Set of community member account names
    """
    try:
        # Use SDS API to get community subscribers
        # API endpoint: https://sds.steemworld.org/communities_api/getCommunitySubscribers/community_tag
        api_url = f"{SDS_API_URL}/communities_api/getCommunitySubscribers/{community_tag}"
        
        # Create GET request
        req = urllib.request.Request(
            api_url,
            method='GET'
        )
        
        # Execute the request
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            # Check for errors in the response
            if result.get('code', 0) != 0:
                logger.warning(f"SDS API error for community {community_tag}: {result.get('message', 'Unknown error')}")
                return set()
            
            # Extract the result array
            subscribers = result.get('result', [])
            
            # Return as a set for efficient union operations
            return set(subscribers)
            
    except urllib.error.URLError as e:
        logger.warning(f"Failed to fetch community members for {community_tag}: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error getting community members for {community_tag}: {e}")
        return set()

def get_community_tags(post):
    """
    Extract community tags from a post (tags that start with 'hive-').
    
    Args:
        post (dict): The post data from Steem API
        
    Returns:
        list: List of community tags found in the post
    """
    try:
        community_tags = []
        
        # Get the community category (primary source)
        category = get_community_category(post)
        if category:
            community_tags.append(category)
        
        # Also check json_metadata for any additional community tags
        if post.get('json_metadata'):
            if isinstance(post['json_metadata'], dict):
                tags = post['json_metadata'].get('tags', [])
            elif isinstance(post['json_metadata'], str):
                try:
                    metadata = json.loads(post['json_metadata'])
                    tags = metadata.get('tags', [])
                except json.JSONDecodeError:
                    tags = []
            else:
                tags = []
            
            # Filter for community tags (those starting with 'hive-')
            additional_community_tags = [tag for tag in tags if tag.startswith('hive-') and tag != category]
            community_tags.extend(additional_community_tags)
        
        return community_tags
    except Exception as e:
        logger.error(f"Error extracting community tags: {e}")
        return []

def get_all_community_members(post, steem_instance=None):
    """
    Get all community members for a post that may be in multiple communities.
    
    Args:
        post (dict): The post data from Steem API
        steem_instance (Steem, optional): Steem instance to use
        
    Returns:
        set: Set of all community member account names
    """
    try:
        community_tags = get_community_tags(post)
        all_members = set()
        
        for community_tag in community_tags:
            members = get_community_members(community_tag, steem_instance)
            all_members.update(members)
        
        return all_members
    except Exception as e:
        logger.error(f"Error getting all community members: {e}")
        return set()
