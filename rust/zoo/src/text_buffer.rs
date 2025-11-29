use regex::Regex;
use std::ops::Range;
use std::sync::Arc;

use crate::resources::split_with_separators;

/// Represents the role of a segment inside a [`TextBuffer`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SegmentKind {
    /// A token that contains at least one non-whitespace character.
    Word,
    /// A run of whitespace characters separating words.
    Separator,
    /// A region that must not be mutated by glitch operations.
    Immutable,
}

/// A contiguous slice of text tracked by the [`TextBuffer`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TextSegment {
    kind: SegmentKind,
    text: String,
    /// Cached count of Unicode characters (not bytes) in this segment.
    /// Stored to avoid expensive .chars().count() during reindex.
    char_len: usize,
    /// Cached byte length of the text.
    byte_len: usize,
}

impl TextSegment {
    fn new(text: String, kind: SegmentKind) -> Self {
        let char_len = text.chars().count();
        let byte_len = text.len();
        Self {
            kind,
            text,
            char_len,
            byte_len,
        }
    }

    /// Creates a new segment and infers its kind from the content.
    fn inferred(text: String) -> Self {
        let kind = if text.chars().all(char::is_whitespace) {
            SegmentKind::Separator
        } else {
            SegmentKind::Word
        };
        Self::new(text, kind)
    }

    /// Returns the segment's text content.
    pub fn text(&self) -> &str {
        &self.text
    }

    /// Returns the classification of the segment.
    pub fn kind(&self) -> SegmentKind {
        self.kind
    }

    /// Returns true when the segment is allowed to be mutated.
    pub fn is_mutable(&self) -> bool {
        !matches!(self.kind, SegmentKind::Immutable)
    }

    /// Returns the cached character count (Unicode scalar values).
    fn char_len(&self) -> usize {
        self.char_len
    }

    /// Returns the cached byte length.
    fn byte_len(&self) -> usize {
        self.byte_len
    }

    fn set_text(&mut self, text: String, kind: SegmentKind) {
        self.char_len = text.chars().count();
        self.byte_len = text.len();
        self.text = text;
        self.kind = kind;
    }
}

/// Metadata describing where a [`TextSegment`] lives inside the overall buffer.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TextSpan {
    pub segment_index: usize,
    pub kind: SegmentKind,
    pub char_range: Range<usize>,
    pub byte_range: Range<usize>,
}

#[derive(Debug, Clone, Default)]
struct MaskingRules {
    include_only_patterns: Arc<Vec<Regex>>,
    exclude_patterns: Arc<Vec<Regex>>,
}

impl MaskingRules {
    fn new(include_only_patterns: &[Regex], exclude_patterns: &[Regex]) -> Self {
        Self {
            include_only_patterns: Arc::new(include_only_patterns.to_vec()),
            exclude_patterns: Arc::new(exclude_patterns.to_vec()),
        }
    }

    fn include_only(&self) -> &[Regex] {
        &self.include_only_patterns
    }

    fn exclude(&self) -> &[Regex] {
        &self.exclude_patterns
    }
}

/// Errors emitted by [`TextBuffer`] mutation helpers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TextBufferError {
    InvalidWordIndex {
        index: usize,
    },
    InvalidCharRange {
        start: usize,
        end: usize,
        max: usize,
    },
}

impl std::fmt::Display for TextBufferError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TextBufferError::InvalidWordIndex { index } => {
                write!(f, "invalid word index {index}")
            }
            TextBufferError::InvalidCharRange { start, end, max } => {
                write!(
                    f,
                    "invalid character range {start}..{end}; buffer length is {max} characters",
                )
            }
        }
    }
}

impl std::error::Error for TextBufferError {}

/// Shared intermediate representation for the Rust pipeline refactor.
///
/// The buffer tokenises the input text once, maintains lightweight metadata for
/// each segment, and offers mutation helpers that keep the metadata in sync so
/// glitchlings can operate deterministically without re-tokenising after each
/// operation.
#[derive(Debug, Clone, Default)]
pub struct TextBuffer {
    segments: Vec<TextSegment>,
    spans: Vec<TextSpan>,
    word_segment_indices: Vec<usize>,
    segment_to_word_index: Vec<Option<usize>>,
    total_chars: usize,
    total_bytes: usize,
    /// Tracks whether the buffer needs reindexing after mutations.
    /// When true, metadata (spans, indices) may be out of sync with segments.
    needs_reindex: bool,
    masking: MaskingRules,
}

