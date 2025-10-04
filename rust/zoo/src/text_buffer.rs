use std::ops::Range;

use crate::resources::split_with_separators;

/// Represents the role of a segment inside a [`TextBuffer`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SegmentKind {
    /// A token that contains at least one non-whitespace character.
    Word,
    /// A run of whitespace characters separating words.
    Separator,
}

/// A contiguous slice of text tracked by the [`TextBuffer`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TextSegment {
    kind: SegmentKind,
    text: String,
}

impl TextSegment {
    fn new(text: String, kind: SegmentKind) -> Self {
        Self { kind, text }
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

    fn set_text(&mut self, text: String, kind: SegmentKind) {
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
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct TextBuffer {
    segments: Vec<TextSegment>,
    spans: Vec<TextSpan>,
    word_segment_indices: Vec<usize>,
    total_chars: usize,
    total_bytes: usize,
}

impl TextBuffer {
    /// Constructs a buffer from an owned `String`.
    pub fn from_owned(text: String) -> Self {
        let mut buffer = Self {
            segments: tokenise(&text),
            spans: Vec::new(),
            word_segment_indices: Vec::new(),
            total_chars: 0,
            total_bytes: 0,
        };
        buffer.reindex();
        buffer
    }

    /// Constructs a buffer from a borrowed `&str`.
    pub fn from_str(text: &str) -> Self {
        Self::from_owned(text.to_string())
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
        self.reindex();
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
        self.reindex();
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
        self.reindex();
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
        *self = TextBuffer::from_owned(text);
        Ok(())
    }

    /// Returns the full text represented by the buffer.
    pub fn to_string(&self) -> String {
        self.segments
            .iter()
            .map(|segment| segment.text.as_str())
            .collect()
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

    fn reindex(&mut self) {
        self.spans.clear();
        self.word_segment_indices.clear();
        let mut char_cursor = 0;
        let mut byte_cursor = 0;
        for (segment_index, segment) in self.segments.iter().enumerate() {
            let char_len = segment.text().chars().count();
            let byte_len = segment.text().len();
            let span = TextSpan {
                segment_index,
                kind: segment.kind(),
                char_range: char_cursor..(char_cursor + char_len),
                byte_range: byte_cursor..(byte_cursor + byte_len),
            };
            if matches!(segment.kind(), SegmentKind::Word) {
                self.word_segment_indices.push(segment_index);
            }
            self.spans.push(span);
            char_cursor += char_len;
            byte_cursor += byte_len;
        }
        self.total_chars = char_cursor;
        self.total_bytes = byte_cursor;
    }
}

fn byte_index_for_char_offset(text: &str, offset: usize) -> usize {
    if offset == 0 {
        return 0;
    }
    let mut count = 0;
    for (byte_index, _) in text.char_indices() {
        if count == offset {
            return byte_index;
        }
        count += 1;
    }
    text.len()
}

fn tokenise(text: &str) -> Vec<TextSegment> {
    if text.is_empty() {
        return Vec::new();
    }

    let mut segments: Vec<TextSegment> = Vec::new();
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
        let buffer = TextBuffer::from_str("Hello  world!\n");
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
        let mut buffer = TextBuffer::from_str("Hello world");
        buffer.replace_word(1, "galaxy").unwrap();
        assert_eq!(buffer.to_string(), "Hello galaxy");
        let spans = buffer.spans();
        assert_eq!(spans.len(), 3);
        assert_eq!(spans[2].char_range, 6..12);
    }

    #[test]
    fn deleting_words_removes_segments() {
        let mut buffer = TextBuffer::from_str("Hello brave world");
        buffer.delete_word(1).unwrap();
        assert_eq!(buffer.to_string(), "Hello  world");
        assert_eq!(buffer.word_count(), 2);
        assert_eq!(buffer.spans().len(), 4);
        assert!(buffer.spans()[1..3]
            .iter()
            .all(|span| matches!(span.kind, SegmentKind::Separator)));
    }

    #[test]
    fn inserting_words_preserves_separator_control() {
        let mut buffer = TextBuffer::from_str("Hello world");
        buffer.insert_word_after(0, "there", Some(", ")).unwrap();
        assert_eq!(buffer.to_string(), "Hello, there world");
        assert_eq!(buffer.word_count(), 3);
        assert_eq!(buffer.spans().len(), 5);
    }

    #[test]
    fn replace_char_range_handles_multisegment_updates() {
        let mut buffer = TextBuffer::from_str("Hello world");
        buffer
            .replace_char_range(6..11, "galaxy")
            .expect("char replacement succeeded");
        assert_eq!(buffer.to_string(), "Hello galaxy");
        assert_eq!(buffer.word_count(), 2);
        assert_eq!(buffer.spans().len(), 3);
    }

    #[test]
    fn invalid_operations_return_errors() {
        let mut buffer = TextBuffer::from_str("Hello");
        let err = buffer.replace_word(1, "world").unwrap_err();
        assert!(matches!(err, TextBufferError::InvalidWordIndex { .. }));

        let err = buffer
            .replace_char_range(2..10, "x")
            .expect_err("range outside bounds");
        assert!(matches!(err, TextBufferError::InvalidCharRange { .. }));
    }
}
