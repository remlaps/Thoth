#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import hybridScreening
from configValidator import ConfigValidator
import authorValidation
import contentValidation
import contentScoring

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
    # Mock the get_following method to avoid network calls
    mock_steem.get_following = Mock(return_value=[])
    return mock_steem

def create_mock_config():
    """Create a mock config validator for testing."""
    mock_config = Mock(spec=ConfigValidator)
    mock_config.get_int = Mock(side_effect=lambda section, key, fallback=0: {
        ('CONTENT', 'MIN_WORDS_HARD'): 100,
        ('AUTHOR', 'MIN_HIVE_INACTIVITY_HARD'): 7,
        ('AUTHOR', 'TARGET_HIVE_INACTIVITY_DAYS'): 60,
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
        ('ENGAGEMENT', 'RESTEEM_MAX'): 20,
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
        ('SCORING', 'MAX_HIVE_INACTIVITY_SCORE'): 10.0,
    }.get((section, key), fallback))
    mock_config.get = Mock(side_effect=lambda section, key, fallback='': {
        ('CONTENT', 'LANGUAGE'): 'en',
        ('BLOG', 'MIN_CURATION_TIER'): 'fair',
    }.get((section, key), fallback))
    return mock_config

def test_blacklisted_author():
    """Test that blacklisted authors are rejected regardless of content quality."""
    logger.info("Testing blacklisted author rule...")
    
    # Mock the isBlacklisted function to return True
    original_isBlacklisted = hybridScreening.isBlacklisted
    hybridScreening.isBlacklisted = Mock(return_value=True)
    
    # Mock the detect_language function to avoid errors
    original_detect_language = hybridScreening.detect_language
    hybridScreening.detect_language = Mock(return_value='en')
    
    # Mock the isEdit function to return False to avoid edit check interference
    original_isEdit = hybridScreening.isEdit
    hybridScreening.isEdit = Mock(return_value=False)
    
    # Mock tag checks to prevent them from triggering before blacklist (as they are now faster/earlier)
    original_hasBlacklistedTag = hybridScreening.hasBlacklistedTag
    original_hasRequiredTag = hybridScreening.hasRequiredTag
    hybridScreening.hasBlacklistedTag = Mock(return_value=False)
    hybridScreening.hasRequiredTag = Mock(return_value=True)
    
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
        
        # Get the full post content for testing
        full_post_content = mock_steem.get_content.return_value
        # Ensure the post data includes the body field and set last_update to avoid edit detection
        test_post_with_body = test_post.copy()
        test_post_with_body['body'] = full_post_content['body']
        test_post_with_body['last_update'] = full_post_content['created']  # Set last_update to created time to avoid edit detection
        # Also set updated to avoid edit detection
        test_post_with_body['updated'] = full_post_content['created']
        # Set last_vote_time to avoid edit detection
        test_post_with_body['last_vote_time'] = full_post_content['created']
        # Set last_root_post to avoid edit detection
        test_post_with_body['last_root_post'] = full_post_content['created']
        # Set last_post to avoid edit detection
        test_post_with_body['last_post'] = full_post_content['created']
        # Set author_reputation to avoid edit detection
        test_post_with_body['author_reputation'] = full_post_content['author_reputation']
        # Set timestamp to match created time to avoid edit detection
        test_post_with_body['timestamp'] = full_post_content['created']
        result = hybrid_screening.screen_content(test_post_with_body, latest_content=full_post_content)
        
        assert result['status'] == 'rejected', f"Expected rejected status, got {result['status']}"
        assert result['rule_type'] == 'blacklist', f"Expected blacklist rule type, got {result['rule_type']}"
        assert 'blacklisted_author' in result['reason'], f"Expected blacklisted_author in reason, got {result['reason']}"
        assert result['score_result'] is None, f"Expected no score result for blacklisted author, got {result['score_result']}"
        
        logger.info("✓ Blacklisted author test passed")
    finally:
        # Restore original functions
        hybridScreening.isBlacklisted = original_isBlacklisted
        hybridScreening.detect_language = original_detect_language
        hybridScreening.isEdit = original_isEdit
        hybridScreening.hasBlacklistedTag = original_hasBlacklistedTag
        hybridScreening.hasRequiredTag = original_hasRequiredTag

