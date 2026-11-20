from miaguard.ia_policy_experiment import select_ia_policy


def test_policy_selection_prefers_less_severe_action_on_equal_accuracy() -> None:
    metrics = {
        "restrict_context": {"attack_accuracy_after": 0.8},
        "summarize_context": {"attack_accuracy_after": 0.6},
        "no_context_answer": {"attack_accuracy_after": 0.5},
        "deny_sensitive_answer": {"attack_accuracy_after": 0.5},
    }

    assert select_ia_policy(metrics) == "no_context_answer"


def test_policy_selection_prioritizes_lower_attack_accuracy() -> None:
    metrics = {
        "restrict_context": {"attack_accuracy_after": 0.8},
        "summarize_context": {"attack_accuracy_after": 0.45},
        "no_context_answer": {"attack_accuracy_after": 0.5},
        "deny_sensitive_answer": {"attack_accuracy_after": 0.5},
    }

    assert select_ia_policy(metrics) == "summarize_context"
