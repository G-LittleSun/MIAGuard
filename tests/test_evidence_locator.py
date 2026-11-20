from miaguard.defense_contracts import Evidence
from miaguard.evidence_locator import locate_evidence


def evidence(doc, parent, text):
    return Evidence(doc, parent, text, 0.5)


def test_locates_nonfirst_source_from_online_text():
    candidates = (evidence('one', 'one', 'Unrelated news about a baseball game.'),
                  evidence('two', 'two', 'The council voted on the proposal after a lengthy public hearing.'))
    result = locate_evidence('Passage: The council voted on the proposal after a lengthy public hearing.', candidates)
    assert result.status == 'located'
    assert result.parent_ids == frozenset({'two'})


def test_masks_break_fragments_and_insufficient_evidence_does_not_guess():
    candidates = (evidence('one', 'one', 'A city council voted on the proposal.'),)
    assert locate_evidence('The [Mask_1] voted [Mask_2].', candidates).status == 'unresolved'
    assert locate_evidence('no quoted source here', ()).status == 'unresolved'


def test_multiple_parents_are_ambiguous_but_duplicate_parent_is_not():
    text = 'The council voted on the proposal after a lengthy public hearing.'
    query = 'Passage: ' + text
    ambiguous = (evidence('a', 'parent_a', text), evidence('b', 'parent_b', text))
    assert locate_evidence(query, ambiguous).status == 'ambiguous'
    same_parent = (evidence('a', 'parent_a', text), evidence('b', 'parent_a', text))
    result = locate_evidence(query, same_parent)
    assert result.status == 'located'
    assert result.parent_ids == frozenset({'parent_a'})