impl std::fmt::Display for TextBuffer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        for segment in &self.segments {
            write!(f, "{}", segment.text)?;
        }
        Ok(())
    }
}

impl std::str::FromStr for TextBuffer {
    type Err = std::convert::Infallible;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(Self::from_owned(s.to_string(), &[], &[]))
    }
}

impl TextBuffer {
    /// Constructs a buffer from an owned `String`.
    pub fn from_owned(
        text: String,
        include_only_patterns: &[Regex],
        exclude_patterns: &[Regex],
    ) -> Self {
        let masking = MaskingRules::new(include_only_patterns, exclude_patterns);
        Self::from_owned_with_rules(text, masking)
    }

    fn from_owned_with_rules(text: String, masking: MaskingRules) -> Self {
        let segments = tokenise(&text, &masking);
        let segment_count = segments.len();

        // Pre-allocate vectors to avoid reallocations during reindex
        let mut buffer = Self {
            segments,
            spans: Vec::with_capacity(segment_count),
            word_segment_indices: Vec::with_capacity(segment_count / 2), // ~half are words
            segment_to_word_index: Vec::with_capacity(segment_count),
            total_chars: 0,
            total_bytes: 0,
            needs_reindex: false,
            masking,
        };
        buffer.reindex();
        buffer
    }

    /// Rebuilds a buffer with the existing masking patterns preserved.
    pub fn rebuild_with_patterns(&self, text: String) -> Self {
        TextBuffer::from_owned_with_rules(text, self.masking.clone())
    }

    /// Returns all tracked segments.
    pub fn segments(&self) -> &[TextSegment] {
        &self.segments
    }

    /// Returns metadata spans describing segment positions.
    pub fn spans(&self) -> &[TextSpan] {
        &self.spans
    }

    /// Returns the number of characters across the entire buffer.
    pub fn char_len(&self) -> usize {
        self.total_chars
    }

    /// Returns the number of word segments tracked by the buffer.
    pub fn word_count(&self) -> usize {
        self.word_segment_indices.len()
    }

    /// Returns the `TextSegment` corresponding to the requested word index.
    pub fn word_segment(&self, word_index: usize) -> Option<&TextSegment> {
        self.word_segment_indices
            .get(word_index)
            .copied()
            .and_then(|segment_index| self.segments.get(segment_index))
    }

