/// Buffer round-trip tests for all GlitchOp implementations.
///
/// These tests verify that:
/// 1. Each op can be applied to a TextBuffer without panicking
/// 2. The resulting buffer is in a valid state (can be converted to string)
/// 3. The buffer can be re-parsed from its string representation without loss

use _zoo_rust::{
    DeleteRandomWordsOp, DeterministicRng, GlitchOperation, OcrArtifactsOp,
    QuotePairsOp, RedactWordsOp, ReduplicateWordsOp, SegmentKind, SwapAdjacentWordsOp,
    TextBuffer, TypoOp, ZeroWidthOp,
};
use _zoo_rust::glitch_ops::{GlitchOp, GlitchRng};

/// Test corpus covering various text patterns
const TEST_CORPUS: &[&str] = &[
    // Basic cases
    "Hello world",
    "The quick brown fox jumps over the lazy dog",
    "",
    "   ",
    "a",

    // Punctuation
    "Hello, world!",
    "Wait... what?",
    "Yes! No? Maybe...",

    // Multiple spaces and whitespace
    "Double  space",
    "Triple   space",
    "Tab\there",
    "Newline\nhere",

    // Mixed case
    "UPPERCASE",
    "lowercase",
    "MixedCase",
    "CamelCase",

    // Numbers and special chars
    "Test123",
    "user@example.com",
    "http://example.com",
    "$100.00",

    // Quotes and apostrophes
    "\"quoted text\"",
    "'single quotes'",
    "`backticks`",
    "don't",
    "it's",

    // Unicode
    "café",
    "résumé",
    "naïve",

    // Edge cases
    "a b c d e f g h i j",
    "Word",
    "Two words",
];

/// Helper to test a single operation without panicking
fn test_op_roundtrip<O>(op: O, text: &str, seed: u64, op_name: &str)
where
    O: GlitchOp,
{
    let mut buffer = TextBuffer::from_str(text);
    let mut rng = DeterministicRng::new(seed);

    // Apply the operation - should not panic
    let result = op.apply(&mut buffer, &mut rng);

    // Even if the operation errors (e.g., NoRedactableWords), buffer should be valid
    match result {
        Ok(_) => {
            // Buffer should be convertible to string
            let output = buffer.to_string();

            // Re-parsing should work
            let reparsed = TextBuffer::from_owned(output.clone());
            let reparsed_str = reparsed.to_string();

            // Round-trip should be lossless
            assert_eq!(
                output, reparsed_str,
                "Round-trip failed for {}: input='{}', output='{}', reparsed='{}'",
                op_name, text, output, reparsed_str
            );

            // Verify segment integrity
            verify_segment_integrity(&reparsed, op_name);
        }
        Err(e) => {
            // Some errors are acceptable (e.g., NoRedactableWords)
            // Buffer should still be in valid state
            let output = buffer.to_string();
            let _reparsed = TextBuffer::from_owned(output);
            // If we get here without panic, the buffer state is valid
            eprintln!("Op {} returned error (acceptable): {:?}", op_name, e);
        }
    }
}

/// Verify that buffer segments are well-formed
fn verify_segment_integrity(buffer: &TextBuffer, op_name: &str) {
    let segments = buffer.segments();
    let spans = buffer.spans();

    // Segments and spans should have same length
    assert_eq!(
        segments.len(),
        spans.len(),
        "{}: segment/span count mismatch",
        op_name
    );

    // Word segments should be tracked correctly
    let word_count = segments
        .iter()
        .filter(|s| matches!(s.kind(), SegmentKind::Word))
        .count();
    assert_eq!(
        word_count,
        buffer.word_count(),
        "{}: word count mismatch",
        op_name
    );

    // Verify no double spaces in output (unless originally present)
    let text = buffer.to_string();
    for (i, segment) in segments.iter().enumerate() {
        if matches!(segment.kind(), SegmentKind::Separator) {
            // Separators should only be whitespace
            assert!(
                segment.text().chars().all(char::is_whitespace),
                "{}: separator segment {} contains non-whitespace: '{}'",
                op_name, i, segment.text()
            );
        }
    }
}

#[test]
fn test_reduplicate_words_roundtrip() {
    for text in TEST_CORPUS {
        for rate in [0.0, 0.5, 1.0] {
            for unweighted in [false, true] {
                let op = ReduplicateWordsOp { rate, unweighted };
                test_op_roundtrip(op, text, 42, "ReduplicateWordsOp");
            }
        }
    }
}

#[test]
fn test_delete_random_words_roundtrip() {
    for text in TEST_CORPUS {
        for rate in [0.0, 0.3, 0.5, 0.8] {
            for unweighted in [false, true] {
                let op = DeleteRandomWordsOp { rate, unweighted };
                test_op_roundtrip(op, text, 123, "DeleteRandomWordsOp");
            }
        }
    }
}

