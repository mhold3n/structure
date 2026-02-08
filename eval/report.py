import json
import glob
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from kernels import get_kernel
from models.kernel_io import KernelInput


def run_regression_suite():
    print("Running Regression Suite...")
    results = []

    files = glob.glob("eval/regression_locked/*.jsonl")
    for file in files:
        print(f"Loading {file}...")
        with open(file) as f:
            for line in f:
                if not line.strip():
                    continue
                case = json.loads(line)

                # Run Kernel
                kernel_id = case["kernel"]
                kernel_cls = get_kernel(kernel_id)
                if not kernel_cls:
                    print(f"ERROR: Kernel {kernel_id} not found")
                    results.append({"id": case["id"], "status": "ERROR", "msg": "Kernel not found"})
                    continue

                kernel = kernel_cls()
                output = kernel.execute(
                    KernelInput(kernel_id=kernel_id, request_id="eval", args=case["args"])
                )

                # Check Result
                if not output.success:
                    results.append({"id": case["id"], "status": "FAIL", "msg": output.error})
                    continue

                # Simple subset match for now
                expected = case["expected"]
                actual = output.result

                # Flatten check (naive)
                success = True
                failed_keys = []

                # TODO: robust deep comparison.
                # For now, just check specific keys in expected exist and match in actual
                def check(exp, act):
                    for k, v in exp.items():
                        if k not in act:
                            return False
                        if isinstance(v, dict) and isinstance(act[k], dict):
                            if not check(v, act[k]):
                                return False
                        elif act[k] != v:
                            return False
                    return True

                if check(expected, actual):
                    results.append({"id": case["id"], "status": "PASS"})
                else:
                    results.append(
                        {
                            "id": case["id"],
                            "status": "FAIL",
                            "msg": f"Expected {expected}, Got {actual}",
                        }
                    )

    # Report
    print("\n--- Regression Report ---")
    passes = len([r for r in results if r["status"] == "PASS"])
    total = len(results)
    print(f"Total: {total}, Pass: {passes}, Fail: {total - passes}")

    for r in results:
        print(f"{r['id']}: {r['status']} {r.get('msg', '')}")

    if passes != total:
        sys.exit(1)


if __name__ == "__main__":
    run_regression_suite()
