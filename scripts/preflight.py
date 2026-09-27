import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.request import Request, urlopen
from datetime import datetime, timezone

from genlayer_py.abi import calldata
from genlayer_py.contracts.utils import make_calldata_object
from genlayer_py.types import CalldataAddress


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "governance_intent_gate.py"
LINTER = ROOT / ".venv" / "Scripts" / "genvm-lint.exe"
EVIDENCE = ROOT / "docs" / "evidence" / "studio-dev" / "target-network-preflight.json"
RPC_URL = "https://studio-dev.genlayer.com/api"
CHAIN_ID = 61997


def rpc_call(method, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 GenLayer-Preflight"},
    )
    with urlopen(request, timeout=45) as response:
        body = json.loads(response.read().decode("utf-8"))
    if "error" in body:
        error = body["error"]
        raise RuntimeError(f"{method} failed with RPC code {error.get('code')}: {error.get('message')}")
    return body["result"]


def local_schema():
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [str(LINTER), "schema", str(CONTRACT), "--json"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)["schema"]


def fee_estimate():
    executable = shutil.which("genlayer.cmd" if os.name == "nt" else "genlayer")
    if executable is None:
        raise RuntimeError("GenLayer CLI is not installed")
    completed = subprocess.run(
        [executable, "estimate-fees", "--rpc", RPC_URL, "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    value = json.loads(completed.stdout)
    distribution = value["distribution"]
    policy = value["policy"]
    return {
        "fee_value": value["feeValue"],
        "distribution": {
            "appeal_rounds": distribution["appealRounds"],
            "execution_budget_per_round": distribution["executionBudgetPerRound"],
            "leader_timeunits": distribution["leaderTimeunitsAllocation"],
            "max_price_gen_per_time_unit": distribution["maxPriceGenPerTimeUnit"],
            "receipt_fee_max_gas_price": distribution["receiptFeeMaxGasPrice"],
            "rotations": distribution["rotations"],
            "storage_fee_max_gas_price": distribution["storageFeeMaxGasPrice"],
            "validator_timeunits": distribution["validatorTimeunitsAllocation"],
        },
        "policy": {
            "enabled": policy["enabled"],
            "execution_budget_floor": policy["executionBudgetFloor"],
            "gen_per_time_unit": policy["genPerTimeUnit"],
            "receipt_gas_price": policy["receiptGasPrice"],
            "storage_unit_price": policy["storageUnitPrice"],
            "time_unit_overlay_bps": policy["timeUnitOverlayBps"],
        },
    }


def abi_roundtrip_count():
    address_a = CalldataAddress("0x" + "11" * 20)
    address_b = CalldataAddress("0x" + "22" * 20)
    address_c = CalldataAddress("0x" + "33" * 20)
    samples = {
        "activate": [],
        "attest_batch": ["case-1", 1, "[]", "a" * 64],
        "attest_proposal": ["case-1", "[]", "b" * 64],
        "configure": ["profile-v1", "dao:demo", address_a, address_b, address_c, "decoder-v1", "transfer"],
        "consume_authorization": ["case-1", 1, "c" * 64, 1],
        "create_case": ["case-1", "proposal-1", 1, 1_893_456_000, ""],
        "expire_case": ["case-1"],
        "request_review": ["case-1"],
        "retry_review": ["case-1"],
    }
    for method, args in samples.items():
        decoded = calldata.decode(calldata.encode(make_calldata_object(method=method, args=args)))
        if decoded[""] != method or decoded.get("args", []) != args:
            raise RuntimeError(f"ABI roundtrip failed for {method}")
    return len(samples)


def main():
    source = CONTRACT.read_bytes()
    text = source.decode("ascii")
    first_nonblank = next(line for line in text.splitlines() if line.strip())
    dependency = re.fullmatch(r'# \{ "Depends": "([^"]+)" \}', first_nonblank)
    if dependency is None:
        raise SystemExit("Depends declaration is not the first nonblank line")

    expected_schema = local_schema()
    remote_schema = rpc_call("gen_getContractSchemaForCode", ["0x" + source.hex()])
    if remote_schema != expected_schema:
        raise SystemExit("Studio Dev schema differs from the locked local schema")
    chain_id_hex = rpc_call("eth_chainId", [])
    if int(chain_id_hex, 16) != CHAIN_ID:
        raise SystemExit("Studio Dev chain ID mismatch")

    methods = remote_schema["methods"]
    write_methods = sorted(name for name, definition in methods.items() if not definition["readonly"])
    evidence = {
        "schema_version": "1.0",
        "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "network": "studio-dev",
        "rpc_url": RPC_URL,
        "chain_id": CHAIN_ID,
        "contract_source_sha256": hashlib.sha256(source).hexdigest(),
        "runner": dependency.group(1),
        "schema_match": True,
        "method_count": len(methods),
        "write_methods": write_methods,
        "native_abi_roundtrip_write_count": abi_roundtrip_count(),
        "gas_price_wei": str(int(rpc_call("eth_gasPrice", []), 16)),
        "fee_estimate": fee_estimate(),
        "capability_boundaries": {
            "local_llm_json_decode_and_fail_closed_paths": "covered by direct tests",
            "live_llm_consensus": "not proven by read-only preflight; requires finalized lifecycle evidence",
            "web_fetch": "not used by this contract",
        },
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "chain_id": CHAIN_ID, "method_count": len(methods), "write_count": len(write_methods)}))


if __name__ == "__main__":
    main()
