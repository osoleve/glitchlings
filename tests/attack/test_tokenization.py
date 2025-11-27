import importlib.util

import pytest

from glitchlings.attack.tokenization import HuggingFaceTokenizerWrapper

if not importlib.util.find_spec("tokenizers"):
    pytest.skip("tokenizers not installed", allow_module_level=True)


def test_hf_wrapper_decode_respects_bpe_artifacts():
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tokenizer.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(special_tokens=["[UNK]"], vocab_size=50, min_frequency=1)
    tokenizer.train_from_iterator(["hello world"], trainer=trainer)

    wrapper = HuggingFaceTokenizerWrapper(tokenizer)
    tokens, ids = wrapper.encode("hello world")

    decoded = wrapper.decode(tokens)

    assert decoded == tokenizer.decode(ids)
    assert decoded.startswith(" ")
    assert decoded.strip() == "hello world"


def test_hf_wrapper_decode_handles_wordpiece_prefixes():
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers

    vocab = {"[UNK]": 0, "play": 1, "##ing": 2}
    tokenizer = Tokenizer(
        models.WordPiece(
            vocab=vocab,
            unk_token="[UNK]",
            continuing_subword_prefix="##",
        )
    )
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    tokenizer.decoder = decoders.WordPiece(prefix="##")

    wrapper = HuggingFaceTokenizerWrapper(tokenizer)
    tokens, ids = wrapper.encode("playing")

    assert tokens == ["play", "##ing"]
    assert wrapper.decode(tokens) == "playing"
    assert wrapper.decode(tokens) == tokenizer.decode(ids)
