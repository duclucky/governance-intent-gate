import hashlib
import json
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.chains import studio_devnet
from genlayer_py.transactions.actions import is_successful
from genlayer_py.types import CalldataAddress

from deployment import (
    DEPLOYMENT_PATH,
    EVIDENCE_DIR,
    RPC_URL,
    project_write_receipt,
    read_env_value,
    save,
    utc_now,
)


STATE_PATH = EVIDENCE_DIR / "lifecycle-state.json"
EVIDENCE_PATH = EVIDENCE_DIR / "lifecycle.json"
CASE_ID = "portal-demo-29264dde"
DEADLINE = 1_893_456_000
MAX_REVIEW_ATTEMPTS = 2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(client, contract, method, args=None):
    value = client.read_contract(address=contract, function_name=method, args=args or [])
    return json.loads(value)


def finalized_write(state, name, client, account, contract, method, args):
    transactions = state.setdefault("transactions", {})
    checkpoint = transactions.get(name)
    if checkpoint is None:
        estimate = client.estimate_transaction_fees_for_write(
            address=contract,
            function_name=method,
            account=account,
            args=args,
        )
        fees = {"distribution": estimate["distribution"], "feeValue": estimate["feeValue"]}
        tx_id = client.write_contract(
            address=contract,
            function_name=method,
            account=account,
            args=args,
            fees=fees,
        )
        checkpoint = {
            "method": method,
            "transaction_id": tx_id,
            "submitted_at": utc_now(),
            "fee_reserve_wei": str(estimate["feeValue"]),
            "status": "SUBMITTED",
        }
        transactions[name] = checkpoint
        save(STATE_PATH, state)
        print(json.dumps({"step": name, "status": "SUBMITTED", "transaction_id": tx_id}), flush=True)
    else:
        tx_id = checkpoint["transaction_id"]
        print(json.dumps({"step": name, "status": "RECOVERING", "transaction_id": tx_id}), flush=True)

    receipt = client.wait_for_finalization(tx_id, interval=5000, retries=120, full_transaction=True)
    projection = project_write_receipt(receipt, tx_id)
    if projection["lifecycle_state"] != "finalized" or not is_successful(receipt):
        raise RuntimeError(f"{name} did not finalize successfully: {json.dumps(projection)}")
    checkpoint.update(projection)
    checkpoint["status"] = "FINALIZED"
    checkpoint["finalized_at"] = utc_now()
    checkpoint["fee_use_refund"] = "Not exposed by the sanitized Studio Dev receipt; no amount is claimed."
    save(STATE_PATH, state)
    print(json.dumps({"step": name, "status": "FINALIZED", "execution_result": projection["execution_result"]}), flush=True)