def test_whitelisted_author():
    """Test that whitelisted authors are accepted unless below hard minimum word count."""
    logger.info("Testing whitelisted author rule...")
    
    # Mock the isAuthorWhitelisted function to return True
    # Patch both the imported name and the source module to ensure it takes effect
    original_isAuthorWhitelisted_hybrid = hybridScreening.isAuthorWhitelisted
    original_isAuthorWhitelisted_author = authorValidation.isAuthorWhitelisted
    hybridScreening.isAuthorWhitelisted = Mock(return_value=True)
    authorValidation.isAuthorWhitelisted = Mock(return_value=True)

    # Mock fast checks to ensure we reach the whitelist check
    original_detect_language = hybridScreening.detect_language
    hybridScreening.detect_language = Mock(return_value='en')
    
    original_isEdit = hybridScreening.isEdit
    hybridScreening.isEdit = Mock(return_value=False)
    
    original_hasBlacklistedTag = hybridScreening.hasBlacklistedTag
    original_hasRequiredTag = hybridScreening.hasRequiredTag
    hybridScreening.hasBlacklistedTag = Mock(return_value=False)
    hybridScreening.hasRequiredTag = Mock(return_value=True)

    # Mock ContentScorer.score_content to prevent crashes if scoring is accidentally triggered
    original_score_content = contentScoring.ContentScorer.score_content
    contentScoring.ContentScorer.score_content = Mock(return_value={
        'total_score': 0.0, 'quality_tier': 'reject', 
        'components': {'author': 0, 'content': 0, 'engagement': 0}, 'ai_intensity': 'none'
    })
    
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
        hybridScreening.isAuthorWhitelisted = original_isAuthorWhitelisted_hybrid
        authorValidation.isAuthorWhitelisted = original_isAuthorWhitelisted_author
        contentScoring.ContentScorer.score_content = original_score_content
        hybridScreening.detect_language = original_detect_language
        hybridScreening.isEdit = original_isEdit
        hybridScreening.hasBlacklistedTag = original_hasBlacklistedTag
        hybridScreening.hasRequiredTag = original_hasRequiredTag

def test_whitelisted_author_below_minimum():
    """Test that whitelisted authors are rejected if below hard minimum word count."""
    logger.info("Testing whitelisted author below minimum word count...")
    
    # Mock the isAuthorWhitelisted function to return True
    original_isAuthorWhitelisted_hybrid = hybridScreening.isAuthorWhitelisted
    original_isAuthorWhitelisted_author = authorValidation.isAuthorWhitelisted
    hybridScreening.isAuthorWhitelisted = Mock(return_value=True)
    authorValidation.isAuthorWhitelisted = Mock(return_value=True)
    
    # Mock the isTooShortHard function to return True (below minimum)
    original_isTooShortHard_hybrid = hybridScreening.isTooShortHard
    original_isTooShortHard_content = contentValidation.isTooShortHard
    hybridScreening.isTooShortHard = Mock(return_value=True)
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
        
        # With the new logic, the word_count check runs first, so that's the rejection reason.
        assert result['status'] == 'rejected', f"Expected rejected status, got {result['status']}"
        assert result['rule_type'] == 'word_count', f"Expected word_count rule type, got {result['rule_type']}"
        assert 'below_minimum_words' in result['reason'], f"Expected below_minimum_words in reason, got {result['reason']}"
        assert result['score_result'] is None, f"Expected no score result for post below minimum, got {result['score_result']}"
        
        logger.info("✓ Whitelisted author below minimum test passed")
    finally:
        # Restore original functions
        hybridScreening.isAuthorWhitelisted = original_isAuthorWhitelisted_hybrid
        authorValidation.isAuthorWhitelisted = original_isAuthorWhitelisted_author
        hybridScreening.isTooShortHard = original_isTooShortHard_hybrid
        contentValidation.isTooShortHard = original_isTooShortHard_content

def test_hive_inactivity_rule():
    """Test that authors with recent Hive activity are rejected."""
    logger.info("Testing Hive inactivity rule...")
    
    # Mock the isHiveActivityTooRecent function to return True
    original_isHiveActivityTooRecent = hybridScreening.isHiveActivityTooRecent
    hybridScreening.isHiveActivityTooRecent = Mock(return_value=True)
    
    # --- Mock preceding checks to ensure this rule is reached ---
    original_detect_language = hybridScreening.detect_language
    hybridScreening.detect_language = Mock(return_value='en')
    
    original_isEdit = hybridScreening.isEdit
    hybridScreening.isEdit = Mock(return_value=False)
    
    original_hasBlacklistedTag = hybridScreening.hasBlacklistedTag
    original_hasRequiredTag = hybridScreening.hasRequiredTag
    hybridScreening.hasBlacklistedTag = Mock(return_value=False)
    hybridScreening.hasRequiredTag = Mock(return_value=True)
    
    original_isBlacklisted = hybridScreening.isBlacklisted
    hybridScreening.isBlacklisted = Mock(return_value=False)
    
    original_isAuthorWhitelisted = hybridScreening.isAuthorWhitelisted
    hybridScreening.isAuthorWhitelisted = Mock(return_value=False)
    
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
        hybridScreening.isHiveActivityTooRecent = original_isHiveActivityTooRecent
        hybridScreening.detect_language = original_detect_language
        hybridScreening.isEdit = original_isEdit
        hybridScreening.hasBlacklistedTag = original_hasBlacklistedTag
        hybridScreening.hasRequiredTag = original_hasRequiredTag
        hybridScreening.isBlacklisted = original_isBlacklisted
        hybridScreening.isAuthorWhitelisted = original_isAuthorWhitelisted

