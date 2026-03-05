#!/usr/bin/env python3
"""
Test script for the hybrid screening system.
This script tests the rule-based constraints to ensure they take precedence over content scores.
"""

import sys
import os
import logging
from unittest.mock import Mock, MagicMock

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hybridScreening import HybridScreening
from configValidator import ConfigValidator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_mock_steem_instance():
    """Create a mock Steem instance for testing."""
    mock_steem = Mock()
    mock_steem.get_content = Mock(return_value={
        'author': 'testauthor',
        'permlink': 'test-permlink',
        'body': 'This is a test post with enough words to pass the minimum word count requirement. ' * 20,
        'title': 'Test Post Title',
        'json_metadata': '{"tags": ["test", "post"]}',
        'created': '2023-01-01T00:00:00',
        'net_votes': 10,
        'children': 5,
        'pending_payout_value': '10.000 SBD',
        'total_payout_value': '5.000 SBD',
        'author_reputation': 50,
        'last_vote_time': '2023-01-01T00:00:00',
        'last_post': '2023-01-01T00:00:00',
        'last_root_post': '2023-01-01T00:00:00'
    })
    return mock_steem

def create_mock_config():
    """Create a mock config validator for testing."""
    mock_config = Mock(spec=ConfigValidator)
    mock_config.get_int = Mock(side_effect=lambda section, key, fallback=0: {
        ('CONTENT', 'MIN_WORDS_HARD'): 100,
        ('AUTHOR', 'LAST_HIVE_ACTIVITY_AGE'): 60,
        ('AUTHOR', 'MIN_FOLLOWERS'): 350,
        ('AUTHOR', 'MIN_FOLLOWERS_PER_MONTH'): 10,
        ('AUTHOR', 'MIN_FOLLOWER_MEDIAN_REP'): 40,
        ('AUTHOR', 'MIN_REPUTATION'): 6,
        ('AUTHOR', 'MAX_INACTIVITY_DAYS'): 4000,
        ('AUTHOR', 'MAX_INCLUDED_POSTS_PER_AUTHOR'): 1,
        ('AUTHOR', 'FOLLOWER_HALFLIFE_YEARS'): 2,
        ('AUTHOR', 'MIN_ACTIVE_FOLLOWERS'): 10,
        ('AUTHOR', 'MAX_FOLLOWER_INACTIVITY_DAYS'): 90,
        ('ENGAGEMENT', 'VOTE_COUNT_MIN'): 10,
        ('ENGAGEMENT', 'VOTE_COUNT_MAX'): 200,
        ('ENGAGEMENT', 'COMMENT_MIN'): -10,
        ('ENGAGEMENT', 'COMMENT_MAX'): 20,
        ('ENGAGEMENT', 'RESTEEM_MIN'): 2,
        ('ENGAGEMENT', 'RESETEEM_MAX'): 20,
        ('ENGAGEMENT', 'ENGAGEMENT_THRESHOLD'): 5,
        ('SCORING', 'TIER_EXCELLENT_MIN'): 85.0,
        ('SCORING', 'TIER_GOOD_MIN'): 70.0,
        ('SCORING', 'TIER_FAIR_MIN'): 55.0,
        ('SCORING', 'TIER_POOR_MIN'): 40.0,
        ('SCORING', 'COMPONENT_AUTHOR_WEIGHT'): 40,
        ('SCORING', 'COMPONENT_CONTENT_WEIGHT'): 35,
        ('SCORING', 'COMPONENT_ENGAGEMENT_WEIGHT'): 25,
    }.get((section, key), fallback))
    mock_config.get_float = Mock(side_effect=lambda section, key, fallback=0.0: {
        ('ENGAGEMENT', 'VALUE_MIN'): 0.25,
        ('ENGAGEMENT', 'VALUE_MAX'): 100.0,
        ('ENGAGEMENT', 'COMMENT_WEIGHT'): 2.0,
        ('ENGAGEMENT', 'RESTEEM_WEIGHT'): 0.0,
        ('ENGAGEMENT', 'VALUE_WEIGHT'): 1.0,
        ('ENGAGEMENT', 'VOTE_COUNT_WEIGHT'): 1.0,
        ('SCORING', 'COMPONENT_AUTHOR_WEIGHT'): 0.40,
        ('SCORING', 'COMPONENT_CONTENT_WEIGHT'): 0.35,
        ('SCORING', 'COMPONENT_ENGAGEMENT_WEIGHT'): 0.25,
    }.get((section, key), fallback))
    return mock_config