    /// Returns an iterator over all segments with their word index (if they are word segments).
    ///
    /// Each item is (segment_index, segment, word_index_option).
    /// Word segments have Some(word_index), separator segments have None.
    ///
    /// Uses cached segment-to-word mapping built during reindex() for O(1) lookup.
    pub fn segments_with_word_indices(
        &self,
    ) -> impl Iterator<Item = (usize, &TextSegment, Option<usize>)> + '_ {
        self.segments.iter().enumerate().map(|(seg_idx, segment)| {
            let word_idx = self.segment_to_word_index.get(seg_idx).copied().flatten();
            (seg_idx, segment, word_idx)
        })
    }

    /// Replace the text for the given word index.
    pub fn replace_word(
        &mut self,
        word_index: usize,
        replacement: &str,
    ) -> Result<(), TextBufferError> {
        let segment_index = self
            .word_segment_indices
            .get(word_index)
            .copied()
            .ok_or(TextBufferError::InvalidWordIndex { index: word_index })?;
        let segment = self
            .segments
            .get_mut(segment_index)
            .ok_or(TextBufferError::InvalidWordIndex { index: word_index })?;
        segment.set_text(replacement.to_string(), SegmentKind::Word);
        self.mark_dirty();
        Ok(())
    }

    /// Replace multiple words in a single pass, avoiding repeated reindexing.
    pub fn replace_words_bulk<I>(&mut self, replacements: I) -> Result<(), TextBufferError>
    where
        I: IntoIterator<Item = (usize, String)>,
    {
        let mut applied_any = false;
        for (word_index, replacement) in replacements {
            let segment_index = self
                .word_segment_indices
                .get(word_index)
                .copied()
                .ok_or(TextBufferError::InvalidWordIndex { index: word_index })?;
            let segment = self
                .segments
                .get_mut(segment_index)
                .ok_or(TextBufferError::InvalidWordIndex { index: word_index })?;
            segment.set_text(replacement, SegmentKind::Word);
            applied_any = true;
        }

        if applied_any {
            self.mark_dirty();
        }
        Ok(())
    }

    /// Deletes the word at the requested index.
    pub fn delete_word(&mut self, word_index: usize) -> Result<(), TextBufferError> {
        let segment_index = self
            .word_segment_indices
            .get(word_index)
            .copied()
            .ok_or(TextBufferError::InvalidWordIndex { index: word_index })?;
        if segment_index >= self.segments.len() {
            return Err(TextBufferError::InvalidWordIndex { index: word_index });
        }
        self.segments.remove(segment_index);
        self.mark_dirty();
        Ok(())
    }

    /// Inserts a word directly after the provided word index.
    ///
    /// When `separator` is provided it will be inserted between the existing
    /// word and the new word as a separator segment, allowing callers to
    /// preserve whitespace decisions.
    pub fn insert_word_after(
        &mut self,
        word_index: usize,
        word: &str,
        separator: Option<&str>,
    ) -> Result<(), TextBufferError> {
        let segment_index = self
            .word_segment_indices
            .get(word_index)
            .copied()
            .ok_or(TextBufferError::InvalidWordIndex { index: word_index })?;
        let mut insert_at = segment_index + 1;
        if let Some(sep) = separator {
            if !sep.is_empty() {
                self.segments.insert(
                    insert_at,
                    TextSegment::new(sep.to_string(), SegmentKind::Separator),
                );
                insert_at += 1;
            }
        }
        self.segments.insert(
            insert_at,
            TextSegment::new(word.to_string(), SegmentKind::Word),
        );
        self.mark_dirty();
        Ok(())
    }

    /// Applies multiple word reduplications in a single pass.
    ///
    /// Each reduplication consists of:
    /// - word_index: the index of the word to reduplicate
    /// - first_replacement: the text to replace the original word with
    /// - second_word: the duplicated word to insert after
    /// - separator: optional separator between the two words
    ///
    /// Rebuilds the segment vector in a single pass to avoid O(N^2) behavior from repeated insertions.
    pub fn reduplicate_words_bulk<I>(&mut self, reduplications: I) -> Result<(), TextBufferError>
    where
        I: IntoIterator<Item = (usize, String, String, Option<String>)>,
    {
        // Ensure indices are fresh before we start
        self.reindex_if_needed();

        // Collect and sort in ASCENDING order by word_index
        let mut ops: Vec<_> = reduplications.into_iter().collect();
        if ops.is_empty() {
            return Ok(());
        }
        ops.sort_by(|a, b| a.0.cmp(&b.0)); // Ascending order

        // Validate all indices first
        if let Some((max_idx, _, _, _)) = ops.last() {
            if *max_idx >= self.word_count() {
                return Err(TextBufferError::InvalidWordIndex { index: *max_idx });
            }
        }

        // Rebuild segments in a new vector
        // Use std::mem::take to consume the old segments and avoid cloning strings
        let old_segments = std::mem::take(&mut self.segments);
        let mut new_segments = Vec::with_capacity(old_segments.len() + ops.len() * 2);
        let mut ops_iter = ops.into_iter().peekable();

        for (segment_index, segment) in old_segments.into_iter().enumerate() {
            // Check if this segment corresponds to a word index we want to modify
            let word_idx_opt = self
                .segment_to_word_index
                .get(segment_index)
                .copied()
                .flatten();

            if let Some(word_idx) = word_idx_opt {
                // Check if the next operation targets this word
                if let Some(&(target_word_idx, _, _, _)) = ops_iter.peek() {
                    if target_word_idx == word_idx {
                        // Apply the operation
                        let (_, first_replacement, second_word, separator) =
                            ops_iter.next().unwrap();

                        // 1. First word (replacement)
                        new_segments.push(TextSegment::new(first_replacement, SegmentKind::Word));

                        // 2. Separator (if any)
                        if let Some(sep) = separator {
                            if !sep.is_empty() {
                                new_segments.push(TextSegment::new(sep, SegmentKind::Separator));
                            }
                        }

                        // 3. Second word
                        new_segments.push(TextSegment::new(second_word, SegmentKind::Word));

                        continue; // Skip adding the original segment
                    }
                }
            }

            // Otherwise, keep the original segment
            new_segments.push(segment);
        }

        self.segments = new_segments;
        self.mark_dirty();
        Ok(())
    }

    /// Deletes multiple words in a single pass.
    ///
    /// Takes an iterator of (word_index, optional_replacement) pairs.
    /// If replacement is Some, replaces the word with that text (e.g., affixes only).
    /// If replacement is None, removes the word segment entirely.
    ///
    /// Processes in descending index order to avoid index shifting.
    /// Only reindexes once at the end.
    pub fn delete_words_bulk<I>(&mut self, deletions: I) -> Result<(), TextBufferError>
    where
        I: IntoIterator<Item = (usize, Option<String>)>,
    {
        // Ensure indices are fresh before we start
        self.reindex_if_needed();

        // Collect and sort in descending order by word_index
        let mut ops: Vec<_> = deletions.into_iter().collect();
        if ops.is_empty() {
            return Ok(());
        }
        ops.sort_by(|a, b| b.0.cmp(&a.0)); // Descending order

        for (word_index, replacement) in ops {
            let segment_index = self
                .word_segment_indices
                .get(word_index)
                .copied()
                .ok_or(TextBufferError::InvalidWordIndex { index: word_index })?;

            // Determine if we should remove or replace
            let should_remove = replacement.as_ref().is_none_or(|s| s.is_empty());

            if should_remove {
                // Remove the segment entirely
                if segment_index < self.segments.len() {
                    self.segments.remove(segment_index);
                }
            } else {
                // Replace with the provided text
                let repl_text = replacement.unwrap(); // Safe: we checked it's Some and not empty
                let segment = self
                    .segments
                    .get_mut(segment_index)
                    .ok_or(TextBufferError::InvalidWordIndex { index: word_index })?;
                segment.set_text(repl_text, SegmentKind::Word);
            }
        }

        self.mark_dirty();
        Ok(())
    }

    /// Replaces the provided character range with new text.
    pub fn replace_char_range(
        &mut self,
        char_range: Range<usize>,
        replacement: &str,
    ) -> Result<(), TextBufferError> {
        if char_range.start > char_range.end || char_range.end > self.total_chars {
            return Err(TextBufferError::InvalidCharRange {
                start: char_range.start,
                end: char_range.end,
                max: self.total_chars,
            });
        }

        if char_range.start == char_range.end && replacement.is_empty() {
            return Ok(());
        }

        let mut text = self.to_string();
        let start_byte =
            self.char_to_byte_index(char_range.start)
                .ok_or(TextBufferError::InvalidCharRange {
                    start: char_range.start,
                    end: char_range.end,
                    max: self.total_chars,
                })?;
        let end_byte =
            self.char_to_byte_index(char_range.end)
                .ok_or(TextBufferError::InvalidCharRange {
                    start: char_range.start,
                    end: char_range.end,
                    max: self.total_chars,
                })?;
        text.replace_range(start_byte..end_byte, replacement);
        *self = self.rebuild_with_patterns(text);
        Ok(())
    }

    /// Normalizes whitespace and punctuation spacing without reparsing.
    ///
    /// This method:
    /// - Merges consecutive separator segments into single spaces
    /// - Removes spaces before punctuation (.,:;)
    /// - Trims leading/trailing whitespace
    ///
    /// This is more efficient than reparsing via `to_string()` + `from_owned()`.
    pub fn normalize(&mut self) {
        // First pass: identify segments to merge/modify
        let mut normalized: Vec<TextSegment> = Vec::new();
        let mut pending_separator = false;

        for segment in &self.segments {
            match segment.kind() {
                SegmentKind::Separator => {
                    // Mark that we have a separator pending
                    pending_separator = true;
                }
                SegmentKind::Word => {
                    let text = segment.text();

                    // Check if word starts with punctuation that should not have space before
                    let starts_with_punct = text
                        .chars()
                        .next()
                        .map(|c| matches!(c, '.' | ',' | ':' | ';'))
                        .unwrap_or(false);

                    // Add separator if needed (but not before sentence punctuation)
                    if pending_separator && !starts_with_punct && !normalized.is_empty() {
                        normalized.push(TextSegment::new(" ".to_string(), SegmentKind::Separator));
                    }
                    pending_separator = false;

                    // Add the word
                    normalized.push(segment.clone());
                }
                SegmentKind::Immutable => {
                    if pending_separator && !normalized.is_empty() {
                        normalized.push(TextSegment::new(" ".to_string(), SegmentKind::Separator));
                    }
                    pending_separator = false;
                    normalized.push(segment.clone());
                }
            }
        }

        // Trim: remove leading/trailing separators
        // Remove leading separators efficiently
        let start = normalized
            .iter()
            .take_while(|s| matches!(s.kind(), SegmentKind::Separator))
            .count();
        if start > 0 {
            normalized.drain(0..start);
        }
        while normalized
            .last()
            .map(|s| matches!(s.kind(), SegmentKind::Separator))
            .unwrap_or(false)
        {
            normalized.pop();
        }

        self.segments = normalized;
        self.mark_dirty();
    }

    /// Replaces the text of a specific segment while preserving its kind.
    ///
    /// This is useful for char-level operations that modify segment content
    /// without changing whether it's a word or separator.
    pub fn replace_segment(&mut self, segment_index: usize, new_text: String) {
        if segment_index >= self.segments.len() {
            return;
        }

        let kind = self.segments[segment_index].kind();
        self.segments[segment_index] = TextSegment::new(new_text, kind);
        self.mark_dirty();
    }

    /// Replaces multiple segments in bulk.
    ///
    /// Takes an iterator of (segment_index, new_text) pairs.
    /// More efficient than calling replace_segment repeatedly.
    pub fn replace_segments_bulk<I>(&mut self, replacements: I)
    where
        I: IntoIterator<Item = (usize, String)>,
    {
        let mut replaced = false;
        for (segment_index, new_text) in replacements {
            if segment_index < self.segments.len() {
                let kind = self.segments[segment_index].kind();
                self.segments[segment_index] = TextSegment::new(new_text, kind);
                replaced = true;
            }
        }
        if replaced {
            self.mark_dirty();
        }
    }

    /// Merges adjacent word segments that consist entirely of the same repeated character,
    /// removing separators between them.
    ///
    /// This is used by RedactWordsOp to merge adjacent redacted words like "███ ███" into "██████".
    pub fn merge_repeated_char_words(&mut self, repeated_char: &str) {
        if self.segments.is_empty() || repeated_char.is_empty() {
            return;
        }

        // Helper function to check if a word consists entirely of repeated copies of the token
        let is_repeated_token = |text: &str| -> bool {
            if text.is_empty() {
                return false;
            }
            // Check if the word length is a multiple of the token length
            if !text.len().is_multiple_of(repeated_char.len()) {
                return false;
            }
            // Check if the word consists of repeated copies of the token
            text.as_bytes()
                .chunks(repeated_char.len())
                .all(|chunk| chunk == repeated_char.as_bytes())
        };

        let mut merged: Vec<TextSegment> = Vec::new();
        let mut i = 0;

        while i < self.segments.len() {
            let segment = &self.segments[i];

            if matches!(segment.kind(), SegmentKind::Word) {
                let text = segment.text();

                // Check if this word is composed of repeated tokens
                if is_repeated_token(text) {
                    // Count how many copies of the token we have
                    let mut token_count = text.len() / repeated_char.len();

                    // Look ahead for more repeated token words separated by separators
                    let mut j = i + 1;
                    while j < self.segments.len() {
                        if matches!(self.segments[j].kind(), SegmentKind::Separator) {
                            // Skip separator, check next word
                            if j + 1 < self.segments.len() {
                                let next_word = &self.segments[j + 1];
                                if matches!(next_word.kind(), SegmentKind::Word) {
                                    let next_text = next_word.text();
                                    if is_repeated_token(next_text) {
                                        // This is also a repeated token word - merge it
                                        token_count += next_text.len() / repeated_char.len();
                                        j += 2; // Skip separator and word
                                        continue;
                                    }
                                }
                            }
                            break;
                        } else {
                            break;
                        }
                    }

                    // Create merged word with total count
                    let merged_text = repeated_char.repeat(token_count);
                    merged.push(TextSegment::new(merged_text, SegmentKind::Word));

                    // Skip to position j (we've consumed segments i..j)
                    i = j;
                    continue;
                }
            }

            // Not a repeated token word - just add it
            merged.push(segment.clone());
            i += 1;
        }

        self.segments = merged;
        self.mark_dirty();
    }

    fn char_to_byte_index(&self, char_index: usize) -> Option<usize> {
        if char_index > self.total_chars {
            return None;
        }
        if char_index == self.total_chars {
            return Some(self.total_bytes);
        }
        for span in &self.spans {
            if span.char_range.contains(&char_index) {
                let relative = char_index - span.char_range.start;
                let segment = &self.segments[span.segment_index];
                let byte_offset = byte_index_for_char_offset(segment.text(), relative);
                return Some(span.byte_range.start + byte_offset);
            }
        }
        None
    }

    /// Reindexes the buffer if mutations have made metadata stale.
    /// This is the public API that should be called after a batch of mutations.
    pub fn reindex_if_needed(&mut self) {
        if self.needs_reindex {
            self.reindex();
        }
    }

    fn reindex(&mut self) {
        self.spans.clear();
        self.word_segment_indices.clear();
        self.segment_to_word_index.clear();
        self.segment_to_word_index.resize(self.segments.len(), None);

        let mut char_cursor = 0;
        let mut byte_cursor = 0;
        for (segment_index, segment) in self.segments.iter().enumerate() {
            // Use cached lengths instead of recomputing - major optimization!
            let char_len = segment.char_len();
            let byte_len = segment.byte_len();
            let span = TextSpan {
                segment_index,
                kind: segment.kind(),
                char_range: char_cursor..(char_cursor + char_len),
                byte_range: byte_cursor..(byte_cursor + byte_len),
            };
            if matches!(segment.kind(), SegmentKind::Word) {
                let word_index = self.word_segment_indices.len();
                self.word_segment_indices.push(segment_index);
                self.segment_to_word_index[segment_index] = Some(word_index);
            }
            self.spans.push(span);
            char_cursor += char_len;
            byte_cursor += byte_len;
        }
        self.total_chars = char_cursor;
        self.total_bytes = byte_cursor;
        self.needs_reindex = false;
    }

    /// Marks the buffer as needing reindexing after a mutation.
    fn mark_dirty(&mut self) {
        self.needs_reindex = true;
    }
}

