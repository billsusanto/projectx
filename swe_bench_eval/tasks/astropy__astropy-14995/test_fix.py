#!/usr/bin/env python
"""Test script to verify the mask propagation fix."""
import numpy as np
import sys
sys.path.insert(0, '/Users/billsusanto/Documents/Projects/projectx/swe_bench_eval/tasks/astropy__astropy-14995/repo')

from astropy.nddata import NDDataRef

# Test case 1: NDData with mask multiplied by scalar (no mask)
print("Test 1: NDData with mask multiplied by scalar...")
array = np.array([1, 2, 3])
mask = np.array([False, True, False])
nref_mask = NDDataRef(array, mask=mask)
nref_nomask = NDDataRef(array)

# This should work now
result1 = nref_mask.multiply(1., handle_mask=np.bitwise_or)
print(f"  Result mask: {result1.mask}")
print(f"  Expected mask: {mask}")
assert np.array_equal(result1.mask, mask), "Test 1 failed: mask not preserved"
print("  ✓ Test 1 passed!")

# Test case 2: Commutativity - nd1.multiply(nd2) should equal nd2.multiply(nd1)
print("\nTest 2: Testing commutativity...")
nd1 = NDDataRef(array, mask=mask)
nd2 = NDDataRef(array)

result_a = nd1.multiply(nd2, handle_mask=np.bitwise_or)
result_b = nd2.multiply(nd1, handle_mask=np.bitwise_or)

print(f"  nd1.multiply(nd2) mask: {result_a.mask}")
print(f"  nd2.multiply(nd1) mask: {result_b.mask}")
assert np.array_equal(result_a.mask, result_b.mask), "Test 2 failed: not commutative"
print("  ✓ Test 2 passed!")

# Test case 3: Both have masks
print("\nTest 3: Both operands have masks...")
mask1 = np.array([False, True, False])
mask2 = np.array([True, False, False])
nd3 = NDDataRef(array, mask=mask1)
nd4 = NDDataRef(array, mask=mask2)

result3 = nd3.multiply(nd4, handle_mask=np.bitwise_or)
expected_mask = mask1 | mask2
print(f"  Result mask: {result3.mask}")
print(f"  Expected mask: {expected_mask}")
assert np.array_equal(result3.mask, expected_mask), "Test 3 failed: mask OR incorrect"
print("  ✓ Test 3 passed!")

# Test case 4: Neither has mask
print("\nTest 4: Neither operand has mask...")
nd5 = NDDataRef(array)
nd6 = NDDataRef(array)

result4 = nd5.multiply(nd6, handle_mask=np.bitwise_or)
print(f"  Result mask: {result4.mask}")
assert result4.mask is None, "Test 4 failed: should have no mask"
print("  ✓ Test 4 passed!")

print("\n✅ All tests passed!")
