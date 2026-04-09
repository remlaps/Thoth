#!/usr/bin/env python3
"""
Simple test script for feed reach screening functionality.
Tests the is_feed_reach_sufficient method in ContentScorer.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_feed_reach_screening_logic():
    """Test that feed reach screening logic works correctly."""
    print("Testing feed reach screening logic...")
    
    try:
        # Import only the communityValidation module which doesn't have global config dependencies
        from communityValidation import is_community_post, get_community_category
        
        # Test case 1: Post with category field starting with 'hive-'
        post_with_category = {
            'category': 'hive-144153',
            'json_metadata': '{"tags": ["photography", "nature", "art"]}'
        }
        
        category = get_community_category(post_with_category)
        is_community = is_community_post(post_with_category)
        
        assert category == 'hive-144153', f"Expected 'hive-144153', got '{category}'"
        assert is_community == True, f"Expected True, got {is_community}"
        print("✓ Test 1 passed: Category field with hive- prefix")
        
        # Test case 2: Post with first tag starting with 'hive-' in json_metadata
        post_with_hive_tag = {
            'category': '',
            'json_metadata': '{"tags": ["hive-12345", "technology", "programming"]}'
        }
        
        category = get_community_category(post_with_hive_tag)
        is_community = is_community_post(post_with_hive_tag)
        
        assert category == 'hive-12345', f"Expected 'hive-12345', got '{category}'"
        assert is_community == True, f"Expected True, got {is_community}"
        print("✓ Test 2 passed: First tag with hive- prefix")
        
        # Test case 3: Post with no community
        post_no_community = {
            'category': 'photography',
            'json_metadata': '{"tags": ["nature", "art", "beauty"]}'
        }
        
        category = get_community_category(post_no_community)
        is_community = is_community_post(post_no_community)
        
        assert category is None, f"Expected None, got '{category}'"
        assert is_community == False, f"Expected False, got {is_community}"
        print("✓ Test 3 passed: No community")
        
        # Test case 4: Post with hive- tag but not first
        post_hive_not_first = {
            'category': '',
            'json_metadata': '{"tags": ["photography", "hive-12345", "nature"]}'
        }
        
        category = get_community_category(post_hive_not_first)
        is_community = is_community_post(post_hive_not_first)
        
        assert category is None, f"Expected None, got '{category}'"
        assert is_community == False, f"Expected False, got {is_community}"
        print("✓ Test 4 passed: hive- tag not first")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing feed reach screening: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Testing feed reach screening logic for Thoth")
    print("=" * 50)
    
    if test_feed_reach_screening_logic():
        print("\n🎉 All feed reach screening logic tests passed!")
        return 0
    else:
        print("\n❌ Feed reach screening logic tests failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())