fn byte_index_for_char_offset(text: &str, offset: usize) -> usize {
    if offset == 0 {
        return 0;
    }
    for (count, (byte_index, _)) in text.char_indices().enumerate() {
        if count == offset {
            return byte_index;
        }
    }
    text.len()
}

fn merge_spans(mut spans: Vec<Range<usize>>) -> Vec<Range<usize>> {
    if spans.is_empty() {
        return spans;
    }

    spans.sort_by_key(|range| range.start);
    let mut merged: Vec<Range<usize>> = Vec::with_capacity(spans.len());

    for span in spans {
        if span.is_empty() {
            continue;
        }
        if let Some(last) = merged.last_mut() {
            if span.start <= last.end {
                last.end = last.end.max(span.end);
                continue;
            }
        }
        merged.push(span);
    }

    merged
}

fn invert_spans(spans: &[Range<usize>], total: usize) -> Vec<Range<usize>> {
    if spans.is_empty() {
        return vec![0..total];
    }

    let mut inverted: Vec<Range<usize>> = Vec::new();
    let mut cursor = 0usize;

    for span in spans {
        if cursor < span.start {
            inverted.push(cursor..span.start);
        }
        cursor = cursor.max(span.end);
    }

    if cursor < total {
        inverted.push(cursor..total);
    }

    inverted
}

