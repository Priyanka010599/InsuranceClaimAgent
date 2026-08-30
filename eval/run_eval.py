from eval.cases import CASES
from main import graph


def run_case(case: dict) -> dict:
    config = {"configurable": {"thread_id": f"eval-{case['name']}"}}
    initial_state = {
        "raw_text": case["raw_text"],
        "claim_data": None,
        "validation_errors": [],
        "policy_context": "",
        "policy_violations": [],
        "risk_score": 0,
        "risk_flags": [],
        "decision": None,
        "human_decision": None,
        "notification": None,
        "extraction_error": None,
    }

    result = graph.invoke(initial_state, config=config)
    actual = result.get("decision")

    return {
        "name": case["name"],
        "expected": case["expected_decision"],
        "actual": actual,
        "passed": actual == case["expected_decision"],
        "policy_violations": result.get("policy_violations"),
        "risk_score": result.get("risk_score"),
    }


def main() -> None:
    results = [run_case(case) for case in CASES]
    passed = sum(r["passed"] for r in results)

    print(f"\n{'CASE':<28} {'EXPECTED':<14} {'ACTUAL':<14} RESULT")
    print("-" * 70)
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"{r['name']:<28} {r['expected']:<14} {str(r['actual']):<14} {mark}")
        if not r["passed"]:
            print(f"    policy_violations={r['policy_violations']}")
            print(f"    risk_score={r['risk_score']}")

    print("-" * 70)
    print(f"Score: {passed}/{len(results)} ({passed / len(results):.0%})")


if __name__ == "__main__":
    main()
