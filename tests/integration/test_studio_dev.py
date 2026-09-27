import json
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.chains import studio_devnet

from scripts.deployment import read_env_value


ROOT = Path(__file__).parents[2]
DEPLOYMENT = ROOT / "docs" / "evidence" / "studio-dev" / "deployment.json"
LIFECYCLE = ROOT / "docs" / "evidence" / "studio-dev" / "lifecycle.json"
CONTRACT = ROOT / "contracts" / "governance_intent_gate.py"


def test_finalized_studio_dev_state_matches_canonical_evidence():
    deployment = json.loads(DEPLOYMENT.read_text(encoding="utf-8"))
    lifecycle = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    account = create_account(read_env_value("STUDIONET_PRIVATE_KEY"))
    client = create_client(chain=studio_devnet, account=account)
    address = deployment["contract_address"]
    assert client.get_contract_schema(address) == client.get_contract_schema_for_code(CONTRACT.read_bytes())

    case_id = lifecycle["case_id"]
    case = json.loads(client.read_contract(address=address, function_name="get_case", args=[case_id]))
    assert case["status"] == "CONSUMED"
    assert case["consumed"] is True
    assert case["normalized_result"]["verdict"] == "CONFORMANT"
    assert client.read_contract(
        address=address,
        function_name="can_consume",
        args=[case_id, case["batch_revision"], case["batch_digest"], 1],
    ) is False
