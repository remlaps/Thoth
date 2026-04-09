#!/usr/bin/env python3
"""
Test script for feed reach screening functionality.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_feed_reach_screening():
    """Test that feed reach screening works correctly."""
    print("Testing feed reach screening...")
    
    try:
        from hybridScreening import HybridScreening
        from configValidator import ConfigValidator
        from steem import Steem
        
        # Create a mock config with feed reach screening enabled
        config = ConfigValidator()
        config.config['ENGAGEMENT'] = {
            'FEED_REACH_SCREENING_ENABLED': 'True',
            'FEED_REACH_MIN': '100',
            'FEED_REACH_MAX': '10000',
            'FEED_REACH_WEIGHT': '0.1'
        }
        
        # Create steem instance
        steem = Steem()
        
        # Create hybrid screening instance
        screening = HybridScreening(steem, config)
        
        # Test case 1: Post with low feed reach (should be rejected)
        post_low_reach = {
            'author': 'testauthor',
            'permlink': 'test-post',
            'body': 'This is a test post with low feed reach.',
            'title': 'Test Post',
            'author_reputation': 50,
            'net_votes': 5,
            'children': 2,
            'pending_payout_value': '0.000 SBD',
            'total_payout_value': '0.000 SBD',
            'category': 'test',
            'json_metadata': '{"tags": ["test"]}'
        }
        
        # Mock the content scorer to return low feed reach
        original_calculate_feed_reach = screening.content_scorer._calculate_feed_reach
        def mock_calculate_feed_reach(post):
            return 50  # Below minimum of 100
        
        screening.content_scorer._calculate_feed_reach = mock_calculate_feed_reach
        
        result = screening._apply_rule_based_screening(post_low_reach, post_low_reach, [])
        
        assert result['passed'] == False, f"Expected False, got {result['passed']}"
        assert result['rule_type'] == 'feed_reach_screening', f"Expected 'feed_reach_screening', got '{result['rule_type']}'"
        print("✓ Test 1 passed: Low feed reach post rejected")
        
        # Test case 2: Post with sufficient feed reach (should pass)
        def mock_calculate_feed_reach_high(post):
            return 200  # Above minimum of 100
        
        screening.content_scorer._calculate_feed_reach = mock_calculate_feed_reach_high
        
        result = screening._apply_rule_based_screening(post_low_reach, post_low_reach, [])
        
        assert result['passed'] == True, f"Expected True, got {result['passed']}"
        assert result['rule_type'] == 'rules_passed', f"Expected 'rules_passed', got '{result['rule_type']}'"
        print("✓ Test 2 passed: High feed reach post accepted")
        
        # Test case 3: Feed reach screening disabled (should pass regardless)
        config.config['ENGAGEMENT']['FEED_REACH_SCREENING_ENABLED'] = 'False'
        
        def mock_calculate_feed_reach_low(post):
            return 50  # Below minimum, but screening is disabled
        
        screening.content_scorer._calculate_feed_reach = mock_calculate_feed_reach_low
        
        result = screening._apply_rule_based_screening(post_low_reach, post_low_reach, [])
        
        assert result['passed'] == True, f"Expected True, got {result['passed']}"
        assert result['rule_type'] == 'rules_passed', f"Expected 'rules_passed', got '{result['rule_type']}'"
        print("✓ Test 3 passed: Feed reach screening disabled")
        
        # Restore original method
        screening.content_scorer._calculate_feed_reach = original_calculate_feed_reach
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing feed reach screening: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Testing feed reach screening for Thoth")
    print("=" * 50)
    
    if test_feed_reach_screening():
        print("\n🎉 All feed reach screening tests passed!")
        return 0
    else:
        print("\n❌ Feed reach screening tests failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())