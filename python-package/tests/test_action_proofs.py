"""Proof-of-test gate (Constitution 4A.1 rules 2 and 3).

`tested=True` is a claim. This module refuses the claim unless `proof_test`
names a test that really exists and really mentions the action_id, either in
the test function's own source or in the test module's `PROVES` tuple.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from teledrive import action_registry

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

PROVES = ()  # this module proves no action itself


def _split(proof_test: str) -> tuple[Path, str]:
    assert "::" in proof_test, f"proof_test must be 'tests/<file>.py::<function>': {proof_test!r}"
    rel, func = proof_test.split("::", 1)
    return PACKAGE_ROOT / rel, func


def _module_proves(tree: ast.Module) -> set[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "PROVES" in targets and isinstance(node.value, (ast.Tuple, ast.List)):
                return {
                    element.value
                    for element in node.value.elts
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                }
    return set()


TESTED = [s for s in action_registry.ACTION_SPECS if s.tested]


def test_no_spec_claims_tested_without_proof():
    """Replaces the old blanket 'everything is ready' assertion."""
    offenders = [s.action_id for s in action_registry.ACTION_SPECS if s.tested and not s.proof_test]
    assert offenders == []


def test_tested_true_is_rejected_without_a_proof_test():
    with pytest.raises(ValueError):
        action_registry.ActionSpec(
            action_id="x.y", handler_name="h_x", service_path="a.b",
            label_key="btn.refresh", section="settings",
            implemented=True, tested=True,
        )


def test_tested_true_is_rejected_without_implemented():
    with pytest.raises(ValueError):
        action_registry.ActionSpec(
            action_id="x.y", handler_name="h_x", service_path="a.b",
            label_key="btn.refresh", section="settings",
            implemented=False, tested=True, proof_test="tests/test_queue.py::test_priority",
        )


@pytest.mark.parametrize("spec", TESTED, ids=lambda s: s.action_id)
def test_proof_test_exists_and_mentions_the_action(spec):
    path, func_name = _split(spec.proof_test)
    assert path.exists(), f"{spec.action_id}: missing proof file {path}"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert func_name in functions, f"{spec.action_id}: {func_name} not in {path.name}"
    body = ast.get_source_segment(source, functions[func_name]) or ""
    mentioned = spec.action_id in body or spec.action_id in _module_proves(tree)
    assert mentioned, (
        f"{spec.action_id}: {spec.proof_test} never mentions the action_id "
        "(add it to the test body or to the module-level PROVES tuple)"
    )


def test_unready_actions_are_declared_honestly():
    for spec in action_registry.unready_specs():
        assert spec.proof_test == "", f"{spec.action_id}: unready spec must not name a proof"
