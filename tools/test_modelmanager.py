#!/usr/bin/env python3
# Quick test of ModelManager

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from modelManager import ModelManager

# Test 1: Single model
print("Test 1: Single model")
m1 = ModelManager('gemini-2.5-flash')
print(f"  Models: {m1.models}")
print(f"  Current: {m1.current_model}")
print(f"  Has next: {m1.has_next_model()}")

# Test 2: Multiple models
print("\nTest 2: Multiple models")
m2 = ModelManager('gemini-2.5-pro,gemini-2.5-flash,gemini-2.0-flash')
print(f"  Models: {m2.models}")
print(f"  Current: {m2.current_model}")
print(f"  Has next: {m2.has_next_model()}")
print(f"  Prefix: {m2.get_model_prefix()}")

# Test 3: Switching
print("\nTest 3: Switching models")
m3 = ModelManager('model-a,model-b,model-c')
print(f"  Starting with: {m3.current_model}")
m3.switch_to_next_model()
print(f"  After switch 1: {m3.current_model}")
m3.switch_to_next_model()
print(f"  After switch 2: {m3.current_model}")
print(f"  Has next: {m3.has_next_model()}")
result = m3.switch_to_next_model()
print(f"  Switch returned: {result}")

print("\nAll tests passed!")