def test_blacklisted_author():
    """Test that blacklisted authors are rejected regardless of content quality."""
    logger.info("Testing blacklisted author rule...")
    
    # Mock the isBlacklisted function to return True
    import authorValidation
    original_isBlacklisted = authorValidation.isBlacklisted
    authorValidation.isBlacklisted = Mock(return_value=True)
    
    try:
        mock_steem = create_mock_steem_instance()
        mock_config = create_mock_config()
        hybrid_screening = HybridScreening(mock_steem, mock_config)
        
        test_post = {
            'author': 'blacklisted_user',
            'permlink': 'test-post',
            'title': 'Excellent Quality Post',
            'timestamp': '2023-01-01T00:00:00'
        }
        
        result = hybrid_screening.screen_content(test_post)
        
        assert result['status'] == 'rejected', f"Expected rejected status, got {result['status']}"
        assert result['rule_type'] == 'blacklist', f"Expected blacklist rule type, got {result['rule_type']}"
        assert 'blacklisted_author' in result['reason'], f"Expected blacklisted_author in reason, got {result['reason']}"
        assert result['score_result'] is None, f"Expected no score result for blacklisted author, got {result['score_result']}"
        
        logger.info("✓ Blacklisted author test passed")
    finally:
        # Restore original function
        authorValidation.isBlacklisted = original_isBlacklisted

def test_whitelisted_author():
    """Test that whitelisted authors are accepted unless below hard minimum word count."""
    logger.info("Testing whitelisted author rule...")
    
    # Mock the isAuthorWhitelisted function to return True
    import authorValidation
    original_isAuthorWhitelisted = authorValidation.isAuthorWhitelisted
    authorValidation.isAuthorWhitelisted = Mock(return_value=True)
    
    try:
        mock_steem = create_mock_steem_instance()
        mock_config = create_mock_config()
        hybrid_screening = HybridScreening(mock_steem, mock_config)
        
        # Test whitelisted author with sufficient word count
        test_post = {
            'author': 'whitelisted_user',
            'permlink': 'test-post',
            'title': 'Whitelisted Author Post',
            'timestamp': '2023-01-01T00:00:00'
        }
        
        result = hybrid_screening.screen_content(test_post)
        
        assert result['status'] == 'accepted', f"Expected accepted status, got {result['status']}"
        assert result['rule_type'] == 'whitelist', f"Expected whitelist rule type, got {result['rule_type']}"
        assert 'whitelisted_author' in result['reason'], f"Expected whitelisted_author in reason, got {result['reason']}"
        
        logger.info("✓ Whitelisted author test passed")
    finally:
        # Restore original function
        authorValidation.isAuthorWhitelisted = original_isAuthorWhitelisted

def test_whitelisted_author_below_minimum():
    """Test that whitelisted authors are rejected if below hard minimum word count."""
    logger.info("Testing whitelisted author below minimum word count...")
    
    # Mock the isAuthorWhitelisted function to return True
    import authorValidation
    original_isAuthorWhitelisted = authorValidation.isAuthorWhitelisted
    authorValidation.isAuthorWhitelisted = Mock(return_value=True)
    
    # Mock the isTooShortHard function to return True (below minimum)
    import contentValidation
    original_isTooShortHard = contentValidation.isTooShortHard
    contentValidation.isTooShortHard = Mock(return_value=True)
    
    try:
        mock_steem = create_mock_steem_instance()
        mock_config = create_mock_config()
        hybrid_screening = HybridScreening(mock_steem, mock_config)
        
        test_post = {
            'author': 'whitelisted_user_short',
            'permlink': 'test-post',
            'title': 'Short Whitelisted Post',
            'timestamp': '2023-01-01T00:00:00'
        }
        
        result = hybrid_screening.screen_content(test_post)
        
        assert result['status'] == 'rejected', f"Expected rejected status, got {result['status']}"
        assert result['rule_type'] == 'whitelist_minimum', f"Expected whitelist_minimum rule type, got {result['rule_type']}"
        assert 'whitelisted_below_minimum_words' in result['reason'], f"Expected whitelisted_below_minimum_words in reason, got {result['reason']}"
        assert result['score_result'] is None, f"Expected no score result for whitelisted author below minimum, got {result['score_result']}"
        
        logger.info("✓ Whitelisted author below minimum test passed")
    finally:
        # Restore original functions
        authorValidation.isAuthorWhitelisted = original_isAuthorWhitelisted
        contentValidation.isTooShortHard = original_isTooShortHard

def test_hive_inactivity_rule():
    """Test that authors with recent Hive activity are rejected."""
    logger.info("Testing Hive inactivity rule...")
    
    # Mock the isHiveActivityTooRecent function to return True
    import authorValidation
    original_isHiveActivityTooRecent = authorValidation.isHiveActivityTooRecent
    authorValidation.isHiveActivityTooRecent = Mock(return_value=True)
    
    try:
        mock_steem = create_mock_steem_instance()
        mock_config = create_mock_config()
        hybrid_screening = HybridScreening(mock_steem, mock_config)
        
        test_post = {
            'author': 'recent_hive_user',
            'permlink': 'test-post',
            'title': 'Recent Hive Activity Post',
            'timestamp': '2023-01-01T00:00:00'
        }
        
        result = hybrid_screening.screen_content(test_post)
        
        assert result['status'] == 'rejected', f"Expected rejected status, got {result['status']}"
        assert result['rule_type'] == 'hive_inactivity', f"Expected hive_inactivity rule type, got {result['rule_type']}"
        assert 'recent_hive_activity' in result['reason'], f"Expected recent_hive_activity in reason, got {result['reason']}"
        assert result['score_result'] is None, f"Expected no score result for recent Hive activity, got {result['score_result']}"
        
        logger.info("✓ Hive inactivity rule test passed")
    finally:
        # Restore original function
        authorValidation.isHiveActivityTooRecent = original_isHiveActivityTooRecent

