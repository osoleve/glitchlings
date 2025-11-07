# GlitchOp Buffer Refactoring Audit

## Overview
This document provides a comprehensive audit of all `GlitchOp` implementations in the rust/zoo crate, identifying which operations use direct buffer segment methods vs. those that reparse the buffer via `buffer.to_string()` + `TextBuffer::from_owned()`.

**Audit Date:** 2025-11-07 (Updated after Milestones 1-7, Final)
**Goal:** Eliminate all `buffer.to_string()` / `TextBuffer::from_owned()` patterns within GlitchOp implementations to avoid redundant reparsing where architecturally feasible.

**Status:** ✅ Milestones 1-7 Complete - 12 fully refactored, 2 require full-text operations
**Fully Refactored:** 12/14 (86%)
**Require Full-Text:** 2/14 (14%) - architectural constraints

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
**Location:** `rust/zoo/src/glitch_ops.rs:507-684`
**Status:** ✅ **FULLY REFACTORED** (Optimized in final pass)
**Before:** Per-word `replace_word()` calls + regex-based merging with reparse
**After:** Single-pass string reconstruction with on-the-fly merging
**Pattern:**
- Collects redaction decisions (HashMap of word_index → candidate)
- Uses `segments_with_word_indices()` to iterate once through all segments
- Tracks pending redaction tokens when merge_adjacent=true
- Skips punctuation/whitespace separators between redacted words during merge
- Builds final string in linear time without reparsing
**Impact:** Eliminated all buffer mutations and reparsing - now O(n) linear scan

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

#### 11. TypoOp ⭐ REFACTORED
**Location:** `rust/zoo/src/glitch_ops.rs:1127-1354`
**Status:** ✅ **REFACTORED** (Milestone 7)
**Before:** Converted entire text to Vec<char>, applied mutations, rebuilt buffer
**After:** Segment-based operations respecting word boundaries
**Pattern:**
- Character operations (swap, delete, keyboard typos, collapse, repeat) work within Word segments
- Space removal operations target Separator segments
- Space insertion operations target Word segments (will split on reparse)
- Modified segments tracked in HashMap
- Final reconstruction from modified segments only
**Impact:** Eliminated full-text char array conversion, now respects segment boundaries

---

### 🟡 Requiring Full-Text Operations (Documented as Special Cases)

These operations require full-text operations due to their architectural characteristics and cannot be efficiently refactored to use segment-based operations without fundamentally changing their design.

#### 11. DeleteRandomWordsOp ⭐ REFACTORED
**Location:** `rust/zoo/src/glitch_ops.rs:294-431`
**Status:** ✅ **FULLY REFACTORED** (Optimized in final pass)
**Before:** Per-word `replace_word()` calls + regex-based cleanup/normalization with reparse
**After:** Single-pass string reconstruction with on-the-fly spacing normalization
**Pattern:**
- Collects deletion decisions (HashSet of word indices)
- Uses `segments_with_word_indices()` to iterate once through all segments
- For deleted words: emits only prefix+suffix (trimmed)
- Handles punctuation spacing rules (no space before .,:;)
- Tracks `needs_separator` state to properly insert spaces
- Builds final string in linear time without reparsing
**Impact:** Eliminated N `replace_word()` calls + regex cleanup - now O(n) linear scan

---

### 🟡 Requiring Full-Text Operations (Special Cases - Architectural Constraints)

These operations require full-text operations due to their architectural characteristics and cannot be efficiently refactored to use segment-based operations without fundamentally changing their design.

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

### After Milestones 1-7 (Final)
| Status | Count | Operations |
|--------|-------|-----------|
| ✅ No Reparse | 12 | ReduplicateWordsOp, SwapAdjacentWordsOp, RushmoreComboOp, DeleteRandomWordsOp ⭐, RedactWordsOp ⭐, EkkokinOp ⭐, SpectrollOp ⭐, Mim1cOp ⭐, OcrArtifactsOp ⭐, QuotePairsOp ⭐, ZeroWidthOp ⭐, TypoOp ⭐ |
| 🟡 Special Cases (Require Full-Text) | 2 | HokeyOp, PedantOp |

**Total:** 14 GlitchOp implementations
**Fully Refactored:** 12 (86%)
**Require Full-Text (Architectural Constraints):** 2 (14%)

---

## Refactoring Priority

### ✅ Completed (Milestones 2-7)
1. ~~**DeleteRandomWordsOp**~~ - ✅ DONE: Single-pass reconstruction with on-the-fly punctuation spacing
2. ~~**RedactWordsOp**~~ - ✅ DONE: Single-pass string reconstruction with on-the-fly merge_adjacent
3. ~~**EkkokinOp**~~ - ✅ DONE: String-splitting converted to segment-based iteration
4. ~~**SpectrollOp**~~ - ✅ DONE: Segment-based with regex per segment, handles multiple matches
5. ~~**Mim1cOp**~~ - ✅ DONE: Segment-based char-level replacements
6. ~~**OcrArtifactsOp**~~ - ✅ DONE: Segment-based confusion pattern matching
7. ~~**QuotePairsOp**~~ - ✅ DONE: Global-to-segment position mapping
8. ~~**ZeroWidthOp**~~ - ✅ DONE: Segment-based (seg_idx, char_idx) position tracking
9. ~~**TypoOp**~~ - ✅ DONE: Segment-based operations respecting word boundaries

### 🟡 Special Cases (Documented as Requiring Full-Text Operations)
10. **HokeyOp** - Custom regex tokenization with linguistic features (essential to operation semantics)
11. **PedantOp** - Context-aware linguistic transformations (require full-text context)

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
