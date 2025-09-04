import difflib

SAMPLE_TEXT = "One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked."


def string_diffs(a: str, b: str):
    """
    Compare two strings using SequenceMatcher and return
    grouped adjacent opcodes (excluding 'equal' tags).

    Each element is a tuple: (tag, a_text, b_text).
    """
    sm = difflib.SequenceMatcher(None, a, b)
    ops = []
    buffer = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            # flush any buffered operations before skipping
            if buffer:
                ops.append(buffer)
                buffer = []
            continue

        # append operation to buffer
        buffer.append((tag, a[i1:i2], b[j1:j2]))

    # flush trailing buffer
    if buffer:
        ops.append(buffer)

    return ops
