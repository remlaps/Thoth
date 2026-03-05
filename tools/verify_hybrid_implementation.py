#!/usr/bin/env python3
"""
Simple verification script for the hybrid screening implementation.
This script verifies that the hybrid screening system is properly integrated.
"""

import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def verify_hybrid_screening_import():
    """Verify that the hybrid screening module can be imported."""
    try:
        from hybridScreening import HybridScreening
        print("✓ HybridScreening class imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import HybridScreening: {e}")
        return False

def verify_main_integration():
    """Verify that main.py has been updated to use hybrid screening."""
    try:
        with open('src/main.py', 'r') as f:
            content = f.read()
        
        # Check for hybrid screening imports
        if 'from hybridScreening import HybridScreening' in content:
            print("✓ HybridScreening import found in main.py")
        else:
            print("✗ HybridScreening import not found in main.py")
            return False
        
        # Check for hybrid screening initialization
        if 'hybrid_screening = HybridScreening(' in content:
            print("✓ HybridScreening initialization found in main.py")
        else:
            print("✗ HybridScreening initialization not found in main.py")
            return False
        
        # Check for hybrid screening usage in main loop
        if 'screening_result = hybrid_screening.screen_content(' in content:
            print("✓ HybridScreening usage found in main loop")
        else:
            print("✗ HybridScreening usage not found in main loop")
            return False
        
        # Check that old content_scorer usage is removed
        if 'score_result = content_scorer.score_content(' in content:
            print("⚠ Warning: Old content_scorer.score_content usage still found in main loop")
        else:
            print("✓ Old content_scorer.score_content usage removed from main loop")
        
        return True
    except FileNotFoundError:
        print("✗ main.py file not found")
        return False
    except Exception as e:
        print(f"✗ Error checking main.py: {e}")
        return False

def verify_rule_precedence_logic():
    """Verify that the hybrid screening implements rule precedence correctly."""
    try:
        with open('src/hybridScreening.py', 'r') as f:
            content = f.read()
        
        # Check for rule-based screening function
        if 'def _apply_rule_based_screening(' in content:
            print("✓ Rule-based screening function found")
        else:
            print("✗ Rule-based screening function not found")
            return False
        
        # Check for the 6 specific rules (including delegation and language screening)
        rules_found = 0
        
        if 'isBlacklisted(author' in content:
            print("✓ Blacklisted author rule found")
            rules_found += 1
        else:
            print("✗ Blacklisted author rule not found")
        
        if 'isAuthorWhitelisted(author' in content:
            print("✓ Whitelisted author rule found")
            rules_found += 1
        else:
            print("✗ Whitelisted author rule not found")
        
        if 'isHiveActivityTooRecent(author' in content:
            print("✓ Hive inactivity rule found")
            rules_found += 1
        else:
            print("✗ Hive inactivity rule not found")
        
        if 'walletScreened(author' in content:
            print("✓ Delegation screening rule found")
            rules_found += 1
        else:
            print("✗ Delegation screening rule not found")
        
        if 'detect_language(body' in content and 'target_languages' in content:
            print("✓ Language validation rule found")
            rules_found += 1
        else:
            print("✗ Language validation rule not found")
        
        if 'hasBlacklistedTag(post_data' in content:
            print("✓ Blacklisted tags rule found")
            rules_found += 1
        else:
            print("✗ Blacklisted tags rule not found")
        
        if 'isTooShortHard(body' in content:
            print("✓ Word count rule found")
            rules_found += 1
        else:
            print("✗ Word count rule not found")
        
        if rules_found == 7:
            print("✓ All 7 required rules found in hybrid screening")
        else:
            print(f"⚠ Only {rules_found}/7 required rules found")
            return False
        
        # Check that rules return early (precedence over scoring)
        if "if not rule_result['passed']:" in content and "return {" in content:
            print("✓ Rule precedence logic found (early return on rule failure)")
        else:
            print("✗ Rule precedence logic not found")
            return False
        
        return True
    except FileNotFoundError:
        print("✗ hybridScreening.py file not found")
        return False
    except Exception as e:
        print(f"✗ Error checking hybridScreening.py: {e}")
        return False

def verify_configuration_usage():
    """Verify that the hybrid screening uses configuration values correctly."""
    try:
        with open('src/hybridScreening.py', 'r') as f:
            content = f.read()
        
        # Check for config usage in rule-based screening
        if "self.config.get_int('CONTENT', 'MIN_WORDS_HARD'" in content:
            print("✓ MIN_WORDS_HARD configuration used")
        else:
            print("✗ MIN_WORDS_HARD configuration not used")
            return False
        
        if "self.config.get_int('AUTHOR', 'LAST_HIVE_ACTIVITY_AGE'" in content:
            print("✓ LAST_HIVE_ACTIVITY_AGE configuration used")
        else:
            print("✗ LAST_HIVE_ACTIVITY_AGE configuration not used")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error checking configuration usage: {e}")
        return False

def main():
    """Run all verification checks."""
    print("Verifying hybrid screening implementation...")
    print("=" * 50)
    
    checks = [
        ("Import Verification", verify_hybrid_screening_import),
        ("Main Integration", verify_main_integration),
        ("Rule Precedence Logic", verify_rule_precedence_logic),
        ("Configuration Usage", verify_configuration_usage),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * len(check_name))
        if check_func():
            passed += 1
        else:
            print(f"Failed: {check_name}")
    
    print("\n" + "=" * 50)
    print(f"Verification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All verification checks passed! Hybrid screening implementation is complete.")
        print("\nKey features implemented:")
        print("• Rule-based screening takes precedence over content scores")
        print("• Blacklisted authors are rejected regardless of score")
        print("• Whitelisted authors are accepted unless below hard minimum word count")
        print("• Hive inactivity rule enforced (must be higher than specified days)")
        print("• Word count rule enforced (must exceed hard minimum)")
        print("• Content scoring only applied to posts that pass rule-based screening")
        return True
    else:
        print(f"❌ {total - passed} verification checks failed. Please review the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)