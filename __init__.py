from zoo import (
    typogre,
    mim1c,
    jargoyle,
    redactyl,
    reduple,
    rushmore,
    Glitchling,
    Gaggle,
    summon,
)
from util import SAMPLE_TEXT


__all__ = [
    "typogre",
    "mim1c",
    "jargoyle",
    "reduple",
    "rushmore",
    "redactyl",
    "summon",
    "Glitchling",
    "Gaggle",
    "SAMPLE_TEXT",
]


if __name__ == "__main__":
    # Example usage
    import verifiers as vf
    from openai import OpenAI
    from dlc import prime as gl

    openai = OpenAI()

    # redactyl.set_param("redaction_rate", 0.5)
    # jargoyle.set_param("replacement_rate", 0.25)

    # gaggle = summon(["reduple", "mim1c", "typogre", jargoyle, "rushmore", redactyl])
    # corrupted = gaggle(SAMPLE_TEXT)
    # print(SAMPLE_TEXT, end="\n\n")
    # print(gaggle.pretty_diff(SAMPLE_TEXT), end="\n\n")
    # print(corrupted)

    # env = load_environment("alphabet-sort")
    # x = env.evaluate(client=openai, model="gpt-4.1-nano", num_examples=100)
    # dx = env.make_dataset(x).to_dict()
    # print(sum(dx["weighted_reward"]))

    bare_env = vf.load_environment("alphabet-sort")
    x = bare_env.evaluate(client=openai, model="gpt-4.1-nano", num_examples=10)
    dx = bare_env.make_dataset(x).to_dict()
    original = 100 * sum(dx["reward"]) / len(dx["reward"])

    easy_env = gl.load_environment("alphabet-sort")
    y = easy_env.evaluate(client=openai, model="gpt-4.1-nano", num_examples=10)
    dy = easy_env.make_dataset(y).to_dict()
    easy = 100 * sum(dy["reward"]) / len(dy["reward"])
    easy_drop = 100 * (original - easy) / original

    crazy_env = gl.load_environment("alphabet-sort", CR=gl.CR.Four)
    z = crazy_env.evaluate(client=openai, model="gpt-4.1-nano", num_examples=10)
    dz = crazy_env.make_dataset(z).to_dict()
    crazy = 100 * sum(dz["reward"]) / len(dz["reward"])
    crazy_drop = 100 * (original - crazy) / original

    print(f"Base Environment:   {original:.1f}%")
    print(f"Glitchlings (CR 1): {easy:.1f}% ({easy_drop:.1f}% drop)")
    print(f"Glitchlings (CR 4): {crazy:.1f}% ({crazy_drop:.1f}% drop)")
