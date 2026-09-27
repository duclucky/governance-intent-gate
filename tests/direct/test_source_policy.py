import ast
from pathlib import Path


CONTRACT = Path(__file__).parents[2] / "contracts" / "governance_intent_gate.py"
RUNNER = "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng"


def source():
    return CONTRACT.read_text(encoding="ascii")


def test_contract_source_policy():
    text = source()
    assert text.splitlines()[0] == f'# {{ "Depends": "{RUNNER}" }}'
    assert "py-genlayer:test" not in text
    assert "py-genlayer:latest" not in text
    assert "gl.vm.run_nondet(" in text
    assert ".payable" not in text
    assert "emit_transfer" not in text
    assert "@gl.evm.contract_interface" not in text

    tree = ast.parse(text)
    contract_classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(isinstance(base, ast.Attribute) and base.attr == "Contract" for base in node.bases)
    ]
    assert [node.name for node in contract_classes] == ["GovernanceIntentGate"]