def main():
    deployment = json.loads(DEPLOYMENT_PATH.read_text(encoding="utf-8"))
    contract = deployment["contract_address"]
    owner = create_account(read_env_value("STUDIONET_PRIVATE_KEY"))
    proposal = create_account(read_env_value("STUDIONET_INTEGRATOR_PRIVATE_KEY"))
    decoder = create_account(read_env_value("STUDIONET_STEWARD_PRIVATE_KEY"))
    if len({owner.address.lower(), proposal.address.lower(), decoder.address.lower()}) != 3:
        raise RuntimeError("Lifecycle authorities must be three distinct addresses")
    clients = {
        "owner": create_client(chain=studio_devnet, account=owner),
        "proposal": create_client(chain=studio_devnet, account=proposal),
        "decoder": create_client(chain=studio_devnet, account=decoder),
    }
    owner_client = clients["owner"]
    expected_schema = owner_client.get_contract_schema_for_code(
        (Path(__file__).resolve().parents[1] / "contracts" / "governance_intent_gate.py").read_bytes()
    )
    deployed_schema = owner_client.get_contract_schema(contract)
    if deployed_schema != expected_schema:
        raise RuntimeError("Deployed schema does not match the exact source schema")

    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.is_file() else {
        "schema_version": "1.0",
        "network": "studio-dev",
        "chain_id": 61997,
        "contract_address": contract,
        "deployment_fingerprint": deployment["deployment_fingerprint"],
        "case_id": CASE_ID,
        "review_retry_budget": MAX_REVIEW_ATTEMPTS,
        "transactions": {},
    }
    if state.get("contract_address", "").lower() != contract.lower() or state.get("case_id") != CASE_ID:
        raise RuntimeError("Existing lifecycle checkpoint is bound to another contract or case")

    profile = read_json(owner_client, contract, "get_profile")
    if not profile["configured"]:
        finalized_write(
            state,
            "configure",
            owner_client,
            owner,
            contract,
            "configure",
            [
                "governance-intent-v1",
                "dao:portal-demo",
                CalldataAddress(proposal.address),
                CalldataAddress(decoder.address),
                CalldataAddress(owner.address),
                "decoder-v1",
                "set_limit,transfer",
            ],
        )
        profile = read_json(owner_client, contract, "get_profile")
    expected_roles = {
        "proposal_authority": proposal.address.lower(),
        "decoder_authority": decoder.address.lower(),
        "governance_authority": owner.address.lower(),
    }
    if any(profile[key].lower() != value for key, value in expected_roles.items()):
        raise RuntimeError("Configured authority binding does not match the immutable lifecycle plan")
    if not profile["active"]:
        finalized_write(state, "activate", owner_client, owner, contract, "activate", [])

    try:
        case = read_json(owner_client, contract, "get_case", [CASE_ID])
    except Exception:
        finalized_write(
            state,
            "create_case",
            owner_client,
            owner,
            contract,
            "create_case",
            [CASE_ID, "proposal-portal-1", 1, DEADLINE, "Synthetic integration fixture; not adoption evidence."],
        )
        case = read_json(owner_client, contract, "get_case", [CASE_ID])

    directives = canonical([
        {"id": "d-limit", "text": "Set the daily treasury transfer limit to 100 tokens."},
        {"id": "d-transfer", "text": "Transfer 10 tokens to the grants multisig."},
    ])
    effects = canonical([
        {"id": "e-limit", "operation": "CALL", "selector": "set_limit", "summary": "Set the daily treasury transfer limit to 100 tokens.", "target": "treasury-policy", "value": "0"},
        {"id": "e-transfer", "operation": "CALL", "selector": "transfer", "summary": "Transfer 10 tokens to the grants multisig.", "target": "treasury-token", "value": "0"},
    ])
    proposal_digest = digest(directives)
    batch_digest = digest(effects)

    if not case["proposal_digest"]:
        finalized_write(state, "attest_proposal", clients["proposal"], proposal, contract, "attest_proposal", [CASE_ID, directives, proposal_digest])
        case = read_json(owner_client, contract, "get_case", [CASE_ID])
    if not case["batch_digest"]:
        finalized_write(state, "attest_batch", clients["decoder"], decoder, contract, "attest_batch", [CASE_ID, 1, effects, batch_digest])
        case = read_json(owner_client, contract, "get_case", [CASE_ID])
    if case["proposal_digest"] != proposal_digest or case["batch_digest"] != batch_digest:
        raise RuntimeError("Canonical case commitments do not match the exact lifecycle fixtures")

    while case["status"] in ("READY", "UNVERIFIABLE") and int(case["review_attempt"]) < MAX_REVIEW_ATTEMPTS:
        attempt = int(case["review_attempt"]) + 1
        method = "request_review" if case["status"] == "READY" else "retry_review"
        finalized_write(state, f"{method}_{attempt}", owner_client, owner, contract, method, [CASE_ID])
        case = read_json(owner_client, contract, "get_case", [CASE_ID])
    if case["status"] != "AUTHORIZED":
        state["terminal_semantic_status"] = case["status"]
        state["normalized_result"] = case["normalized_result"]
        save(STATE_PATH, state)
        raise RuntimeError(f"Semantic review did not authorize within retry budget: {case['status']}")

    authorized_snapshot = {
        "status": case["status"],
        "review_attempt": case["review_attempt"],
        "authorization_nonce": case["authorization_nonce"],
        "batch_revision": case["batch_revision"],
        "batch_digest": case["batch_digest"],
        "normalized_result": case["normalized_result"],
    }
    if not case["consumed"]:
        finalized_write(
            state,
            "consume_authorization",
            owner_client,
            owner,
            contract,
            "consume_authorization",
            [CASE_ID, case["batch_revision"], case["batch_digest"], case["authorization_nonce"]],
        )
        case = read_json(owner_client, contract, "get_case", [CASE_ID])
    if case["status"] != "CONSUMED" or not case["consumed"]:
        raise RuntimeError("Canonical one-time authorization was not consumed")
    can_consume = owner_client.read_contract(
        address=contract,
        function_name="can_consume",
        args=[CASE_ID, case["batch_revision"], case["batch_digest"], authorized_snapshot["authorization_nonce"]],
    )
    if can_consume is not False:
        raise RuntimeError("Consumed authorization remains available")

    lifecycle = {
        "schema_version": "1.0",
        "verified_at": utc_now(),
        "network": "studio-dev",
        "chain_id": 61997,
        "contract_address": contract,
        "case_id": CASE_ID,
        "exact_commitments": {"proposal_digest": proposal_digest, "batch_digest": batch_digest},
        "authority_addresses": expected_roles,
        "finalized_transactions": state["transactions"],
        "semantic_result": authorized_snapshot,
        "canonical_consequence": {
            "status": case["status"],
            "consumed": case["consumed"],
            "can_consume_after_consequence": can_consume,
            "meaning": "The exact digest/revision/nonce-bound internal authorization was consumed once.",
        },
        "boundaries": [
            "This synthetic lifecycle proves contract behavior on Studio Dev, not DAO adoption.",
            "The contract does not execute the modeled external calls or prove hidden runtime behavior.",
            "Fee reserve values are recorded per transaction; actual fee use/refund is not exposed and is not claimed.",
        ],
    }
    save(EVIDENCE_PATH, lifecycle)
    print(json.dumps({
        "status": "EVIDENCE_LOCKED",
        "case_status": case["status"],
        "semantic_verdict": authorized_snapshot["normalized_result"]["verdict"],
        "transaction_count": len(state["transactions"]),
    }), flush=True)


if __name__ == "__main__":
    main()
