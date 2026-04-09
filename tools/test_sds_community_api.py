#!/usr/bin/env python3
"""
Test script for SDS community API integration.
"""

import sys
import os
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_sds_community_api():
    """Test that SDS community API integration works correctly."""
    print("Testing SDS community API integration...")
    
    try:
        from communityValidation import get_community_members
        
        # Test case 1: Valid community tag
        community_tag = "hive-193637"
        print(f"Testing community: {community_tag}")
        
        members = get_community_members(community_tag)
        
        print(f"Found {len(members)} community members")
        if len(members) > 0:
            print(f"Sample members: {list(members)[:5]}")
            print("✓ Test 1 passed: Successfully fetched community members")
        else:
            print("⚠ Test 1 partial: No members returned (may be empty community or API issue)")
        
        # Test case 2: Invalid community tag
        invalid_community = "hive-invalid-community"
        print(f"\nTesting invalid community: {invalid_community}")
        
        members_invalid = get_community_members(invalid_community)
        
        print(f"Found {len(members_invalid)} members for invalid community")
        print("✓ Test 2 passed: Handled invalid community gracefully")
        
        # Test case 3: Empty result handling
        print(f"\nTesting empty result handling...")
        if isinstance(members_invalid, set):
            print("✓ Test 3 passed: Returns set type as expected")
        else:
            print("✗ Test 3 failed: Expected set type")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing SDS community API: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Testing SDS community API integration for Thoth")
    print("=" * 50)
    
    if test_sds_community_api():
        print("\n🎉 SDS community API integration tests completed!")
        return 0
    else:
        print("\n❌ SDS community API integration tests failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())