import pytest
from teledrive.state_machine import assert_transition, IllegalTransition, LEGAL


def test_all_legal_transitions_pass():
    for s, targets in LEGAL.items():
        for t in targets:
            assert_transition(s, t)


def test_illegal_transitions_raise():
    with pytest.raises(IllegalTransition):
        assert_transition("Uploaded", "Downloading")
    with pytest.raises(IllegalTransition):
        assert_transition("Pending", "Uploaded")
    with pytest.raises(IllegalTransition):
        assert_transition("Deleted", "Pending")