def test_word_count_rule():
    """Test that posts below hard minimum word count are rejected."""
    logger.info("Testing word count rule...")
    
    # Mock the isTooShortHard function to return True (below minimum)
    original_isTooShortHard = hybridScreening.isTooShortHard
    hybridScreening.isTooShortHard = Mock(return_value=True)
    
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
        hybridScreening.isTooShortHard = original_isTooShortHard

def test_successful_screening():
    """Test that posts passing all rule-based checks proceed to scoring."""
    logger.info("Testing successful screening (passes rules, proceeds to scoring)...")
    
    # Mock all rule-based functions to return False (pass the checks)
    # We patch the hybridScreening namespace which is what the class uses
    original_isBlacklisted = hybridScreening.isBlacklisted
    original_isAuthorWhitelisted = hybridScreening.isAuthorWhitelisted
    original_isHiveActivityTooRecent = hybridScreening.isHiveActivityTooRecent
    original_isTooShortHard = hybridScreening.isTooShortHard
    original_isEdit = hybridScreening.isEdit
    original_hasBlacklistedTag = hybridScreening.hasBlacklistedTag
    original_hasRequiredTag = hybridScreening.hasRequiredTag
    original_isAuthorPostLimitReached = hybridScreening.isAuthorPostLimitReached
    original_detect_language = hybridScreening.detect_language
    original_walletScreened = hybridScreening.walletScreened
    
    hybridScreening.isBlacklisted = Mock(return_value=False)
    hybridScreening.isAuthorWhitelisted = Mock(return_value=False)
    hybridScreening.isHiveActivityTooRecent = Mock(return_value=False)
    hybridScreening.isTooShortHard = Mock(return_value=False)
    hybridScreening.isEdit = Mock(return_value=False)
    hybridScreening.hasBlacklistedTag = Mock(return_value=False)
    hybridScreening.hasRequiredTag = Mock(return_value=True)
    hybridScreening.isAuthorPostLimitReached = Mock(return_value=False)
    hybridScreening.detect_language = Mock(return_value='en')
    hybridScreening.walletScreened = Mock(return_value=False)

    # Mock score_content to return a passing score to verify acceptance
    original_score_content = contentScoring.ContentScorer.score_content
    contentScoring.ContentScorer.score_content = Mock(return_value={
        'total_score': 90.0, 'quality_tier': 'excellent', 
        'components': {'author': 30, 'content': 30, 'engagement': 30}, 'ai_intensity': 'detailed'
    })
    
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
        hybridScreening.isBlacklisted = original_isBlacklisted
        hybridScreening.isAuthorWhitelisted = original_isAuthorWhitelisted
        hybridScreening.isHiveActivityTooRecent = original_isHiveActivityTooRecent
        hybridScreening.isTooShortHard = original_isTooShortHard
        hybridScreening.isEdit = original_isEdit
        hybridScreening.hasBlacklistedTag = original_hasBlacklistedTag
        hybridScreening.hasRequiredTag = original_hasRequiredTag
        hybridScreening.isAuthorPostLimitReached = original_isAuthorPostLimitReached
        hybridScreening.walletScreened = original_walletScreened
        hybridScreening.detect_language = original_detect_language
        contentScoring.ContentScorer.score_content = original_score_content

