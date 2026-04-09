#!/usr/bin/env python3
"""
Test script for feedReach implementation in Thoth content scoring system.
This script tests the new feedReach functionality without making actual API calls.
"""

import sys
import os
import unittest.mock
from unittest.mock import Mock, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_feedreach_imports():
    """Test that all new modules can be imported correctly."""
    print("Testing imports...")
    
    try:
        # Test communityValidation import
        from communityValidation import is_community_post, get_community_tags, get_all_community_members
        print("✓ communityValidation imports successful")
        
        # Test contentScoring import with new functions
        from contentScoring import ContentScorer
        print("✓ contentScoring imports successful")
        
        # Test that getAllFollowers is imported
        from authorValidation import getAllFollowers
        print("✓ getAllFollowers import successful")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_config_template():
    """Test that config template has the new feedReach parameters."""
    print("\nTesting config template...")
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.template')
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            
        # Check for new parameters
        required_params = [
            'FEED_REACH_MIN = 10',
            'FEED_REACH_MAX = 10000', 
            'FEED_REACH_WEIGHT = 0.1'
        ]
        
        for param in required_params:
            if param in content:
                print(f"✓ Found {param}")
            else:
                print(f"✗ Missing {param}")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Error reading config template: {e}")
        return False

def test_content_scorer_initialization():
    """Test that ContentScorer can be initialized with feedReach support."""
    print("\nTesting ContentScorer initialization...")
    
    try:
        # Mock config
        mock_config = Mock()
        mock_config.get_float.return_value = 0.1
        mock_config.get_int.return_value = 100
        mock_config.get_boolean.return_value = False
        
        # Mock steem instance
        mock_steem = Mock()
        
        # Test initialization
        from contentScoring import ContentScorer
        scorer = ContentScorer(mock_steem, mock_config)
        
        # Check that feed_reach_weight is loaded
        assert 'engagement_feed_reach' in scorer.weights
        print("✓ ContentScorer initialization successful")
        print(f"✓ Feed reach weight: {scorer.weights['engagement_feed_reach']}")
        
        return True
    except Exception as e:
        print(f"✗ Error initializing ContentScorer: {e}")
        return False

def test_feedreach_calculation_methods():
    """Test that feedReach calculation methods exist and are callable."""
    print("\nTesting feedReach calculation methods...")
    
    try:
        # Mock config and steem
        mock_config = Mock()
        mock_config.get_float.return_value = 0.1
        mock_config.get_int.return_value = 100
        mock_config.get_boolean.return_value = False
        mock_steem = Mock()
        
        from contentScoring import ContentScorer
        scorer = ContentScorer(mock_steem, mock_config)
        
        # Check that the methods exist
        assert hasattr(scorer, '_get_author_followers')
        assert hasattr(scorer, '_get_resteem_followers')
        assert hasattr(scorer, '_calculate_feed_reach')
        
        print("✓ FeedReach calculation methods exist")
        
        # Test that _calculate_feed_reach can be called (with mocked dependencies)
        with unittest.mock.patch.object(scorer, '_get_author_followers', return_value={'user1', 'user2'}):
            with unittest.mock.patch.object(scorer, '_get_resteem_followers', return_value={'user3', 'user4'}):
                with unittest.mock.patch('communityValidation.get_all_community_members', return_value={'user5'}):
                    mock_post = {'author': 'test', 'permlink': 'test'}
                    feed_reach = scorer._calculate_feed_reach(mock_post)
                    
                    # Should be 5 unique accounts: user1, user2, user3, user4, user5
                    assert feed_reach == 5
                    print(f"✓ Feed reach calculation works: {feed_reach} unique accounts")
        
        return True
    except Exception as e:
        print(f"✗ Error testing feedReach calculation: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing feedReach implementation for Thoth")
    print("=" * 50)
    
    tests = [
        test_feedreach_imports,
        test_config_template,
        test_content_scorer_initialization,
        test_feedreach_calculation_methods
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! feedReach implementation is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == '__main__':
    sys.exit(main())