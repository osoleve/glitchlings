# GlitchOp Buffer Refactoring Audit

## Overview
This document provides a comprehensive audit of all `GlitchOp` implementations in the rust/zoo crate, identifying which operations use direct buffer segment methods vs. those that reparse the buffer via `buffer.to_string()` + `TextBuffer::from_owned()`.

**Audit Date:** 2025-11-07
**Goal:** Eliminate all `buffer.to_string()` / `TextBuffer::from_owned()` patterns within GlitchOp implementations to avoid redundant reparsing.

---

## Implementation Status

### ✅ Already Using Segment Methods Correctly (No Reparse)

#### 1. ReduplicateWordsOp
**Location:** `rust/zoo/src/glitch_ops.rs:207-285`
**Status:** ✅ Good
**Pattern:** Uses `buffer.word_segment()`, `buffer.replace_word()`, `buffer.insert_word_after()`
**Notes:** This is the canonical example of proper segment-based operations.

#### 2. SwapAdjacentWordsOp
**Location:** `rust/zoo/src/glitch_ops.rs:378-436`
**Status:** ✅ Good
**Pattern:** Uses `buffer.word_segment()`, `buffer.replace_words_bulk()`
**Notes:** Efficient bulk replacement pattern. Good example.

#### 3. RushmoreComboOp
**Location:** `rust/zoo/src/glitch_ops.rs:438-493`
**Status:** ✅ Good
**Pattern:** Delegates to other ops
**Notes:** No direct buffer manipulation, just orchestration.

---

### ⚠️ Using Segment Methods BUT with Cleanup Reparse

#### 4. DeleteRandomWordsOp
**Location:** `rust/zoo/src/glitch_ops.rs:287-376`
**Status:** ⚠️ Needs Refactoring
**Reparse Location:** Lines 367-373
```rust
let mut joined = buffer.to_string();
joined = SPACE_BEFORE_PUNCTUATION.replace_all(&joined, "$1").into_owned();
joined = MULTIPLE_WHITESPACE.replace_all(&joined, " ").into_owned();
let final_text = joined.trim().to_string();
*buffer = TextBuffer::from_owned(final_text);
```
**Pattern:** Uses segment methods for deletions, but reparsed for whitespace cleanup
**Refactor Plan:** Implement cleanup logic directly on segments or create helper that doesn't require full reparse

#### 5. RedactWordsOp
**Location:** `rust/zoo/src/glitch_ops.rs:495-614`
**Status:** ⚠️ Needs Refactoring
**Reparse Location:** Lines 599-609
```rust
if self.merge_adjacent {
    let text = buffer.to_string();
    let regex = cached_merge_regex(&self.replacement_char)?;
    let merged = regex.replace_all(&text, |caps: &Captures| { ... }).into_owned();
    *buffer = TextBuffer::from_owned(merged);
}
```
**Pattern:** Uses segment methods for redaction, but reparsed for merge_adjacent
**Refactor Plan:** Implement merge_adjacent logic via segment traversal

---

### 🔴 Using Full String Reparse (split_with_separators pattern)

#### 6. EkkokinOp
**Location:** `rust/zoo/src/ekkokin.rs:148-203`
**Status:** 🔴 High Priority - Needs Refactoring
**Reparse Locations:**
- Line 150: `let text = buffer.to_string();`
- Line 164: `let mut tokens = split_with_separators(&text);`
- Line 198: `*buffer = TextBuffer::from_owned(updated);`

**Pattern:**
```rust
let text = buffer.to_string();
let mut tokens = split_with_separators(&text);
// ... mutate tokens ...
let updated = tokens.concat();
*buffer = TextBuffer::from_owned(updated);
```
**Refactor Plan:** Use `buffer.word_segments()` iterator + `replace_word()` for mutations

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

| Status | Count | Operations |
|--------|-------|-----------|
| ✅ Good | 3 | ReduplicateWordsOp, SwapAdjacentWordsOp, RushmoreComboOp |
| ⚠️ Partial | 2 | DeleteRandomWordsOp, RedactWordsOp |
| 🔴 Full Reparse | 9 | EkkokinOp, HokeyOp, PedantOp, OcrArtifactsOp, ZeroWidthOp, TypoOp, QuotePairsOp, Mim1cOp, SpectrollOp |

**Total:** 14 GlitchOp implementations
**Needing Refactoring:** 11 (79%)

---

## Refactoring Priority

### High Priority (Milestone 3-4)
1. **DeleteRandomWordsOp** - Already mostly segment-based, just cleanup needed
2. **EkkokinOp** - String-splitting pattern, straightforward to convert
3. **HokeyOp** - Complex but important, custom tokenization
4. **PedantOp** - Regex-based, may need special handling

### Medium Priority (Milestone 4)
5. **RedactWordsOp** - merge_adjacent logic needs segment-based solution
6. **SpectrollOp** - Regex-based but simpler than Pedant

### Lower Priority (As needed)
7. **OcrArtifactsOp**, **ZeroWidthOp**, **TypoOp**, **QuotePairsOp**, **Mim1cOp** - Char-level ops that may benefit from buffer enhancements

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
