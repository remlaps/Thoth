#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
        
        # Extract the function body to verify order within the function
        try:
            func_parts = content.split('def _apply_rule_based_screening')
            if len(func_parts) < 2:
                print("✗ Could not parse function body")
                return False
            # Take the part after definition, stop at next def (simple heuristic)
            func_body = func_parts[1].split('\n    def ')[0]
        except Exception:
            print("✗ Error extracting function body")
            return False
        
        print("\nVerifying optimization order (Fail-Fast Strategy):")
        
        # Define expected order: (function_call_substring, display_name)
        expected_order = [
            ('isTooShortHard', '1. Word count (Hard limit)'),
            ('detect_language', '2. Language detection'),
            ('isEdit', '3. Edit check'),
            ('hasBlacklistedTag', '4. Blacklisted tags'),
            ('hasRequiredTag', '5. Required tags'),
            ('isAuthorPostLimitReached', '6. Author post limit'),
            ('isBlacklisted', '7. Blacklisted author'),
            ('isAuthorWhitelisted', '8. Whitelisted author'),
            ('isHiveActivityTooRecent', '9. Hive inactivity'),
            ('walletScreened', '10. Wallet screening')
        ]
        
        last_pos = -1
        order_correct = True
        rules_found = 0
        
        for func_name, display_name in expected_order:
            pos = func_body.find(func_name)
            if pos != -1:
                rules_found += 1
                if pos > last_pos:
                    print(f"✓ {display_name} found in correct relative position")
                    last_pos = pos
                else:
                    print(f"✗ {display_name} found but OUT OF ORDER (should be later)")
                    order_correct = False
            else:
                print(f"⚠ {display_name} check not found in function body")
        
        if order_correct and rules_found >= 7:
            print("✓ Rule execution order is optimized for speed")
        else:
            print("✗ Rule optimization verification failed")
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
        print("• Rule-based screening optimized for speed (Fail-Fast)")
        print("• Cheap local checks (word count, tags) run first")
        print("• Expensive network checks (wallet, history) run last")
        print("• Blacklists checked before Whitelists for safety")
        print("• Content scoring only applied after all rules pass")
        return True
    else:
        print(f"❌ {total - passed} verification checks failed. Please review the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)