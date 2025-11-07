# GlitchOp Buffer Refactoring Audit

## Overview
This document provides a comprehensive audit of all `GlitchOp` implementations in the rust/zoo crate, identifying which operations use direct buffer segment methods vs. those that reparse the buffer via `buffer.to_string()` + `TextBuffer::from_owned()`.

**Audit Date:** 2025-11-07 (Updated after Milestones 1-6, Final)
**Goal:** Eliminate all `buffer.to_string()` / `TextBuffer::from_owned()` patterns within GlitchOp implementations to avoid redundant reparsing where architecturally feasible.

**Status:** ✅ Milestones 1-6 Complete - 10/14 operations refactored (71% complete)
**Remaining:** 4 operations documented as requiring full-text operations due to architectural constraints

---

## Implementation Status

### ✅ Already Using Segment Methods Correctly (No Reparse)

#### 1. ReduplicateWordsOp
**Location:** `rust/zoo/src/glitch_ops.rs:207-285`
**Status:** ✅ Good (Original)
**Pattern:** Uses `buffer.word_segment()`, `buffer.replace_word()`, `buffer.insert_word_after()`
**Notes:** This is the canonical example of proper segment-based operations.

#### 2. SwapAdjacentWordsOp
**Location:** `rust/zoo/src/glitch_ops.rs:378-436`
**Status:** ✅ Good (Original)
**Pattern:** Uses `buffer.word_segment()`, `buffer.replace_words_bulk()`
**Notes:** Efficient bulk replacement pattern. Good example.

#### 3. RushmoreComboOp
**Location:** `rust/zoo/src/glitch_ops.rs:438-493`
**Status:** ✅ Good (Original)
**Pattern:** Delegates to other ops
**Notes:** No direct buffer manipulation, just orchestration.

#### 4. RedactWordsOp ⭐ REFACTORED
**Location:** `rust/zoo/src/glitch_ops.rs:495-605`
**Status:** ✅ **REFACTORED** (Milestone 2)
**Before:** Lines 595-605 used regex-based merging with reparse
**After:** Now uses `buffer.merge_repeated_char_words()` (line 596)
**Impact:** Eliminated conditional reparsing path, 10 lines of regex code removed

#### 5. EkkokinOp ⭐ REFACTORED
**Location:** `rust/zoo/src/ekkokin.rs:148-208`
**Status:** ✅ **REFACTORED** (Milestone 4)
**Before:** Lines 150-198 used `split_with_separators()` + `concat()` + reparse
**After:** Now uses segment-based iteration with `buffer.word_segment()` and `buffer.replace_words_bulk()`
**Impact:**
- Eliminated split_with_separators pattern entirely
- No more `to_string()` + `from_owned()` round-trip
- Uses efficient bulk update for all replacements
- Removed unused import

#### 6. SpectrollOp ⭐ REFACTORED
**Location:** `rust/zoo/src/spectroll.rs:270-318`
**Status:** ✅ **REFACTORED** (Milestone 6)
**Before:** Used regex on full text, rebuilt string with color replacements
**After:** Segment-based iteration with regex per segment, uses `buffer.replace_words_bulk()`
**Impact:** Eliminated 7 lines of reparse code

#### 7. Mim1cOp ⭐ REFACTORED
**Location:** `rust/zoo/src/mim1c.rs:90-198`
**Status:** ✅ **REFACTORED** (Milestone 6)
**Before:** Converted to string, found char_indices, rebuilt with character replacements
**After:** Segment-based with (seg_idx, char_offset, char) tracking, uses `buffer.replace_segments_bulk()`
**Impact:** Eliminated 15 lines of reparse code

#### 8. OcrArtifactsOp ⭐ REFACTORED
**Location:** `rust/zoo/src/glitch_ops.rs:614-713`
**Status:** ✅ **REFACTORED** (Milestone 6)
**Before:** Full text string matching for confusion patterns
**After:** Segment-based pattern matching, groups replacements by segment
**Impact:** Eliminated ~12 lines of reparse code, preserves Fisher-Yates shuffle