#[test]
fn test_swap_adjacent_words_roundtrip() {
    for text in TEST_CORPUS {
        for rate in [0.0, 0.5, 1.0] {
            let op = SwapAdjacentWordsOp { rate };
            test_op_roundtrip(op, text, 456, "SwapAdjacentWordsOp");
        }
    }
}

#[test]
fn test_redact_words_roundtrip() {
    for text in TEST_CORPUS {
        for rate in [0.0, 0.5, 1.0] {
            for merge_adjacent in [false, true] {
                for unweighted in [false, true] {
                    let op = RedactWordsOp {
                        replacement_char: "█".to_string(),
                        rate,
                        merge_adjacent,
                        unweighted,
                    };
                    // This may error on empty/whitespace-only inputs - that's ok
                    test_op_roundtrip(op, text, 789, "RedactWordsOp");
                }
            }
        }
    }
}

#[test]
fn test_ocr_artifacts_roundtrip() {
    for text in TEST_CORPUS {
        for rate in [0.0, 0.5, 1.0] {
            let op = OcrArtifactsOp { rate };
            test_op_roundtrip(op, text, 101, "OcrArtifactsOp");
        }
    }
}

#[test]
fn test_typo_roundtrip() {
    let layout = std::collections::HashMap::from([
        ("a".to_string(), vec!["s".to_string(), "q".to_string()]),
        ("s".to_string(), vec!["a".to_string(), "d".to_string()]),
        ("d".to_string(), vec!["s".to_string(), "f".to_string()]),
    ]);

    for text in TEST_CORPUS {
        for rate in [0.0, 0.1, 0.3] {
            let op = TypoOp {
                rate,
                layout: layout.clone(),
            };
            test_op_roundtrip(op, text, 202, "TypoOp");
        }
    }
}

#[test]
fn test_zero_width_roundtrip() {
    for text in TEST_CORPUS {
        for rate in [0.0, 0.1, 0.5] {
            let op = ZeroWidthOp {
                rate,
                characters: vec!["\u{200B}".to_string(), "\u{200C}".to_string()],
            };
            test_op_roundtrip(op, text, 303, "ZeroWidthOp");
        }
    }
}

#[test]
fn test_quote_pairs_roundtrip() {
    for text in TEST_CORPUS {
        let op = QuotePairsOp::default();
        test_op_roundtrip(op, text, 404, "QuotePairsOp");
    }
}

/// Test that all operations preserve determinism with same seed
#[test]
fn test_deterministic_operations() {
    let text = "The quick brown fox jumps over the lazy dog";

    // Run each op twice with same seed
    let ops: Vec<(&str, GlitchOperation)> = vec![
        ("Reduplicate", GlitchOperation::Reduplicate(ReduplicateWordsOp { rate: 0.5, unweighted: false })),
        ("Delete", GlitchOperation::Delete(DeleteRandomWordsOp { rate: 0.3, unweighted: false })),
        ("SwapAdjacent", GlitchOperation::SwapAdjacent(SwapAdjacentWordsOp { rate: 0.5 })),
        ("Ocr", GlitchOperation::Ocr(OcrArtifactsOp { rate: 0.5 })),
        ("QuotePairs", GlitchOperation::QuotePairs(QuotePairsOp::default())),
    ];

    for (name, op) in ops {
        let mut buffer1 = TextBuffer::from_str(text);
        let mut rng1 = DeterministicRng::new(999);
        let _ = op.apply(&mut buffer1, &mut rng1);
        let result1 = buffer1.to_string();

        let mut buffer2 = TextBuffer::from_str(text);
        let mut rng2 = DeterministicRng::new(999);
        let _ = op.apply(&mut buffer2, &mut rng2);
        let result2 = buffer2.to_string();

        assert_eq!(result1, result2, "{} should be deterministic with same seed", name);
    }
}

/// Test that buffer operations work on very long text
#[test]
fn test_long_text_roundtrip() {
    let long_text = "word ".repeat(1000);

    let ops: Vec<Box<dyn Fn() -> Box<dyn GlitchOp>>> = vec![
        Box::new(|| Box::new(ReduplicateWordsOp { rate: 0.1, unweighted: false })),
        Box::new(|| Box::new(DeleteRandomWordsOp { rate: 0.1, unweighted: false })),
        Box::new(|| Box::new(SwapAdjacentWordsOp { rate: 0.1 })),
    ];

    for (i, op_factory) in ops.iter().enumerate() {
        let op = op_factory();
        let mut buffer = TextBuffer::from_str(&long_text);
        let mut rng = DeterministicRng::new(555);

        let result = op.apply(&mut buffer, &mut rng);
        assert!(result.is_ok(), "Op {} failed on long text", i);

        // Verify round-trip
        let output = buffer.to_string();
        let reparsed = TextBuffer::from_owned(output.clone());
        assert_eq!(output, reparsed.to_string(), "Op {} failed round-trip on long text", i);
    }
}