fn collect_match_spans(patterns: &[Regex], text: &str) -> Vec<Range<usize>> {
    let mut spans: Vec<Range<usize>> = Vec::new();
    for regex in patterns {
        for capture in regex.find_iter(text) {
            spans.push(capture.start()..capture.end());
        }
    }
    merge_spans(spans)
}

fn push_mutable_segments(text: &str, segments: &mut Vec<TextSegment>) {
    for token in split_with_separators(text) {
        if token.is_empty() {
            continue;
        }

        if token.chars().all(char::is_whitespace) {
            segments.push(TextSegment::new(token, SegmentKind::Separator));
        } else {
            segments.push(TextSegment::new(token, SegmentKind::Word));
        }
    }
}

fn tokenise(text: &str, masking: &MaskingRules) -> Vec<TextSegment> {
    if text.is_empty() {
        return Vec::new();
    }

    let include_spans = collect_match_spans(masking.include_only(), text);
    let mut immutable_spans = collect_match_spans(masking.exclude(), text);
    if !include_spans.is_empty() {
        immutable_spans.extend(invert_spans(&include_spans, text.len()));
        immutable_spans = merge_spans(immutable_spans);
    }

    let mut segments: Vec<TextSegment> = Vec::new();
    let mut cursor = 0usize;

    for span in immutable_spans {
        if cursor < span.start {
            push_mutable_segments(&text[cursor..span.start], &mut segments);
        }
        if span.start < span.end {
            segments.push(TextSegment::new(
                text[span.start..span.end].to_string(),
                SegmentKind::Immutable,
            ));
        }
        cursor = span.end;
    }

    if cursor < text.len() {
        push_mutable_segments(&text[cursor..], &mut segments);
    }

    if segments.is_empty() {
        segments.push(TextSegment::inferred(text.to_string()));
    }

    segments
}

