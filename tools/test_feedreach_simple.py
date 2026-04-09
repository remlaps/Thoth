#!/usr/bin/env python3
"""
Simple test script for feedReach implementation in Thoth content scoring system.
This script tests the basic structure without importing full modules.
"""

import sys
import os

def test_config_template():
    """Test that config template has the new feedReach parameters."""
    print("Testing config template...")
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.template')
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            
        # Check for new parameters in ENGAGEMENT section
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
                
        # Check that they're in the ENGAGEMENT section
        engagement_section = False
        found_params = 0
        
        for line in content.split('\n'):
            if line.strip() == '[ENGAGEMENT]':
                engagement_section = True
            elif line.strip().startswith('[') and line.strip() != '[ENGAGEMENT]':
                engagement_section = False
            elif engagement_section and any(param.split(' = ')[0] in line for param in required_params):
                found_params += 1
                
        if found_params == 3:
            print("✓ All feedReach parameters found in ENGAGEMENT section")
        else:
            print(f"✗ Only {found_params}/3 parameters found in ENGAGEMENT section")
            return False
                
        return True
    except Exception as e:
        print(f"✗ Error reading config template: {e}")
        return False

def test_community_validation_file():
    """Test that communityValidation.py file exists and has required functions."""
    print("\nTesting communityValidation.py file...")
    
    community_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'communityValidation.py')
    
    try:
        with open(community_file, 'r') as f:
            content = f.read()
            
        required_functions = [
            'def is_community_post(',
            'def get_community_tags(',
            'def get_all_community_members('
        ]
        
        for func in required_functions:
            if func in content:
                print(f"✓ Found {func}")
            else:
                print(f"✗ Missing {func}")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Error reading communityValidation.py: {e}")
        return False

def test_content_scoring_updates():
    """Test that contentScoring.py has the feedReach updates."""
    print("\nTesting contentScoring.py updates...")
    
    content_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'contentScoring.py')
    
    try:
        with open(content_file, 'r') as f:
            content = f.read()
            
        required_updates = [
            'from communityValidation import get_all_community_members',
            'getAllFollowers',
            'def _get_author_followers(',
            'def _get_resteem_followers(',
            'def _calculate_feed_reach(',
            'engagement_feed_reach',
            'FEED_REACH_WEIGHT'
        ]
        
        for update in required_updates:
            if update in content:
                print(f"✓ Found {update}")
            else:
                print(f"✗ Missing {update}")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Error reading contentScoring.py: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing feedReach implementation for Thoth")
    print("=" * 50)
    
    tests = [
        test_config_template,
        test_community_validation_file,
        test_content_scoring_updates
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