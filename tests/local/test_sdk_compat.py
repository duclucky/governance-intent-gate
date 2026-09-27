import json
import os
import subprocess
from pathlib import Path

from genlayer_py.abi import calldata
from genlayer_py.contracts.utils import make_calldata_object
from genlayer_py.types import CalldataAddress
from scripts import check


ROOT = Path(__file__).parents[2]
CONTRACT = ROOT / "contracts" / "governance_intent_gate.py"
LINTER = ROOT / ".venv" / "Scripts" / "genvm-lint.exe"
ADDRESS_A = CalldataAddress("0x" + "11" * 20)
ADDRESS_B = CalldataAddress("0x" + "22" * 20)
ADDRESS_C = CalldataAddress("0x" + "33" * 20)


WRITE_SAMPLES = {
    "activate": [],
    "attest_batch": ["case-1", 1, "[]", "a" * 64],
    "attest_proposal": ["case-1", "[]", "b" * 64],
    "configure": ["profile-v1", "dao:demo", ADDRESS_A, ADDRESS_B, ADDRESS_C, "decoder-v1", "transfer"],
    "consume_authorization": ["case-1", 1, "c" * 64, 1],
    "create_case": ["case-1", "proposal-1", 1, 1_893_456_000, ""],
    "expire_case": ["case-1"],
    "request_review": ["case-1"],
    "retry_review": ["case-1"],
}


def local_schema():
    result = subprocess.run(
        [str(LINTER), "schema", str(CONTRACT), "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)["schema"]


def test_every_write_has_native_sdk_calldata_roundtrip():
    schema = local_schema()
    writes = {name for name, method in schema["methods"].items() if not method["readonly"]}
    assert writes == set(WRITE_SAMPLES)
    for method, args in WRITE_SAMPLES.items():
        encoded = calldata.encode(make_calldata_object(method=method, args=args))
        decoded = calldata.decode(encoded)
        assert decoded[""] == method
        assert decoded.get("args", []) == args


def test_configure_addresses_remain_native_address_values():
    encoded = calldata.encode(make_calldata_object(method="configure", args=WRITE_SAMPLES["configure"]))
    decoded = calldata.decode(encoded)
    assert all(isinstance(decoded["args"][index], CalldataAddress) for index in (2, 3, 4))


def test_check_runner_exposes_venv_tools_on_path(monkeypatch):
    observed = {}

    def fake_run(*args, **kwargs):
        observed.update(kwargs)
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(check.subprocess, "run", fake_run)
    check.run([check.LINTER, "--version"])

    first_path_entry = observed["env"]["PATH"].split(os.pathsep)[0]
    assert Path(first_path_entry).resolve() == check.SCRIPTS.resolve()