#[cfg(test)]
mod tests {
    use super::{SegmentKind, TextBuffer, TextBufferError};

    #[test]
    fn tokenisation_tracks_words_and_separators() {
        let buffer = TextBuffer::from_owned("Hello  world!\n".to_string(), &[], &[]);
        let segments = buffer.segments();
        assert_eq!(segments.len(), 4);
        assert_eq!(segments[0].text(), "Hello");
        assert_eq!(segments[0].kind(), SegmentKind::Word);
        assert_eq!(segments[1].text(), "  ");
        assert_eq!(segments[1].kind(), SegmentKind::Separator);
        assert_eq!(segments[2].text(), "world!");
        assert_eq!(segments[2].kind(), SegmentKind::Word);
        assert_eq!(segments[3].text(), "\n");
        assert_eq!(segments[3].kind(), SegmentKind::Separator);

        assert_eq!(buffer.char_len(), "Hello  world!\n".chars().count());
        assert_eq!(buffer.word_count(), 2);
    }

    #[test]
    fn replacing_words_updates_segments_and_metadata() {
        let mut buffer = TextBuffer::from_owned("Hello world".to_string(), &[], &[]);
        buffer.replace_word(1, "galaxy").unwrap();
        buffer.reindex_if_needed();
        assert_eq!(buffer.to_string(), "Hello galaxy");
        let spans = buffer.spans();
        assert_eq!(spans.len(), 3);
        assert_eq!(spans[2].char_range, 6..12);
    }

