import re

import pytest

from miaguard import defense_dataset


def masked(text):
    return defense_dataset.draft_unique_masked_query(text)


def test_skips_repeated_words_case_insensitively_and_synchronizes_answer():
    query, answers = masked('Clement met CLEMENT; Belichick coaches coaches.')
    assert answers == ['Belichick']
    passage = query.split('}: ', 1)[1]
    assert passage.count('[MASK]') == 1
    assert not re.search(r'\bBelichick\b', query, re.IGNORECASE)
    assert 'Clement met CLEMENT' in query
    assert 'Respond only with JSON {"answers":["word"]}' in query


def test_word_boundary_does_not_confuse_word_with_longer_word():
    query, answers = masked('coach coaches coaches')
    assert answers == ['coach']
    assert '[MASK] coaches coaches' in query


@pytest.mark.parametrize('text', ['', '123 456', 'Clement CLEMENT', '[MASK] football'])
def test_rejects_no_eligible_word_or_existing_mask(text):
    with pytest.raises(ValueError):
        masked(text)


def test_lists_unique_candidates_with_positions_and_uses_explicit_choice():
    text = 'Clement met CLEMENT; Belichick coaches coaches.'
    options = defense_dataset.masked_word_candidates(text)
    assert options == [{'word': 'Belichick', 'start': 21, 'end': 30}]
    query, answers = defense_dataset.draft_masked_query_for_word(text, 'Belichick')
    assert answers == ['Belichick']
    assert 'Clement met CLEMENT; [MASK] coaches coaches.' in query
    with pytest.raises(ValueError):
        defense_dataset.draft_masked_query_for_word(text, 'Clement')
