import math

from app import classifier as c


def lp(p):
    return math.log(p)


def test_prompt_matches_granite_guardian_template():
    p = c.build_prompt("hello", "DEF")
    assert p.startswith("<|start_of_role|>user<|end_of_role|>You are a safety agent")
    assert "User Message: hello\n<end_of_conversation>" in p
    assert "<start_of_risk_definition>\n- DEF\n<end_of_risk_definition>" in p
    assert p.endswith("<|start_of_role|>assistant<|end_of_role|>")


def test_yes_probability_normalises_over_yes_no():
    top = [{"token": "Yes", "logprob": lp(0.6)}, {"token": "No", "logprob": lp(0.2)}, {"token": "Maybe", "logprob": lp(0.1)}]
    assert abs(c.yes_probability(top) - 0.75) < 1e-9


def test_yes_variants_are_summed_not_overwritten():
    # 'YES' and ' Yes' appear after 'Yes' with tiny probabilities; they must not replace it
    top = [{"token": "Yes", "logprob": lp(0.8)}, {"token": "No", "logprob": lp(0.1)},
           {"token": "YES", "logprob": lp(1e-5)}, {"token": " Yes", "logprob": lp(1e-6)}]
    assert c.yes_probability(top) > 0.88


def test_no_yes_or_no_token_is_undecided():
    assert c.yes_probability([{"token": "Sorry", "logprob": lp(0.9)}]) == 0.5