    #[test]
    fn deleting_words_removes_segments() {
        let mut buffer = TextBuffer::from_owned("Hello brave world".to_string(), &[], &[]);
        buffer.delete_word(1).unwrap();
        buffer.reindex_if_needed();
        assert_eq!(buffer.to_string(), "Hello  world");
        assert_eq!(buffer.word_count(), 2);
        assert_eq!(buffer.spans().len(), 4);
        assert!(buffer.spans()[1..3]
            .iter()
            .all(|span| matches!(span.kind, SegmentKind::Separator)));
    }

    #[test]
    fn inserting_words_preserves_separator_control() {
        let mut buffer = TextBuffer::from_owned("Hello world".to_string(), &[], &[]);
        buffer.insert_word_after(0, "there", Some(", ")).unwrap();
        buffer.reindex_if_needed();
        assert_eq!(buffer.to_string(), "Hello, there world");
        assert_eq!(buffer.word_count(), 3);
        assert_eq!(buffer.spans().len(), 5);
    }

    #[test]
    fn bulk_replace_words_updates_multiple_entries() {
        let mut buffer = TextBuffer::from_owned("alpha beta gamma delta".to_string(), &[], &[]);
        buffer
            .replace_words_bulk(vec![(0, "delta".to_string()), (3, "alpha".to_string())])
            .expect("bulk replace succeeds");
        assert_eq!(buffer.to_string(), "delta beta gamma alpha");
        let spans = buffer.spans();
        assert_eq!(spans[0].char_range, 0..5);
        assert_eq!(spans.len(), 7);
        assert_eq!(spans.last().unwrap().char_range, 17..22);
    }

    #[test]
    fn replace_char_range_handles_multisegment_updates() {
        let mut buffer = TextBuffer::from_owned("Hello world".to_string(), &[], &[]);
        buffer
            .replace_char_range(6..11, "galaxy")
            .expect("char replacement succeeded");
        assert_eq!(buffer.to_string(), "Hello galaxy");
        assert_eq!(buffer.word_count(), 2);
        assert_eq!(buffer.spans().len(), 3);
    }

    #[test]
    fn invalid_operations_return_errors() {
        let mut buffer = TextBuffer::from_owned("Hello".to_string(), &[], &[]);
        let err = buffer.replace_word(1, "world").unwrap_err();
        assert!(matches!(err, TextBufferError::InvalidWordIndex { .. }));

        let err = buffer
            .replace_char_range(2..10, "x")
            .expect_err("range outside bounds");
        assert!(matches!(err, TextBufferError::InvalidCharRange { .. }));
    }
}
