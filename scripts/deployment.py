import hashlib
import base64
import json
from pathlib import Path
import re
from datetime import datetime, timezone

from genlayer_py import create_account, create_client
from genlayer_py.chains import studio_devnet
from genlayer_py.transactions.actions import is_successful


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "governance_intent_gate.py"
EVIDENCE_DIR = ROOT / "docs" / "evidence" / "studio-dev"
STATE_PATH = EVIDENCE_DIR / "deployment-state.json"
DEPLOYMENT_PATH = EVIDENCE_DIR / "deployment.json"
NETWORK = "studio-dev"
CHAIN_ID = 61997
RPC_URL = "https://studio-dev.genlayer.com/api"
RUNNER = "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng"
REGISTRY_RECORD = "afd015abb32e8ab185a8376c56f301a5173e18c22fbea88c2c345c9cb3829c52"
ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
TX_ID = re.compile(r"^0x[0-9a-fA-F]{64}$")


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_hash(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_env_value(name):
    candidates = [ROOT / ".env", ROOT.parents[2] / ".env"]
    for path in candidates:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == name and value.strip():
                return value.strip().strip('"').strip("'")
    raise RuntimeError(f"Required environment variable {name} is absent from project and authorized root .env files")


def pick(mapping, *paths):
    for path in paths:
        current = mapping
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current is not None:
            return current
    return None


def project_receipt(receipt, tx_id):
    lifecycle = receipt.get("lifecycle") if isinstance(receipt, dict) else None
    lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
    contract_address = pick(
        receipt,
        ("data", "contract_address"),
        ("data", "contractAddress"),
        ("tx_data_decoded", "contract_address"),
        ("txDataDecoded", "contractAddress"),
    )
    leader_receipt = pick(receipt, ("consensus_data", "leader_receipt"), ("consensusData", "leaderReceipt"))
    if isinstance(leader_receipt, list):
        leader_receipt = leader_receipt[0] if leader_receipt else None
    leader_receipt = leader_receipt if isinstance(leader_receipt, dict) else {}
    execution = pick(receipt, ("tx_execution_result_name",), ("txExecutionResultName",))
    if execution is None and leader_receipt.get("execution_result") == "SUCCESS":
        execution = "FINISHED_WITH_RETURN"
    result = {
        "transaction_id": tx_id,
        "contract_address": contract_address,
        "lifecycle_state": lifecycle.get("state"),
        "lifecycle_outcome": lifecycle.get("outcome"),
        "consensus_result": pick(receipt, ("result_name",), ("resultName",)),
        "execution_result": execution,
    }
    if not TX_ID.fullmatch(str(result["transaction_id"])):
        raise RuntimeError("Invalid transaction ID in receipt projection")
    if not ADDRESS.fullmatch(str(result["contract_address"])):
        raise RuntimeError("Invalid contract address in receipt projection")
    return result


def project_write_receipt(receipt, tx_id):
    lifecycle = receipt.get("lifecycle") if isinstance(receipt, dict) else None
    lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
    leader_receipt = pick(receipt, ("consensus_data", "leader_receipt"), ("consensusData", "leaderReceipt"))
    if isinstance(leader_receipt, list):
        leader_receipt = leader_receipt[0] if leader_receipt else None
    leader_receipt = leader_receipt if isinstance(leader_receipt, dict) else {}
    execution = pick(receipt, ("tx_execution_result_name",), ("txExecutionResultName",))
    if execution is None and leader_receipt.get("execution_result") == "SUCCESS":
        execution = "FINISHED_WITH_RETURN"
    if not TX_ID.fullmatch(str(tx_id)):
        raise RuntimeError("Invalid transaction ID in receipt projection")
    return {
        "transaction_id": tx_id,
        "lifecycle_state": lifecycle.get("state"),
        "lifecycle_outcome": lifecycle.get("outcome"),
        "consensus_result": pick(receipt, ("result_name",), ("resultName",)),
        "execution_result": execution,
    }


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    source = CONTRACT.read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    identity = {
        "network": NETWORK,
        "chain_id": CHAIN_ID,
        "rpc_url": RPC_URL,
        "contract_source_sha256": source_hash,
        "runner": RUNNER,
        "registry_record_hash": REGISTRY_RECORD,
    }
    fingerprint = canonical_hash(identity)
    private_key = read_env_value("STUDIONET_PRIVATE_KEY")
    account = create_account(private_key)
    client = create_client(chain=studio_devnet, account=account)

    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.is_file() else None
    if state is not None and state.get("deployment_fingerprint") != fingerprint:
        raise RuntimeError("Existing deployment state belongs to a different immutable fingerprint")

    if state is None:
        estimate = client.estimate_transaction_fees()
        fees = {"distribution": estimate["distribution"], "feeValue": estimate["feeValue"]}
        tx_id = client.deploy_contract(code=source, account=account, fees=fees)
        if not TX_ID.fullmatch(str(tx_id)):
            raise RuntimeError("Deployment did not return a valid GenLayer transaction ID")
        state = {
            **identity,
            "deployment_fingerprint": fingerprint,
            "deployer": account.address,
            "transaction_id": tx_id,
            "submitted_at": utc_now(),
            "fee_reserve_wei": str(estimate["feeValue"]),
            "status": "SUBMITTED",
        }
        save(STATE_PATH, state)
        print(json.dumps({"status": "SUBMITTED", "transaction_id": tx_id}))
    else:
        tx_id = state["transaction_id"]
        print(json.dumps({"status": "RECOVERING", "transaction_id": tx_id}))

    receipt = client.wait_for_finalization(tx_id, interval=5000, retries=120, full_transaction=True)
    projection = project_receipt(receipt, tx_id)
    if projection["lifecycle_state"] != "finalized" or not is_successful(receipt):
        raise RuntimeError(
            "Deployment finalized without successful execution: "
            + json.dumps({key: projection[key] for key in ("lifecycle_state", "lifecycle_outcome", "execution_result")})
        )
    deployed_code = client.provider.make_request(
        method="gen_getContractCode", params=[projection["contract_address"]]
    )["result"]
    deployed_source_hash = hashlib.sha256(base64.b64decode(deployed_code)).hexdigest()
    if deployed_source_hash != source_hash:
        raise RuntimeError("Deployed source bytes do not match the immutable source fingerprint")
    deployment = {
        **identity,
        "schema_version": "1.0",
        "deployment_fingerprint": fingerprint,
        "deployer": account.address,
        "transaction_id": tx_id,
        "contract_address": projection["contract_address"],
        "deployed_source_sha256": deployed_source_hash,
        "submitted_at": state["submitted_at"],
        "finalized_at": utc_now(),
        "lifecycle_state": projection["lifecycle_state"],
        "lifecycle_outcome": projection["lifecycle_outcome"],
        "consensus_result": projection["consensus_result"],
        "execution_result": projection["execution_result"],
        "fee_reserve_wei": state["fee_reserve_wei"],
        "fee_use_refund": "Not exposed by the sanitized Studio Dev receipt; no amount is claimed.",
        "explorer_url": "https://explorer-studio-dev.genlayer.com/tx/" + tx_id,
        "contract_explorer_url": "https://explorer-studio-dev.genlayer.com/address/" + projection["contract_address"],
    }
    save(DEPLOYMENT_PATH, deployment)
    state["status"] = "FINALIZED"
    state["contract_address"] = projection["contract_address"]
    save(STATE_PATH, state)
    print(json.dumps({
        "status": "FINALIZED",
        "transaction_id": tx_id,
        "contract_address": projection["contract_address"],
        "execution_result": projection["execution_result"],
    }))


if __name__ == "__main__":
    main()
