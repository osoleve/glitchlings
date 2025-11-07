# GlitchOp Buffer Refactoring Audit

## Overview
This document provides a comprehensive audit of all `GlitchOp` implementations in the rust/zoo crate, identifying which operations use direct buffer segment methods vs. those that reparse the buffer via `buffer.to_string()` + `TextBuffer::from_owned()`.

**Audit Date:** 2025-11-07 (Updated after Milestones 1-4)
**Goal:** Eliminate all `buffer.to_string()` / `TextBuffer::from_owned()` patterns within GlitchOp implementations to avoid redundant reparsing.

**Status:** ✅ Milestones 1-4 Complete - 6/14 operations refactored (43% complete)

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

#### 4. DeleteRandomWordsOp ⭐ REFACTORED
**Location:** `rust/zoo/src/glitch_ops.rs:287-370`
**Status:** ✅ **REFACTORED** (Milestone 2)
**Before:** Lines 367-373 used regex-based reparsing for cleanup
**After:** Now uses `buffer.normalize()` (line 368)
**Impact:** Eliminated 7 lines of reparse code, no more `to_string()` + `from_owned()` round-trip

#### 5. RedactWordsOp ⭐ REFACTORED
**Location:** `rust/zoo/src/glitch_ops.rs:495-605`
**Status:** ✅ **REFACTORED** (Milestone 2)
**Before:** Lines 595-605 used regex-based merging with reparse
**After:** Now uses `buffer.merge_repeated_char_words()` (line 596)
**Impact:** Eliminated conditional reparsing path, 10 lines of regex code removed

#### 6. EkkokinOp ⭐ REFACTORED
**Location:** `rust/zoo/src/ekkokin.rs:148-208`
**Status:** ✅ **REFACTORED** (Milestone 4)
**Before:** Lines 150-198 used `split_with_separators()` + `concat()` + reparse
**After:** Now uses segment-based iteration with `buffer.word_segment()` and `buffer.replace_words_bulk()`
**Impact:**
- Eliminated split_with_separators pattern entirely
- No more `to_string()` + `from_owned()` round-trip
- Uses efficient bulk update for all replacements
- Removed unused import

---

### 🔴 Using Full String Reparse (Still Needs Refactoring)

#### 7. HokeyOp
**Location:** `rust/zoo/src/hokey.rs:574-628`
**Status:** 🔴 High Priority - Needs Refactoring
**Reparse Locations:**
- Line 576: `let text = buffer.to_string();`
- Line 581: `let tokens = self.tokenise(&text);` (custom tokenizer)
- Line 588: `let mut token_strings: Vec<String> = tokens.iter().map(...)`
- Line 625: `*buffer = TextBuffer::from_owned(result);`

**Pattern:** Custom tokenization and reconstruction
**Refactor Plan:** Adapt to use buffer's word segmentation or enhance buffer with needed features

#### 8. PedantOp
**Location:** `rust/zoo/src/pedant.rs:89-114`
**Status:** 🔴 Medium Priority - Needs Refactoring
**Reparse Locations:**
- Line 95: `let original = buffer.to_string();`
- Line 109: `*buffer = TextBuffer::from_owned(transformed);`

**Pattern:** Uses regex-based transformations on entire text
**Refactor Plan:** May need to keep string-based approach but document as exception, or implement regex over segments

---

### 🔴 Using Full Char-Level Reparse

#### 9. OcrArtifactsOp
**Location:** `rust/zoo/src/glitch_ops.rs:616-693`
**Status:** 🔴 Needs Refactoring
**Reparse Locations:**
- Line 624: `let text = buffer.to_string();`
- Line 690: `*buffer = TextBuffer::from_owned(output);`

**Pattern:** Char-level byte index matching and replacement
**Refactor Plan:** Could use `buffer.replace_char_range()` or implement via segment traversal