#### 9. QuotePairsOp ⭐ REFACTORED
**Location:** `rust/zoo/src/glitch_ops.rs:1135-1243`
**Status:** ✅ **REFACTORED** (Milestone 6)
**Before:** Full text quote pair detection and replacement
**After:** Global position mapping to segment positions, batch segment updates
**Impact:** Eliminated ~10 lines of reparse code

#### 10. ZeroWidthOp ⭐ REFACTORED
**Location:** `rust/zoo/src/glitch_ops.rs:716-834`
**Status:** ✅ **REFACTORED** (Milestone 6)
**Before:** Full text char-level insertion tracking
**After:** Segment-based (seg_idx, char_idx) position tracking with bulk updates
**Impact:** Eliminated ~10 lines of reparse code

---

### 🟡 Requiring Full-Text Operations (Documented as Special Cases)

These operations require full-text operations due to their architectural characteristics and cannot be efficiently refactored to use segment-based operations without fundamentally changing their design.

#### 11. DeleteRandomWordsOp
**Location:** `rust/zoo/src/glitch_ops.rs:287-378`
**Status:** 🟡 **REQUIRES REPARSING** (Re-evaluated after test failure)
**Reparse Locations:**
- Line 370: `let mut joined = buffer.to_string();`
- Lines 371-375: Regex-based cleanup and trimming
- Line 376: `*buffer = TextBuffer::from_owned(final_text);`

**Pattern:** Deletes word cores while preserving punctuation affixes
**Rationale:** After deleting word cores and keeping only punctuation affixes (e.g., "beta;" → ";"), the operation creates Word segments containing only punctuation marks. Proper spacing normalization requires re-tokenization to merge adjacent punctuation into coherent separators. Attempted refactoring with `normalize()` caused test failures (`test_rushmore_preserves_leading_token_and_spacing`) because `normalize()` doesn't re-tokenize the modified segments, leaving multiple adjacent Word segments with punctuation and trailing spaces.

#### 12. HokeyOp
**Location:** `rust/zoo/src/hokey.rs:574-628`
**Status:** 🟡 **DOCUMENTED AS SPECIAL CASE**
**Reparse Locations:**
- Line 576: `let text = buffer.to_string();`
- Line 581: `let tokens = self.tokenise(&text);` (custom regex-based tokenizer)
- Line 625: `*buffer = TextBuffer::from_owned(result);`

**Pattern:** Custom regex tokenization with clause tracking, linguistic features, and metadata
**Rationale:** Uses custom tokenization that differs from TextBuffer's segmentation, tracks clause boundaries, computes lexical/POS/sentiment/phonotactic features. The custom tokenization is essential to the operation's semantics, not redundant reparsing.

#### 13. PedantOp
**Location:** `rust/zoo/src/pedant.rs:89-114`
**Status:** 🟡 **DOCUMENTED AS SPECIAL CASE**
**Reparse Locations:**
- Line 95: `let original = buffer.to_string();`
- Line 109: `*buffer = TextBuffer::from_owned(transformed);`

**Pattern:** Multiple regex-based whole-text linguistic transformations (8 variants)
**Rationale:** Applies context-aware linguistic transformations (whomst, fewerling, aetheria, apostrofae, subjunic, commama, kiloa, correctopus) that require seeing full text context for semantic correctness. These are legitimate linguistic operations, not redundant parsing.

#### 14. TypoOp
**Location:** `rust/zoo/src/glitch_ops.rs:836-1095`
**Status:** 🟡 **DOCUMENTED AS SPECIAL CASE**
**Reparse Locations:**
- Line 994: `let text = buffer.to_string();`
- Line 1008: `let mut chars: Vec<char> = text.chars().collect();`
- Line 1092: `*buffer = TextBuffer::from_owned(chars.into_iter().collect());`

**Pattern:** Vec<char> in-place mutations with 8 action types crossing segment boundaries
**Rationale:** Operations fundamentally require flat character array with in-place mutations (swap chars, remove/insert spaces, repeat chars, collapse duplicates). These operations cross segment boundaries and modify separator structure itself, making segment-based operations architecturally incompatible.

---

## Summary Statistics

