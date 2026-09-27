import hashlib
import json
import os
from pathlib import Path
import tempfile

import pytest


# genlayer-test 0.30.0rc2 unlinks a file that is still mapped to fd 0. That is
# legal on POSIX and raises WinError 32 on Windows. Keep the file until process
# exit; the test process owns no durable data and Windows removes temp files
# during normal cleanup. This compatibility shim changes no VM semantics.
if os.name == "nt":
    import gltest.direct.loader as _direct_loader

    def _windows_inject_message_to_fd0(vm):
        calldata = _direct_loader.import_calldata()
        Address = _direct_loader.import_address()
        sender_addr = Address(vm.sender) if isinstance(vm.sender, bytes) else vm.sender
        contract_addr = Address(vm._contract_address) if isinstance(vm._contract_address, bytes) else vm._contract_address
        origin_addr = Address(vm.origin) if isinstance(vm.origin, bytes) else vm.origin
        encoded = calldata.encode({
            "contract_address": contract_addr,
            "sender_address": sender_addr,
            "origin_address": origin_addr,
            "stack": [],
            "value": vm._value,
            "datetime": vm._datetime,
            "is_init": False,
            "chain_id": vm._chain_id,
            "entry_kind": 0,
            "entry_data": b"",
            "entry_stage_data": None,
        })
        fd, _path = tempfile.mkstemp(prefix="gltest-fd0-")
        os.write(fd, encoded)
        os.lseek(fd, 0, os.SEEK_SET)
        vm._original_stdin_fd = os.dup(0)
        os.dup2(fd, 0)
        os.close(fd)

    _direct_loader._inject_message_to_fd0 = _windows_inject_message_to_fd0


# genlayer-test 0.30.0rc2 predates the runner's current JSON decoding contract:
# it eagerly converts mocked JSON text to a dict, while SDK v0.3-rc9 decodes the
# response itself and therefore requires text. Preserve the wire-shaped text in
# direct tests; production still uses response_format="json" as required.
import gltest.direct.wasi_mock as _wasi_mock


def _sdk_rc9_llm_mock(vm, data):
    prompt = data.get("prompt", "")
    response = vm._match_llm_mock(prompt)
    if response is not None:
        return {"ok": response}
    if getattr(vm, "_strict_mock_mode", False):
        raise _wasi_mock.MockNotFoundError("No LLM mock matched prompt")
    live = getattr(vm, "_live_llm_handler", None)
    if live is not None:
        return {"ok": live(prompt)}
    return {"ok": ""}


_wasi_mock._handle_llm_request = _sdk_rc9_llm_mock


CONTRACT = Path(__file__).parents[2] / "contracts" / "governance_intent_gate.py"
DEADLINE = 1_893_456_000  # 2030-01-01T00:00:00Z


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def address(value):
    import gltest.direct.loader as loader
    return loader.import_address()(value) if isinstance(value, bytes) else value


@pytest.fixture
def directives():
    text = canonical([
        {"id": "d-transfer", "text": "Transfer 10 tokens to the grants multisig."},
        {"id": "d-limit", "text": "Set the daily treasury limit to 100 tokens."},
    ])
    return text, digest(text)


@pytest.fixture
def effects():
    text = canonical([
        {"id": "e-transfer", "operation": "CALL", "selector": "transfer", "summary": "Transfer 10 tokens to the grants multisig", "target": "treasury-token", "value": "0"},
        {"id": "e-limit", "operation": "CALL", "selector": "set_limit", "summary": "Set daily treasury limit to 100 tokens", "target": "treasury-policy", "value": "0"},
    ])
    return text, digest(text)


@pytest.fixture
def conformant_result():
    return {
        "verdict": "CONFORMANT",
        "directive_ids": ["d-limit", "d-transfer"],
        "effect_ids": ["e-limit", "e-transfer"],
        "edges": [
            {"directive_id": "d-limit", "effect_id": "e-limit"},
            {"directive_id": "d-transfer", "effect_id": "e-transfer"},
        ],
        "discrepancy_codes": [],
    }


@pytest.fixture
def gate(direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie):
    direct_vm.check_pickling = True
    direct_vm.strict_mocks = True
    direct_vm.sender = direct_owner
    contract = direct_deploy(str(CONTRACT))
    contract.configure(
        "profile-v1",
        "dao:demo",
        address(direct_alice),
        address(direct_bob),
        address(direct_charlie),
        "decoder-v1",
        "set_limit,transfer",
    )
    contract.activate()
    return contract


def open_ready_case(direct_vm, gate, direct_alice, direct_bob, directives, effects, case_id="case-1"):
    direct_vm.warp("2029-12-31T23:59:00Z")
    gate.create_case(case_id, "proposal-7", 1, DEADLINE, "non-authoritative context")
    direct_vm.sender = direct_alice
    gate.attest_proposal(case_id, directives[0], directives[1])
    direct_vm.sender = direct_bob
    gate.attest_batch(case_id, 1, effects[0], effects[1])
    return case_id