def test_author_post_limit_reached():
    """Test that authors are rejected when they reach the maximum number of included posts."""
    logger.info("Testing author post limit constraint...")
    
    # Mock the isAuthorPostLimitReached function to return True (limit reached)
    original_isAuthorPostLimitReached = hybridScreening.isAuthorPostLimitReached
    hybridScreening.isAuthorPostLimitReached = Mock(return_value=True)
    
    # Mock detect_language to prevent language filter from interfering
    original_detect_language = hybridScreening.detect_language
    hybridScreening.detect_language = Mock(return_value='en')

    # Mock isEdit to prevent edit check from interfering (and accessing missing body)
    original_isEdit = hybridScreening.isEdit
    hybridScreening.isEdit = Mock(return_value=False)

    try:
        mock_steem = create_mock_steem_instance()
        mock_config = create_mock_config()
        hybrid_screening = HybridScreening(mock_steem, mock_config)
        
        test_post = {
            'author': 'limit_reached_author',
            'permlink': 'test-post',
            'title': 'Post Beyond Limit',
            'timestamp': '2023-01-01T00:00:00',
            'body': 'Test body content'
        }
        
        # Create a mock included_posts list with one post from the same author
        included_posts = [
            {'author': 'limit_reached_author', 'permlink': 'first-post'}
        ]
        
        result = hybrid_screening.screen_content(test_post, included_posts=included_posts)
        
        assert result['status'] == 'rejected', f"Expected rejected status, got {result['status']}"
        assert result['rule_type'] == 'author_post_limit', f"Expected author_post_limit rule type, got {result['rule_type']}"
        assert 'max_posts_per_author_reached' in result['reason'], f"Expected max_posts_per_author_reached in reason, got {result['reason']}"
        assert result['score_result'] is None, f"Expected no score result for post limit reached, got {result['score_result']}"
        
        logger.info("✓ Author post limit test passed")
    finally:
        # Restore original function
        hybridScreening.isAuthorPostLimitReached = original_isAuthorPostLimitReached
        hybridScreening.detect_language = original_detect_language
        hybridScreening.isEdit = original_isEdit

def test_author_post_limit_not_reached():
    """Test that authors are allowed when they haven't reached the maximum number of included posts."""
    logger.info("Testing author post limit not reached...")
    
    # Mock the isAuthorPostLimitReached function to return False (limit not reached)
    original_isAuthorPostLimitReached = hybridScreening.isAuthorPostLimitReached
    hybridScreening.isAuthorPostLimitReached = Mock(return_value=False)

    # Mock detect_language to prevent language filter from interfering
    original_detect_language = hybridScreening.detect_language
    hybridScreening.detect_language = Mock(return_value='en')

    # Mock isEdit to prevent edit check from interfering
    original_isEdit = hybridScreening.isEdit
    hybridScreening.isEdit = Mock(return_value=False)

    # Mock walletScreened to prevent it from running real checks
    original_walletScreened = hybridScreening.walletScreened
    hybridScreening.walletScreened = Mock(return_value=False)
    
    try:
        mock_steem = create_mock_steem_instance()
        mock_config = create_mock_config()
        hybrid_screening = HybridScreening(mock_steem, mock_config)
        
        test_post = {
            'author': 'new_author',
            'permlink': 'test-post',
            'title': 'First Post',
            'timestamp': '2023-01-01T00:00:00',
            'body': 'Test body content'
        }
        
        # Create a mock included_posts list with posts from other authors
        included_posts = [
            {'author': 'other_author1', 'permlink': 'first-post'},
            {'author': 'other_author2', 'permlink': 'second-post'}
        ]
        
        result = hybrid_screening.screen_content(test_post, included_posts=included_posts)
        
        # Should proceed to scoring since post limit is not reached
        assert result['status'] in ['accepted', 'score_rejected'], f"Expected accepted or score_rejected status, got {result['status']}"
        assert result['rule_type'] == 'hybrid', f"Expected hybrid rule type, got {result['rule_type']}"
        assert result['score_result'] is not None, f"Expected score result for post not reaching limit, got {result['score_result']}"
        
        logger.info("✓ Author post limit not reached test passed")
    finally:
        # Restore original function
        hybridScreening.isAuthorPostLimitReached = original_isAuthorPostLimitReached
        hybridScreening.detect_language = original_detect_language
        hybridScreening.isEdit = original_isEdit
        hybridScreening.walletScreened = original_walletScreened

def main():
    """Run all tests."""
    logger.info("Starting hybrid screening tests...")

    # Mock external calls that would otherwise make network requests during scoring
    import contentScoring
    original_get_resteem_count = contentScoring.get_resteem_count
    contentScoring.get_resteem_count = Mock(return_value=5)

    try:
        test_blacklisted_author()
        test_whitelisted_author()
        test_whitelisted_author_below_minimum()
        test_hive_inactivity_rule()
        test_word_count_rule()
        test_successful_screening()
        test_author_post_limit_reached()
        test_author_post_limit_not_reached()
        
        logger.info("All tests passed! ✓")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False
    finally:
        # Restore original function to avoid side effects in other tests
        contentScoring.get_resteem_count = original_get_resteem_count

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)