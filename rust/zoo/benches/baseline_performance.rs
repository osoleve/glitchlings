use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use pprof::criterion::{Output, PProfProfiler};
use _zoo_rust::{
    DeleteRandomWordsOp, DeterministicRng, GlitchOp, GlitchOperation,
    ReduplicateWordsOp, SwapAdjacentWordsOp, TextBuffer,
};

/// Generate test text of approximately target_chars length
fn generate_test_text(target_chars: usize) -> String {
    // Average word length is ~5 chars, plus 1 for space = 6 chars per word
    let word_count = target_chars / 6;

    let words = vec![
        "the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
        "performance", "optimization", "requires", "careful", "measurement",
        "benchmarking", "critical", "infrastructure", "improvements",
        "tokenization", "segmentation", "operations", "pipeline",
    ];

    let mut text = String::with_capacity(target_chars);
    for i in 0..word_count {
        if i > 0 {
            text.push(' ');
        }
        text.push_str(words[i % words.len()]);
    }

    text
}

/// Typical operation mix that represents common usage
fn create_typical_pipeline() -> Vec<GlitchOperation> {
    vec![
        GlitchOperation::Reduplicate(ReduplicateWordsOp {
            rate: 0.05,
            unweighted: false,
        }),
        GlitchOperation::Delete(DeleteRandomWordsOp {
            rate: 0.03,
            unweighted: false,
        }),
        GlitchOperation::SwapAdjacent(SwapAdjacentWordsOp {
            rate: 0.04,
        }),
    ]
}