def test_word_count_rule():
    """Test that posts below hard minimum word count are rejected."""
    logger.info("Testing word count rule...")
    
    # Mock the isTooShortHard function to return True (below minimum)
    import contentValidation
    original_isTooShortHard = contentValidation.isTooShortHard
    contentValidation.isTooShortHard = Mock(return_value=True)
    
    try:
        mock_steem = create_mock_steem_instance()
        mock_config = create_mock_config()
        hybrid_screening = HybridScreening(mock_steem, mock_config)
        
        test_post = {
            'author': 'short_post_author',
            'permlink': 'test-post',
            'title': 'Short Post',
            'timestamp': '2023-01-01T00:00:00'
        }
        
        result = hybrid_screening.screen_content(test_post)
        
        assert result['status'] == 'rejected', f"Expected rejected status, got {result['status']}"
        assert result['rule_type'] == 'word_count', f"Expected word_count rule type, got {result['rule_type']}"
        assert 'below_minimum_words' in result['reason'], f"Expected below_minimum_words in reason, got {result['reason']}"
        assert result['score_result'] is None, f"Expected no score result for short post, got {result['score_result']}"
        
        logger.info("✓ Word count rule test passed")
    finally:
        # Restore original function
        contentValidation.isTooShortHard = original_isTooShortHard

def test_successful_screening():
    """Test that posts passing all rule-based checks proceed to scoring."""
    logger.info("Testing successful screening (passes rules, proceeds to scoring)...")
    
    # Mock all rule-based functions to return False (pass the checks)
    import authorValidation
    import contentValidation
    
    original_isBlacklisted = authorValidation.isBlacklisted
    original_isAuthorWhitelisted = authorValidation.isAuthorWhitelisted
    original_isHiveActivityTooRecent = authorValidation.isHiveActivityTooRecent
    original_isTooShortHard = contentValidation.isTooShortHard
    original_isEdit = contentValidation.isEdit
    original_hasBlacklistedTag = contentValidation.hasBlacklistedTag
    original_hasRequiredTag = contentValidation.hasRequiredTag
    
    authorValidation.isBlacklisted = Mock(return_value=False)
    authorValidation.isAuthorWhitelisted = Mock(return_value=False)
    authorValidation.isHiveActivityTooRecent = Mock(return_value=False)
    contentValidation.isTooShortHard = Mock(return_value=False)
    contentValidation.isEdit = Mock(return_value=False)
    contentValidation.hasBlacklistedTag = Mock(return_value=False)
    contentValidation.hasRequiredTag = Mock(return_value=True)
    
    try:
        mock_steem = create_mock_steem_instance()
        mock_config = create_mock_config()
        hybrid_screening = HybridScreening(mock_steem, mock_config)
        
        test_post = {
            'author': 'good_author',
            'permlink': 'test-post',
            'title': 'Good Quality Post',
            'timestamp': '2023-01-01T00:00:00'
        }
        
        result = hybrid_screening.screen_content(test_post)
        
        # Should proceed to scoring, so status depends on the score
        # The mock content should get a good score and be accepted
        assert result['status'] in ['accepted', 'score_rejected'], f"Expected accepted or score_rejected status, got {result['status']}"
        assert result['rule_type'] == 'hybrid', f"Expected hybrid rule type, got {result['rule_type']}"
        assert result['score_result'] is not None, f"Expected score result for post passing rules, got {result['score_result']}"
        assert result['quality_tier'] is not None, f"Expected quality tier, got {result['quality_tier']}"
        assert result['ai_intensity'] is not None, f"Expected AI intensity, got {result['ai_intensity']}"
        
        logger.info("✓ Successful screening test passed")
    finally:
        # Restore original functions
        authorValidation.isBlacklisted = original_isBlacklisted
        authorValidation.isAuthorWhitelisted = original_isAuthorWhitelisted
        authorValidation.isHiveActivityTooRecent = original_isHiveActivityTooRecent
        contentValidation.isTooShortHard = original_isTooShortHard
        contentValidation.isEdit = original_isEdit
        contentValidation.hasBlacklistedTag = original_hasBlacklistedTag
        contentValidation.hasRequiredTag = original_hasRequiredTag

def main():
    """Run all tests."""
    logger.info("Starting hybrid screening tests...")
    
    try:
        test_blacklisted_author()
        test_whitelisted_author()
        test_whitelisted_author_below_minimum()
        test_hive_inactivity_rule()
        test_word_count_rule()
        test_successful_screening()
        
        logger.info("All tests passed! ✓")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)