### Before Refactoring (Baseline)
| Status | Count | Operations |
|--------|-------|-----------|
| ✅ Good | 3 | ReduplicateWordsOp, SwapAdjacentWordsOp, RushmoreComboOp |
| ⚠️ Partial | 2 | DeleteRandomWordsOp, RedactWordsOp |
| 🔴 Full Reparse | 9 | EkkokinOp, HokeyOp, PedantOp, OcrArtifactsOp, ZeroWidthOp, TypoOp, QuotePairsOp, Mim1cOp, SpectrollOp |

**Total:** 14 GlitchOp implementations
**Needing Refactoring:** 11 (79%)

### After Milestones 1-6 (Final)
| Status | Count | Operations |
|--------|-------|-----------|
| ✅ No Reparse | 10 | ReduplicateWordsOp, SwapAdjacentWordsOp, RushmoreComboOp, RedactWordsOp ⭐, EkkokinOp ⭐, SpectrollOp ⭐, Mim1cOp ⭐, OcrArtifactsOp ⭐, QuotePairsOp ⭐, ZeroWidthOp ⭐ |
| 🟡 Special Cases (Require Full-Text) | 4 | DeleteRandomWordsOp, HokeyOp, PedantOp, TypoOp |

**Total:** 14 GlitchOp implementations
**Successfully Refactored:** 10 (71%)
**Special Cases (Architectural Constraints):** 4 (29%)

---

## Refactoring Priority

### ✅ Completed (Milestones 2-6)
1. ~~**RedactWordsOp**~~ - ✅ DONE: merge_adjacent using `buffer.merge_repeated_char_words()`
2. ~~**EkkokinOp**~~ - ✅ DONE: String-splitting converted to segment-based iteration
3. ~~**SpectrollOp**~~ - ✅ DONE: Segment-based with regex per segment
4. ~~**Mim1cOp**~~ - ✅ DONE: Segment-based char-level replacements
5. ~~**OcrArtifactsOp**~~ - ✅ DONE: Segment-based confusion pattern matching
6. ~~**QuotePairsOp**~~ - ✅ DONE: Global-to-segment position mapping
7. ~~**ZeroWidthOp**~~ - ✅ DONE: Segment-based (seg_idx, char_idx) position tracking

### 🟡 Special Cases (Documented as Requiring Full-Text Operations)
8. **DeleteRandomWordsOp** - Word core deletion creates punctuation-only segments requiring re-tokenization
9. **HokeyOp** - Custom regex tokenization with linguistic features (essential to operation semantics)
10. **PedantOp** - Context-aware linguistic transformations (require full-text context)
11. **TypoOp** - In-place char mutations crossing segment boundaries (architecturally incompatible)

---

## Key Patterns to Eliminate

### Pattern 1: split_with_separators + concat
```rust
// BAD - current pattern
let text = buffer.to_string();
let mut tokens = split_with_separators(&text);
// ... mutate tokens ...
*buffer = TextBuffer::from_owned(tokens.concat());
```

```rust
// GOOD - target pattern
for idx in 0..buffer.word_count() {
    if let Some(segment) = buffer.word_segment(idx) {
        // ... process segment ...
        buffer.replace_word(idx, &new_value)?;
    }
}
```

### Pattern 2: String + TextBuffer::from_owned
```rust
// BAD - current pattern
let mut text = buffer.to_string();
// ... string manipulation ...
*buffer = TextBuffer::from_owned(text);
```

```rust
// GOOD - target pattern (use segment methods)
// or for truly char-level ops:
buffer.replace_char_range(start..end, replacement)?;
```

---

## Next Steps

1. ✅ Complete this audit (Milestone 1)
2. ⏳ Add table-driven round-trip tests (Milestone 1)
3. Create `normalize_buffer()` helper for interim safety (Milestone 2)
4. Refactor DeleteRandomWordsOp and SwapAdjacentWordsOp (Milestone 3)
5. Refactor EkkokinOp, HokeyOp, PedantOp (Milestone 4)
6. Add regression tests and validation (Milestone 5)
7. Remove temporary helpers and verify (Milestone 6-7)