/// Benchmark tokenization (TextBuffer creation from string)
fn bench_tokenization(c: &mut Criterion) {
    let mut group = c.benchmark_group("tokenization");

    for size in [10_000, 50_000, 100_000, 500_000].iter() {
        let text = generate_test_text(*size);
        let actual_len = text.chars().count();

        group.throughput(Throughput::Elements(actual_len as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(format!("{}chars", actual_len)),
            &text,
            |b, text| {
                b.iter(|| {
                    let buffer = TextBuffer::from_str(black_box(text));
                    black_box(buffer);
                });
            },
        );
    }

    group.finish();
}

/// Benchmark full pipeline execution with typical operations
fn bench_pipeline_typical(c: &mut Criterion) {
    let mut group = c.benchmark_group("pipeline_typical");

    for size in [10_000, 50_000, 100_000, 500_000].iter() {
        let text = generate_test_text(*size);
        let actual_len = text.chars().count();
        let ops = create_typical_pipeline();

        group.throughput(Throughput::Elements(actual_len as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(format!("{}chars", actual_len)),
            &text,
            |b, text| {
                b.iter(|| {
                    let mut buffer = TextBuffer::from_str(black_box(text));
                    let mut rng = DeterministicRng::new(42);

                    for op in &ops {
                        let _ = op.apply(&mut buffer, &mut rng);
                    }

                    black_box(buffer);
                });
            },
        );
    }

    group.finish();
}

/// Benchmark individual reindex operation
fn bench_reindex(c: &mut Criterion) {
    let mut group = c.benchmark_group("reindex");

    for size in [10_000, 50_000, 100_000, 500_000].iter() {
        let text = generate_test_text(*size);
        let actual_len = text.chars().count();

        group.throughput(Throughput::Elements(actual_len as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(format!("{}chars", actual_len)),
            &text,
            |b, text| {
                // Pre-create buffer outside measurement
                let buffer = TextBuffer::from_str(text);

                b.iter(|| {
                    let mut buffer = buffer.clone();
                    // Force reindex by doing a no-op mutation
                    // This will trigger reindex in current implementation
                    let word_count = buffer.word_count();
                    if word_count > 0 {
                        let word = buffer.word_segment(0).map(|s| s.text().to_string()).unwrap_or_default();
                        let _ = buffer.replace_word(0, &word);
                    }
                    black_box(buffer);
                });
            },
        );
    }

    group.finish();
}

/// Benchmark heavy word replacement (worst case for current implementation)
fn bench_heavy_replace(c: &mut Criterion) {
    let mut group = c.benchmark_group("heavy_replace");

    for size in [10_000, 50_000, 100_000, 500_000].iter() {
        let text = generate_test_text(*size);
        let actual_len = text.chars().count();

        group.throughput(Throughput::Elements(actual_len as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(format!("{}chars", actual_len)),
            &text,
            |b, text| {
                b.iter(|| {
                    let mut buffer = TextBuffer::from_str(black_box(text));
                    let mut rng = DeterministicRng::new(42);

                    // Heavy reduplicate - this will call reindex many times
                    let op = ReduplicateWordsOp {
                        rate: 0.2, // 20% of words
                        unweighted: false,
                    };

                    let _ = op.apply(&mut buffer, &mut rng);
                    black_box(buffer);
                });
            },
        );
    }

    group.finish();
}

/// Benchmark heavy word deletion (worst case for current implementation)
fn bench_heavy_delete(c: &mut Criterion) {
    let mut group = c.benchmark_group("heavy_delete");

    for size in [10_000, 50_000, 100_000, 500_000].iter() {
        let text = generate_test_text(*size);
        let actual_len = text.chars().count();

        group.throughput(Throughput::Elements(actual_len as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(format!("{}chars", actual_len)),
            &text,
            |b, text| {
                b.iter(|| {
                    let mut buffer = TextBuffer::from_str(black_box(text));
                    let mut rng = DeterministicRng::new(42);

                    // Heavy delete - with deferred reindexing, reindex() is now called only once at the end via reindex_if_needed()
                    let op = DeleteRandomWordsOp {
                        rate: 0.2, // 20% of words
                        unweighted: false,
                    };

                    let _ = op.apply(&mut buffer, &mut rng);
                    black_box(buffer);
                });
            },
        );
    }

    group.finish();
}

/// Benchmark mixed operations on large text
fn bench_mixed_ops_large(c: &mut Criterion) {
    let mut group = c.benchmark_group("mixed_ops_500k");

    let text = generate_test_text(500_000);
    let actual_len = text.chars().count();

    group.throughput(Throughput::Elements(actual_len as u64));
    group.bench_function("typical_mix", |b| {
        b.iter(|| {
            let mut buffer = TextBuffer::from_str(black_box(&text));
            let mut rng = DeterministicRng::new(42);

            let ops = create_typical_pipeline();
            for op in &ops {
                let _ = op.apply(&mut buffer, &mut rng);
            }

            black_box(buffer);
        });
    });

    group.finish();
}

/// Benchmark scaling: measure how performance scales with input size
fn bench_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("scaling");

    // Test 2x scaling: 250k vs 500k should be close to 2x time (ideally ≤2.4x)
    for size in [250_000, 500_000].iter() {
        let text = generate_test_text(*size);
        let actual_len = text.chars().count();

        group.throughput(Throughput::Elements(actual_len as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(format!("{}chars", actual_len)),
            &text,
            |b, text| {
                b.iter(|| {
                    let mut buffer = TextBuffer::from_str(black_box(text));
                    let mut rng = DeterministicRng::new(42);

                    let ops = create_typical_pipeline();
                    for op in &ops {
                        let _ = op.apply(&mut buffer, &mut rng);
                    }

                    black_box(buffer);
                });
            },
        );
    }

    group.finish();
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .with_profiler(PProfProfiler::new(100, Output::Flamegraph(None)))
        .sample_size(10)  // Reduced for faster baseline
        .warm_up_time(std::time::Duration::from_secs(1));
    targets =
        bench_tokenization,
        bench_pipeline_typical,
        bench_reindex,
        bench_heavy_replace,
        bench_heavy_delete,
        bench_mixed_ops_large,
        bench_scaling
}

criterion_main!(benches);
