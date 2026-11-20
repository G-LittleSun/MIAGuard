from miaguard.masked_mia import _recover_masks


class _InvalidJsonClient:
    def generate_json(self, *args, **kwargs):
        raise RuntimeError("invalid JSON")


def test_recover_masks_scores_invalid_model_json_as_empty_answers() -> None:
    answers = _recover_masks(
        "[Mask_1] text [Mask_2]",
        2,
        ["retrieved context"],
        _InvalidJsonClient(),  # type: ignore[arg-type]
        "model",
        128,
    )

    assert answers == ["", ""]
