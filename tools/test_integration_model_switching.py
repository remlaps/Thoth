"""
Integration tests for model switching behavior.
Tests verify core model switching logic with minimal dependencies.
"""

import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from modelManager import ModelManager


def test_basic_switching():
    """Test basic model switching behavior."""
    print("\n=== Test: Basic model switching ===")
    
    mm = ModelManager("model-1,model-2,model-3")
    
    # Start with first model
    assert mm.current_model == "model-1"
    assert mm.has_next_model() == True
    assert mm.get_models_used() == ["model-1"]
    
    # Switch to second model
    switched = mm.mark_rate_limited(dry_run=False)
    assert switched == True
    assert mm.current_model == "model-2"
    assert mm.rate_limited_models == ["model-1"]
    assert mm.get_models_used() == ["model-1", "model-2"]
    
    # Switch to third model
    switched = mm.mark_rate_limited(dry_run=False)
    assert switched == True
    assert mm.current_model == "model-3"
    assert mm.rate_limited_models == ["model-1", "model-2"]
    assert mm.get_models_used() == ["model-1", "model-2", "model-3"]
    
    # Can't switch further
    switched = mm.mark_rate_limited(dry_run=False)
    assert switched == False
    assert mm.current_model == "model-3"
    assert mm.rate_limited_models == ["model-1", "model-2", "model-3"]
    
    print(f"  + Switched through all models")
    print(f"  + Final rate_limited: {mm.rate_limited_models}")
    print(f"  + get_models_used(): {mm.get_models_used()}")
    print("  PASSED")


def test_dry_run_mode():
    """Test dry-run mode (marks but doesn't switch)."""
    print("\n=== Test: Dry-run mode ===")
    
    mm = ModelManager("model-a,model-b,model-c")
    
    # Mark as rate-limited in dry-run mode
    switched = mm.mark_rate_limited(dry_run=True)
    assert switched == False
    assert mm.current_model == "model-a"  # Still on first
    assert mm.rate_limited_models == ["model-a"]  # But marked
    assert mm.has_next_model() == True  # Can still switch
    
    # Second dry-run on same model
    switched = mm.mark_rate_limited(dry_run=True)
    assert switched == False
    assert mm.current_model == "model-a"
    assert mm.rate_limited_models == ["model-a"]  # No duplicate
    
    # Now do a real switch
    switched = mm.mark_rate_limited(dry_run=False)
    assert switched == True
    assert mm.current_model == "model-b"
    assert mm.rate_limited_models == ["model-a"]
    
    print(f"  + Dry-run marked model: {mm.rate_limited_models}")
    print(f"  + Still on original model: {mm.current_model}")
    print(f"  + Real switch worked afterward")
    print("  PASSED")


def test_no_duplicates():
    """Test that rate_limited_models has no duplicates."""
    print("\n=== Test: No duplicates in rate_limited ===")
    
    mm = ModelManager("model-x,model-y")
    
    # Mark dry-run then real
    mm.mark_rate_limited(dry_run=True)
    assert mm.rate_limited_models == ["model-x"]
    
    mm.mark_rate_limited(dry_run=False)
    assert mm.rate_limited_models == ["model-x"]  # No duplicate
    assert mm.current_model == "model-y"
    
    # Mark y as rate-limited
    mm.mark_rate_limited(dry_run=False)
    assert mm.rate_limited_models == ["model-x", "model-y"]
    
    # Can't switch further
    mm.mark_rate_limited(dry_run=False)
    assert mm.rate_limited_models == ["model-x", "model-y"]  # Still no change
    
    print(f"  + No duplicates: {mm.rate_limited_models}")
    print("  PASSED")


def test_reset():
    """Test reset functionality."""
    print("\n=== Test: Reset ===")
    
    mm = ModelManager("a,b,c")
    
    mm.mark_rate_limited()
    mm.mark_rate_limited()
    assert mm.current_model == "c"
    assert mm.rate_limited_models == ["a", "b"]
    
    # Reset
    mm.reset()
    assert mm.current_model == "a"
    assert mm.rate_limited_models == []
    assert mm.get_models_used() == ["a"]
    
    print(f"  + Reset successful")
    print(f"  + Current: {mm.current_model}, Rate-limited: {mm.rate_limited_models}")
    print("  PASSED")


def test_single_model():
    """Test with a single model (no fallback)."""
    print("\n=== Test: Single model (no fallback) ===")
    
    mm = ModelManager("only-model")
    
    assert mm.current_model == "only-model"
    assert mm.has_next_model() == False
    
    switched = mm.mark_rate_limited()
    assert switched == False
    assert mm.current_model == "only-model"
    assert mm.rate_limited_models == ["only-model"]
    
    print(f"  + Single model handled correctly")
    print("  PASSED")


def test_get_models_used():
    """Test get_models_used() ordering."""
    print("\n=== Test: get_models_used() ordering ===")
    
    mm = ModelManager("first,second,third")
    
    # Initially just first
    assert mm.get_models_used() == ["first"]
    
    # After first failure, first is marked and second is current
    mm.mark_rate_limited()
    assert mm.get_models_used() == ["first", "second"]
    
    # After second failure
    mm.mark_rate_limited()
    assert mm.get_models_used() == ["first", "second", "third"]
    
    print(f"  + Models in correct order: {mm.get_models_used()}")
    print("  PASSED")


def test_whitespace_handling():
    """Test that whitespace in model names is handled."""
    print("\n=== Test: Whitespace handling ===")
    
    # Leading/trailing whitespace should be stripped
    mm = ModelManager("  model-1  ,  model-2  ,  model-3  ")
    
    assert mm.current_model == "model-1"
    assert len(mm.models) == 3
    assert mm.models == ["model-1", "model-2", "model-3"]
    
    mm.mark_rate_limited()
    assert mm.current_model == "model-2"
    
    print(f"  + Whitespace stripped correctly")
    print(f"  + Models: {mm.models}")
    print("  PASSED")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Integration Tests: Model Switching")
    print("="*60)
    
    try:
        test_basic_switching()
        test_dry_run_mode()
        test_no_duplicates()
        test_reset()
        test_single_model()
        test_get_models_used()
        test_whitespace_handling()
        
        print("\n" + "="*60)
        print("+ ALL INTEGRATION TESTS PASSED")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)