#### 10. ZeroWidthOp
**Location:** `rust/zoo/src/glitch_ops.rs:695-781`
**Status:** 🔴 Needs Refactoring
**Reparse Locations:**
- Line 713: `let text = buffer.to_string();`
- Line 778: `*buffer = TextBuffer::from_owned(result);`

**Pattern:** Char-level insertion between positions
**Refactor Plan:** Use segment-based char position tracking

#### 11. TypoOp
**Location:** `rust/zoo/src/glitch_ops.rs:783-1042`
**Status:** 🔴 Needs Refactoring
**Reparse Locations:**
- Line 941: `let text = buffer.to_string();`
- Line 1039: `*buffer = TextBuffer::from_owned(chars.into_iter().collect());`

**Pattern:** Vec<char> manipulation
**Refactor Plan:** Complex - may benefit from buffer enhancement to support char-level ops

#### 12. QuotePairsOp
**Location:** `rust/zoo/src/glitch_ops.rs:1092-1192`
**Status:** 🔴 Needs Refactoring
**Reparse Locations:**
- Line 1122: `let text = buffer.to_string();`
- Line 1189: `*buffer = TextBuffer::from_owned(result);`

**Pattern:** Char-index-based quote pair detection and replacement
**Refactor Plan:** Can likely use segment traversal with quote tracking

#### 13. Mim1cOp
**Location:** `rust/zoo/src/mim1c.rs:90-173`
**Status:** 🔴 Needs Refactoring
**Reparse Locations:**
- Line 92: `let original = buffer.to_string();`
- Line 169: `*buffer = TextBuffer::from_owned(result);`

**Pattern:** Byte-index-based character replacement
**Refactor Plan:** Could use `buffer.replace_char_range()` for individual char replacements

#### 14. SpectrollOp
**Location:** `rust/zoo/src/spectroll.rs:270-285`
**Status:** 🔴 Needs Refactoring
**Reparse Locations:**
- Line 276: `let text = buffer.to_string();`
- Line 282: `*buffer = TextBuffer::from_owned(updated);`

**Pattern:** Regex-based color word replacement
**Refactor Plan:** Could use segment-based traversal with regex matching per segment

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

### After Milestones 1-4 (Current)
| Status | Count | Operations |
|--------|-------|-----------|
| ✅ No Reparse | 6 | ReduplicateWordsOp, SwapAdjacentWordsOp, RushmoreComboOp, DeleteRandomWordsOp ⭐, RedactWordsOp ⭐, EkkokinOp ⭐ |
| 🔴 Still Need Refactoring | 8 | HokeyOp, PedantOp, OcrArtifactsOp, ZeroWidthOp, TypoOp, QuotePairsOp, Mim1cOp, SpectrollOp |

**Total:** 14 GlitchOp implementations
**Refactored:** 6 (43%)
**Remaining:** 8 (57%)

---

## Refactoring Priority

### ✅ Completed (Milestones 2-4)
1. ~~**DeleteRandomWordsOp**~~ - ✅ DONE: Cleanup using `buffer.normalize()`
2. ~~**RedactWordsOp**~~ - ✅ DONE: merge_adjacent using `buffer.merge_repeated_char_words()`
3. ~~**EkkokinOp**~~ - ✅ DONE: String-splitting converted to segment-based iteration

### 🎯 Remaining High Priority (Milestone 4-5)
4. **HokeyOp** - Complex custom tokenization, needs careful adaptation
5. **PedantOp** - Multiple regex-based transforms, may need hybrid approach

### 🔶 Medium Priority (Milestone 6)
6. **SpectrollOp** - Regex-based color word replacement
7. **OcrArtifactsOp** - Byte-index-based character confusion

### 🔸 Lower Priority (Milestone 6+)
8. **ZeroWidthOp** - Char-level insertion
9. **TypoOp** - Vec<char> manipulation
10. **QuotePairsOp** - Char-index quote pair detection
11. **Mim1cOp** - Byte-index character replacement

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
