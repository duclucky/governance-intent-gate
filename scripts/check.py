import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".venv" / "Scripts"
PYTHON = SCRIPTS / "python.exe"
LINTER = SCRIPTS / "genvm-lint.exe"
CONTRACT = ROOT / "contracts" / "governance_intent_gate.py"
EXPECTED_METHODS = {
    "activate",
    "attest_batch",
    "attest_proposal",
    "can_consume",
    "configure",
    "consume_authorization",
    "create_case",
    "expire_case",
    "get_case",
    "get_case_count",
    "get_case_id",
    "get_profile",
    "request_review",
    "retry_review",
}


def run(command, *, capture=False):
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    return subprocess.run(
        [str(item) for item in command],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=capture,
        text=True,
        encoding="utf-8",
    )


def main():
    if not PYTHON.exists() or not LINTER.exists():
        raise SystemExit("Install the pinned requirements into .venv before running checks")
    run([LINTER, "check", CONTRACT])
    run([LINTER, "typecheck", CONTRACT, "--strict"])
    schema_result = run([LINTER, "schema", CONTRACT, "--json"], capture=True)
    schema = json.loads(schema_result.stdout)["schema"]
    methods = schema.get("methods", {})
    if set(methods) != EXPECTED_METHODS:
        raise SystemExit("Contract schema method set does not match the locked interface")
    if any(method.get("payable", False) for method in methods.values()):
        raise SystemExit("The locked no-value design contains a payable method")
    run([PYTHON, "-m", "pytest", "tests/direct", "tests/local", "-q"])
    print(json.dumps({"ok": True, "contract_count": 1, "method_count": len(methods)}))


if __name__ == "__main__":
    main()
