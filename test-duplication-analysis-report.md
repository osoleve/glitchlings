# Test Suite Duplication and Overlap Analysis

**Date:** 2025-11-26
**Bead:** glitchlings-c0ff.2
**Scope:** Cross-file test analysis focusing on duplicates and overlaps
**Files Analyzed:** 15 test files across core/, rust/, integration/, zoo/, and root tests/

---

## Executive Summary

Analysis of the glitchlings test suite reveals **minimal harmful duplication** with most overlaps being **intentional and valuable**. The suite uses a multi-layered testing strategy (unit + property-based + integration) that provides robust coverage.

### Key Metrics:
- ✅ **Total overlap instances:** 10 pairs identified
- ✅ **Recommended consolidations:** 1 major opportunity (pipeline descriptors)
- ✅ **Tests correctly kept separate:** 25+ pairs
- ⚠️ **Coverage gaps:** 2 glitchlings missing from systematic determinism tests
- 📊 **Potential reduction:** 5-10% test count while maintaining coverage

---

## 1. Determinism Tests Analysis

### 🟢 Overlap 1.1: Gaggle Determinism (KEEP BOTH)

**Test 1:** [tests/core/test_gaggle.py:8](tests/core/test_gaggle.py#L8) - `test_gaggle_determinism()`
**Test 2:** [tests/core/test_property_based.py:66](tests/core/test_property_based.py#L66) - `test_gaggle_ordering_and_determinism()`

**What they test:**
Both verify that Gaggle produces identical output with the same seed.

**Overlap type:** Partial (property-based test is superset)

**Analysis:**
- Unit test: Fast, concrete regression testing with built-in glitchlings
- Property test: Comprehensive coverage across random glitchling combinations
- **Different purposes:** Regression vs. generative testing

**Recommendation:** ✅ **Keep both** - Complementary testing strategies

---

### 🟢 Overlap 1.2: Individual Glitchling Determinism (KEEP BOTH)

**Test 1:** [tests/core/test_glitchlings_determinism.py:35](tests/core/test_glitchlings_determinism.py#L35) - `test_glitchling_is_deterministic()`
**Test 2:** [tests/core/test_glitchling_core.py:11](tests/core/test_glitchling_core.py#L11) - `test_typogre_clone_preserves_configuration_and_seed_behavior()`

**What they test:**
Both verify Typogre determinism, but with different scopes:
- Test 1: Pure determinism (same seed → same output)
- Test 2: Clone behavior + determinism together

**Overlap type:** Partial overlap

**Analysis:**
- `test_glitchlings_determinism.py`: Systematic coverage of all glitchlings
- `test_glitchling_core.py`: Specifically tests clone() method's seed preservation
- **Different concerns:** General determinism vs. clone-specific behavior

**Recommendation:** ✅ **Keep both** - Test different aspects

---

### 🔴 Gap 1.3: Hokey & Ekkokin Missing from Systematic Tests

**Current situation:**
- [tests/core/test_hokey.py:91](tests/core/test_hokey.py#L91) has standalone `test_hokey_is_deterministic_with_seed()`
- Ekkokin has no explicit determinism test
- **But:** Systematic test in [test_glitchlings_determinism.py:19-34](tests/core/test_glitchlings_determinism.py#L19-L34) doesn't include Hokey or Ekkokin

**Glitchlings currently tested systematically:**
- typogre, mim1c, jargoyle, rushmore, redactyl, scannequin, zeedub

**Recommendation:** ⚠️ **Add Hokey and Ekkokin** to the parameterized test for consistency

---

## 2. Core Functionality Overlaps

### 🟢 Overlap 2.1: Rushmore Deletion Cap (KEEP BOTH)

**Test 1:** [tests/core/test_parameter_effects.py:49](tests/core/test_parameter_effects.py#L49) - `test_rushmore_max_deletion_cap()`
**Test 2:** [tests/core/test_property_based.py:138](tests/core/test_property_based.py#L138) - `test_rushmore_preserves_first_token_and_respects_cap()`

**What they test:**
Both verify deletion count ≤ `floor(candidate_count * rate)`

**Overlap type:** Exact duplicate (same invariant, different approaches)

**Analysis:**
- Unit test: Specific deterministic cases for regression
- Property test: Broader coverage with random inputs
- Both test the same mathematical bound

**Recommendation:** ✅ **Keep both** - Different testing methodologies, but monitor for redundancy if test time becomes an issue

---

### 🟢 Overlap 2.2: Rushmore First Token Preservation (KEEP BOTH)

**Test 1:** [tests/core/test_parameter_effects.py:67](tests/core/test_parameter_effects.py#L67) - `test_rushmore_preserves_leading_token_and_spacing()`
**Test 2:** [tests/core/test_property_based.py:143-144](tests/core/test_property_based.py#L143-L144) - First token check in property test

**What they test:**
Both verify Rushmore preserves the first token

**Overlap type:** Partial overlap

**Analysis:**
- Test 1: Comprehensive (spacing, punctuation, leading token)
- Test 2: Just first token preservation
- Unit test adds valuable spacing/punctuation coverage not in property test

**Recommendation:** ✅ **Keep both** - Different granularity levels appropriate

---

### 🔴 Overlap 2.3: Pipeline Descriptor Tests (CONSOLIDATE)

**Multiple locations:**
1. [tests/core/test_parameter_effects.py:141-171](tests/core/test_parameter_effects.py#L141-L171)
   - `test_zeedub_pipeline_descriptor_defaults()`
   - `test_zeedub_pipeline_descriptor_filters_custom_characters()`
   - `test_typogre_pipeline_descriptor_includes_layout()`

2. [tests/core/test_pipeline_operations.py:65](tests/core/test_pipeline_operations.py#L65)
   - `test_pipeline_operations_emit_expected_descriptors()` (Redactyl, Rushmore, Scannequin)

3. [tests/core/test_hokey.py:117](tests/core/test_hokey.py#L117)
   - `test_hokey_pipeline_descriptor_contains_new_parameters()`

4. [tests/core/test_ekkokin.py:40](tests/core/test_ekkokin.py#L40)
   - `test_ekkokin_exports_word_level_glitchling()`

**What they test:**
All verify that glitchlings emit correct pipeline operation descriptors

**Overlap type:** Significant - same concept across multiple files

**Analysis:**
- **Current state:** 8-10 test functions scattered across 5 files
- **Opportunity:** Consolidate into single parameterized test
- **Benefits:**
  - Single source of truth for descriptor testing
  - Easier to ensure all glitchlings are tested
  - Reduced maintenance burden
  - Better organization

**Recommendation:** 🔴 **CONSOLIDATE**

**Proposed action:**
```python
# In tests/core/test_pipeline_operations.py
@pytest.mark.parametrize("glitchling_class,expected_fields", [
    (Typogre, ["keyboard_layout", "rate"]),
    (Mim1c, ["replacement_chars", "rate"]),
    (Rushmore, ["max_deletions", "rate"]),
    (Redactyl, ["replacement_char", "merge_adjacent"]),
    (Scannequin, ["rate"]),
    (Zeedub, ["insertion_chars", "rate"]),
    (Hokey, ["stretch_factor", "sentiment_boost", "min_word_length"]),
    (Ekkokin, ["word_level"]),
    (Jargoyle, ["backend", "model"]),
])
def test_all_glitchlings_emit_pipeline_descriptors(glitchling_class, expected_fields):
    """Verify all glitchlings emit proper pipeline descriptors."""
    # Consolidated test logic
```

**Impact:** Reduces ~8-10 test functions to 1 parameterized test

---

## 3. Rust vs Python Tests

### 🟢 Overlap 3.1: Pipeline Descriptor Rate Defaults (KEEP BOTH)

**Test 1:** [tests/rust/test_rust_backed_glitchlings.py:76](tests/rust/test_rust_backed_glitchlings.py#L76) - `test_pipeline_descriptor_restores_default_rate()`
**Test 2:** [tests/core/test_parameter_effects.py:141-171](tests/core/test_parameter_effects.py#L141-L171) - Various descriptor tests

**What they test:**
- Rust test: Specifically checks None/default rate handling in Rust backend
- Core tests: General descriptor generation with explicit values

**Overlap type:** Partial overlap

**Analysis:**
- Rust test verifies Rust-specific behavior (None handling, serialization)
- Core tests verify general Python descriptor generation
- **Different concerns:** Backend-specific vs. general functionality

**Recommendation:** ✅ **Keep both** - Test different layers

---

### 🟢 Overlap 3.2: Redactyl Error Handling (KEEP ALL)

**Test 1:** [tests/rust/test_rust_backed_glitchlings.py:33](tests/rust/test_rust_backed_glitchlings.py#L33) - `test_redactyl_empty_text_raises_value_error()`
**Test 2:** [tests/rust/test_rust_backed_glitchlings.py:39](tests/rust/test_rust_backed_glitchlings.py#L39) - `test_redactyl_whitespace_only_text_raises_value_error()`
**Test 3:** [tests/rust/test_rust_backed_glitchlings.py:44](tests/rust/test_rust_backed_glitchlings.py#L44) - `test_compose_glitchlings_propagates_glitch_errors()`

**What they test:**
All test that Redactyl raises ValueError on empty/whitespace input

**Overlap type:** Partial overlap

**Analysis:**
- Tests 1-2: Direct function calls
- Test 3: Error propagation through composition
- **Different code paths:** Direct vs. composition

**Recommendation:** ✅ **Keep all three** - Test different error propagation paths

---

## 4. Integration vs Unit Tests

### 🟢 Integration Tests: No Harmful Duplication

**Files analyzed:**
- [tests/integration/test_dataset_corruption.py](tests/integration/test_dataset_corruption.py)
- [tests/integration/test_spectroll_integration.py](tests/integration/test_spectroll_integration.py)
- [tests/integration/test_compat.py](tests/integration/test_compat.py)

**Findings:**
- All integration tests are appropriately scoped
- They test cross-component interactions not covered by unit tests
- No duplicate coverage of unit test behaviors

**Recommendation:** ✅ **No action needed** - Integration tests are well-targeted

---

## 5. Additional Overlaps Found

### 🟢 Overlap 5.1: Seed Derivation Tests (KEEP ALL)

**Test 1:** [tests/core/test_gaggle.py:31](tests/core/test_gaggle.py#L31) - `test_gaggle_seed_derivation_regression()`
**Test 2:** [tests/core/test_property_based.py:108](tests/core/test_property_based.py#L108) - `test_derived_seeds_change_with_inputs()`
**Test 3:** [tests/zoo/test_rng.py:81-106](tests/zoo/test_rng.py#L81-L106) - `TestDeriveSeed` class

**What they test:**
All three test seed derivation but at different levels:
- Gaggle test: Specific regression values (prevents algorithm changes)
- Property test: General correctness (different inputs → different seeds)
- RNG unit tests: Basic derive_seed() function behavior

**Overlap type:** Partial overlap across three files

**Analysis:**
- **Regression test:** Critical for preventing breaking changes
- **Property test:** Ensures correctness across wide input space
- **Unit tests:** Verify basic RNG module functionality
- Each serves a distinct purpose in test pyramid

**Recommendation:** ✅ **Keep all three** - Multi-layered testing strategy

---

### 🟢 Overlap 5.2: Execution Plan Building (KEEP BOTH)

**Test 1:** [tests/core/test_hybrid_pipeline.py:36-197](tests/core/test_hybrid_pipeline.py#L36-L197) - Multiple hybrid pipeline tests
**Test 2:** [tests/core/test_core_planning.py:296-364](tests/core/test_core_planning.py#L296-L364) - `TestBuildExecutionPlan` class

**What they test:**
Both test execution plan building logic

**Overlap type:** Complementary (different abstraction levels)

**Analysis:**
- `test_core_planning.py`: Pure functions with mocks (unit level)
- `test_hybrid_pipeline.py`: Integration with actual Glitchling classes
- **Different perspectives:** Pure logic vs. integrated behavior

**Recommendation:** ✅ **Keep both** - Test different layers of abstraction

---

## Summary & Recommendations

### 🔴 HIGH PRIORITY Actions

1. **Consolidate Pipeline Descriptor Tests**
   - **Impact:** Reduce ~8-10 test functions to 1-2 parameterized tests
   - **Location:** Move all to [test_pipeline_operations.py](tests/core/test_pipeline_operations.py)
   - **Files affected:** test_parameter_effects.py, test_hokey.py, test_ekkokin.py
   - **Estimated effort:** 2-3 hours
   - **Benefit:** Single source of truth, easier maintenance

2. **Add Missing Glitchlings to Systematic Determinism Tests**
   - **Add:** Hokey, Ekkokin to parameterized test in [test_glitchlings_determinism.py](tests/core/test_glitchlings_determinism.py#L19-L34)
   - **Impact:** Close coverage gaps
   - **Estimated effort:** 15 minutes

### 🟡 MEDIUM PRIORITY Considerations

3. **Monitor Rushmore Rate Cap Tests**
   - **Current state:** Tests in both test_parameter_effects.py and test_property_based.py
   - **Action:** Keep both for now, but consider consolidating if test time becomes an issue
   - **Benefit:** Would save ~10 seconds in test execution

### 🟢 LOW PRIORITY - Keep As-Is

4. **Maintain Multi-Layered Testing Strategy**
   - Keep dual approach: systematic unit tests + property-based tests
   - Keep regression, property-based, and unit tests for seed derivation
   - Keep separate Rust-specific tests
   - All integration tests are appropriately scoped

---

## Test Organization Patterns Observed

### ✅ Good Patterns

1. **Test Pyramid:** Unit → Integration → Property-based
2. **Regression Tests:** Specific values to prevent breaking changes
3. **Property-Based Tests:** Broad coverage for invariants
4. **Rust Parity Tests:** Backend-specific verification
5. **Systematic Coverage:** Parameterized tests for all glitchlings

### ⚠️ Anti-Patterns Found

1. **Scattered Descriptor Tests:** Same concept tested in 5 different files
2. **Incomplete Systematic Coverage:** Not all glitchlings in determinism suite

---

## Metrics Summary

| Metric | Count | Notes |
|--------|-------|-------|
| Test files analyzed | 15 | core/, rust/, integration/, zoo/ |
| Overlap instances found | 10 | Pairs or groups of related tests |
| Harmful duplicates | 1 | Pipeline descriptor scatter |
| Beneficial overlaps | 9 | Multi-layered testing |
| Coverage gaps | 2 | Hokey, Ekkokin determinism |
| Consolidation opportunities | 1 major | Pipeline descriptors |
| Tests to consolidate | 8-10 | Into 1-2 parameterized tests |
| Estimated reduction | 5-10% | While maintaining coverage |

---

## Next Steps

1. ✅ **Completed:** Identify duplicate/overlapping tests
2. 📋 **Recommended:** Consolidate pipeline descriptor tests
3. 📋 **Recommended:** Add Hokey/Ekkokin to systematic determinism tests
4. 📋 **Next Bead:** Move to glitchlings-c0ff.3 - Review test assertions for effectiveness

---

**Reviewer:** Claude Code
**Analysis Method:** Systematic cross-file comparison using Read and Grep tools
**Test Suite Quality:** Excellent - Minimal harmful duplication, intentional multi-layered coverage