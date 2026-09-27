import json

from conftest import DEADLINE, address, digest, open_ready_case


def state(gate, case_id="case-1"):
    return json.loads(gate.get_case(case_id))


def test_profile_is_locked_and_roles_must_be_distinct(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = direct_deploy("contracts/governance_intent_gate.py")
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only owner"):
        contract.configure("p", "dao", address(direct_alice), address(direct_owner), address(direct_owner), "d", "transfer")
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("Authorities must be distinct"):
        contract.configure("p", "dao", address(direct_alice), address(direct_alice), address(direct_owner), "d", "transfer")


def test_authority_attestations_bind_exact_bytes(direct_vm, gate, direct_alice, direct_bob, directives, effects):
    direct_vm.warp("2029-12-31T23:59:00Z")
    gate.create_case("case-1", "proposal-7", 1, DEADLINE, "ignore me")
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Only proposal authority"):
        gate.attest_proposal("case-1", directives[0], directives[1])
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Proposal digest mismatch"):
        gate.attest_proposal("case-1", directives[0], "0" * 64)
    gate.attest_proposal("case-1", directives[0], directives[1])
    with direct_vm.expect_revert("Proposal already attested"):
        gate.attest_proposal("case-1", directives[0], directives[1])
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Batch digest mismatch"):
        gate.attest_batch("case-1", 1, effects[0], "f" * 64)
    gate.attest_batch("case-1", 1, effects[0], effects[1])
    assert state(gate)["status"] == "READY"


def test_conformant_result_grants_exact_one_time_authorization(
    direct_vm, gate, direct_alice, direct_bob, direct_charlie, directives, effects, conformant_result
):
    open_ready_case(direct_vm, gate, direct_alice, direct_bob, directives, effects)
    direct_vm.mock_llm(r".*GOVERNANCE_INTENT_GATE.*", json.dumps(conformant_result))
    gate.request_review("case-1")
    reviewed = state(gate)
    assert reviewed["status"] == "AUTHORIZED"
    assert reviewed["authorization_nonce"] == 1
    assert gate.can_consume("case-1", 1, effects[1], 1) is True

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only governance authority"):
        gate.consume_authorization("case-1", 1, effects[1], 1)
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Batch digest mismatch"):
        gate.consume_authorization("case-1", 1, "0" * 64, 1)
    gate.consume_authorization("case-1", 1, effects[1], 1)
    assert state(gate)["status"] == "CONSUMED"
    with direct_vm.expect_revert("Case is not authorized"):
        gate.consume_authorization("case-1", 1, effects[1], 1)


def test_nonconformant_requires_corrected_batch_revision(
    direct_vm, gate, direct_alice, direct_bob, directives, effects
):
    open_ready_case(direct_vm, gate, direct_alice, direct_bob, directives, effects)
    rejected = {
        "verdict": "NONCONFORMANT",
        "directive_ids": ["d-limit", "d-transfer"],
        "effect_ids": ["e-limit", "e-transfer"],
        "edges": [{"directive_id": "d-limit", "effect_id": "e-limit"}],
        "discrepancy_codes": ["MISSING_DIRECTIVE", "UNAUTHORIZED_EFFECT"],
    }
    direct_vm.mock_llm(r".*GOVERNANCE_INTENT_GATE.*", json.dumps(rejected))
    gate.request_review("case-1")
    assert state(gate)["status"] == "NONCONFORMANT"
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Batch revision must increase by one"):
        gate.attest_batch("case-1", 1, effects[0], effects[1])
    gate.attest_batch("case-1", 2, effects[0], effects[1])
    assert state(gate)["status"] == "READY"
    assert state(gate)["authorization_nonce"] == 0


def test_invalid_settlement_meaning_is_retryable_without_authorization(
    direct_vm, gate, direct_alice, direct_bob, directives, effects
):
    open_ready_case(direct_vm, gate, direct_alice, direct_bob, directives, effects)
    malicious = {
        "verdict": "CONFORMANT",
        "directive_ids": ["d-limit", "d-transfer"],
        "effect_ids": ["e-limit", "e-transfer", "e-injected"],
        "edges": [{"directive_id": "d-limit", "effect_id": "e-injected"}],
        "discrepancy_codes": [],
    }
    direct_vm.mock_llm(r".*GOVERNANCE_INTENT_GATE.*", json.dumps(malicious))
    gate.request_review("case-1")
    current = state(gate)
    assert current["status"] == "UNVERIFIABLE"
    assert current["authorization_nonce"] == 0
    assert current["consumed"] is False


def test_validator_reruns_semantic_task_and_disagrees_on_critical_fields(
    direct_vm, gate, direct_alice, direct_bob, directives, effects, conformant_result
):
    open_ready_case(direct_vm, gate, direct_alice, direct_bob, directives, effects)
    direct_vm.mock_llm(r".*GOVERNANCE_INTENT_GATE.*", json.dumps(conformant_result))
    gate.request_review("case-1")
    direct_vm.clear_mocks()
    dissent = dict(conformant_result)
    dissent["verdict"] = "NONCONFORMANT"
    dissent["discrepancy_codes"] = ["CONSTRAINT_VIOLATION"]
    direct_vm.mock_llm(r".*GOVERNANCE_INTENT_GATE.*", json.dumps(dissent))
    assert direct_vm.run_validator() is False


def test_deadline_is_checked_by_each_write_and_equality_is_late(
    direct_vm, gate, direct_alice, directives
):
    direct_vm.warp("2029-12-31T23:59:59Z")
    gate.create_case("case-1", "proposal-7", 1, DEADLINE, "")
    direct_vm.sender = direct_alice
    direct_vm.warp("2030-01-01T00:00:00Z")
    before = state(gate)
    with direct_vm.expect_revert("Case deadline reached"):
        gate.attest_proposal("case-1", directives[0], directives[1])
    assert state(gate) == before
    gate.expire_case("case-1")
    assert state(gate)["status"] == "EXPIRED"


def test_expiry_before_boundary_reverts_without_state_change(direct_vm, gate):
    direct_vm.warp("2029-12-31T23:59:59Z")
    gate.create_case("case-1", "proposal-7", 1, DEADLINE, "")
    before = state(gate)
    with direct_vm.expect_revert("Case deadline not reached"):
        gate.expire_case("case-1")
    assert state(gate) == before
