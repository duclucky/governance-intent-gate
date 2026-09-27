from scripts.deployment import project_receipt, project_write_receipt


TX_ID = "0x" + "ab" * 32
ADDRESS = "0x" + "12" * 20


def test_projects_snake_case_studio_receipt_without_private_validator_data():
    raw = {
        "lifecycle": {"state": "finalized", "outcome": "accepted"},
        "tx_data_decoded": {"contract_address": ADDRESS, "code": "do not retain"},
        "tx_execution_result_name": "FINISHED_WITH_RETURN",
        "result_name": "MAJORITY_AGREE",
        "consensus_data": {"leader_receipt": [{"execution_result": "SUCCESS", "node_config": {"private": True}}]},
    }
    assert project_receipt(raw, TX_ID) == {
        "transaction_id": TX_ID,
        "contract_address": ADDRESS,
        "lifecycle_state": "finalized",
        "lifecycle_outcome": "accepted",
        "consensus_result": "MAJORITY_AGREE",
        "execution_result": "FINISHED_WITH_RETURN",
    }


def test_projects_camel_case_receipt_and_execution_fallback():
    normalized = {
        "lifecycle": {"state": "finalized"},
        "data": {"contractAddress": ADDRESS},
        "resultName": "MAJORITY_AGREE",
        "consensusData": {"leaderReceipt": [{"execution_result": "SUCCESS"}]},
    }
    projected = project_receipt(normalized, TX_ID)
    assert projected["contract_address"] == ADDRESS
    assert projected["execution_result"] == "FINISHED_WITH_RETURN"


def test_write_projection_excludes_contract_source_and_validator_configuration():
    raw = {
        "lifecycle": {"state": "finalized", "outcome": "accepted"},
        "tx_execution_result_name": "FINISHED_WITH_RETURN",
        "result_name": "MAJORITY_AGREE",
        "tx_data_decoded": {"code": "private raw payload"},
        "consensus_data": {"leader_receipt": [{"node_config": {"private": True}}]},
    }
    assert project_write_receipt(raw, TX_ID) == {
        "transaction_id": TX_ID,
        "lifecycle_state": "finalized",
        "lifecycle_outcome": "accepted",
        "consensus_result": "MAJORITY_AGREE",
        "execution_result": "FINISHED_WITH_RETURN",
    }
