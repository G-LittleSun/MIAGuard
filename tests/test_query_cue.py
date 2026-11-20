from miaguard.query_cue import query_cues


def test_long_quotation_and_context_presence_are_both_required():
    passage = 'The report describes a company whose recent changes affect customers around the world today'
    assert query_cues(f'Does this: "{passage}" appear in the context?') == ('quoted_context_check',)
    assert query_cues(f'Please summarize "{passage}" based on the context.') == ()
    assert query_cues('Does "short quote" appear in the context?') == ()


def test_multiple_distinct_masks_and_recovery_intent_are_required():
    assert query_cues('Recover the original words: [Mask_1] [Mask_2] [Mask_3]') == ('masked_recovery',)
    assert query_cues('Give an original story with [Mask_1] and [Mask_1].') == ()
    assert query_cues('Describe placeholders [Mask_1] [Mask_2] [Mask_3].') == ()
