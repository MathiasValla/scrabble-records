#!/usr/bin/env python3
"""Check and consolidate every numerical row of the manuscript's bound audit."""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
CERT = ROOT / "certificates" / "upper_bound_audit.json"
EXACT = {
    "NWL23": {1: 213, 2: 459, 3: 882, 4: 1130, 5: 1401, 6: 1723, 7: 1786},
    "CSW24": {1: 225, 2: 483, 3: 912, 4: 1349, 5: 1478, 6: 1721, 7: 1787},
}
EXPECTED_FIRST = {
    ("NWL23", 2): 81, ("CSW24", 2): 256,
    ("NWL23", 3): 4, ("CSW24", 3): 7,
    ("NWL23", 4): 10, ("CSW24", 4): 3,
    ("NWL23", 5): 2, ("CSW24", 5): 12,
    ("NWL23", 6): 9, ("CSW24", 6): 21,
    ("NWL23", 7): 87, ("CSW24", 7): 168,
}
THRESHOLD = {
    ("NWL23", 2): 459, ("CSW24", 2): 459,
    ("NWL23", 3): 883, ("CSW24", 3): 883,
    ("NWL23", 4): 1131, ("CSW24", 4): 1350,
    ("NWL23", 5): 1402, ("CSW24", 5): 1479,
    ("NWL23", 6): 1724, ("CSW24", 6): 1722,
    ("NWL23", 7): 1737, ("CSW24", 7): 1738,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative: str):
    return json.loads((ROOT / relative).read_text())


def metadata(relative: str) -> dict[str, int]:
    values = {}
    for line in (ROOT / relative).read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].isdigit():
            values[fields[0]] = int(fields[1])
    return values


def artifact(relative: str) -> dict[str, str]:
    path = ROOT / relative
    assert path.is_file(), relative
    return {"path": relative, "sha256": digest(path)}


def main() -> None:
    if not __debug__:
        raise SystemExit("Do not run a proof verifier with Python assertions disabled.")

    parser = argparse.ArgumentParser()
    parser.add_argument("--check-existing", action="store_true")
    args = parser.parse_args()

    one = load("output/one_tile_certificate.json")
    assert one["schema"] == "one-tile-certificate-v1"
    rows = []
    for name, deletion_count, pairs in (
        ("NWL23", 240528, 36941),
        ("CSW24", 387172, 27520),
    ):
        bound = one["upper_bounds"][name]
        scan = metadata(f"output/{name}_k2_upper.txt")
        assert scan["deletion_valid_cross"] == deletion_count
        assert bound["checked_pairs_above_live_bound"] == pairs
        assert bound["best_score"] == EXACT[name][1]
        rows.append({
            "dictionary": name,
            "k": 1,
            "threshold_prebonus": None,
            "first_stage": deletion_count,
            "exact_stage": pairs,
            "conclusion": {"largest_score": EXACT[name][1]},
            "artifacts": [
                artifact("output/one_tile_certificate.json"),
                artifact(f"output/{name}_k2_upper.txt"),
            ],
        })

    for name in ("NWL23", "CSW24"):
        for k in range(2, 8):
            upper_path = f"output/{name}_k{k}_upper.txt"
            scan = metadata(upper_path)
            assert scan["k"] == k
            assert scan["threshold"] == THRESHOLD[name, k]
            assert scan["independent_upper_at_least_threshold"] == EXPECTED_FIRST[name, k]
            prebonus_exact = EXACT[name][k] - (50 if k == 7 else 0)
            assert scan["threshold"] <= prebonus_exact + 1
            artifacts = [artifact(upper_path)]

            if k == 2:
                path = f"output/{name}_k2_products.json"
                result = load(path)
                exact_stage = len(result["records"])
                assert exact_stage == (1 if name == "NWL23" else 369)
                assert result["best_prebonus"] == EXACT[name][k]
                conclusion = {"largest_product": result["best_prebonus"]}
                artifacts.append(artifact(path))
            elif name == "NWL23" and k in (3, 4, 5):
                path = f"output/NWL23_k{k}_cpp_exclusion.json"
                result = load(path)
                assert result["remaining"] == 0
                assert len(result["summaries"]) == EXPECTED_FIRST[name, k]
                exact_stage = 0
                conclusion = {"product_enumeration_remaining": 0}
                artifacts.append(artifact(path))
                for item in result["summaries"]:
                    lines = (ROOT / item["output"]).read_text().splitlines()
                    assert not any(line.startswith("record ") for line in lines)
                    artifacts.append(artifact(item["output"]))
            elif (name, k) == ("CSW24", 3):
                path = "output/CSW24_k3_verified_upper.json"
                result = load(path)
                exact_stage = result["products"]
                assert exact_stage == 11350 and result["upper_bound"] == 912
                conclusion = {"largest_product": 912}
                artifacts.append(artifact(path))
            elif (name, k) == ("CSW24", 4):
                path = "output/CSW24_k4_verified_upper.json"
                result = load(path)
                exact_stage = result["remaining_products"]
                assert exact_stage == 0 and result["upper_bound"] == 1349
                conclusion = {"resource_product_remaining": 0}
                artifacts.append(artifact(path))
            elif (name, k) == ("CSW24", 5):
                path = "output/CSW24_k5_verified_upper.json"
                result = load(path)
                exact_stage = result["products"]
                assert exact_stage == 10 and result["remaining"] == 0
                assert len(result["records"]) == 10 and result["upper_bound"] == 1478
                conclusion = {"centre_occupancy_remaining": 0}
                artifacts.append(artifact(path))
            elif (name, k) == ("NWL23", 6):
                product_path = "output/NWL23_k6_products.json"
                completion_path = "output/NWL23_k6_completion_safe.json"
                products = load(product_path)
                result = load(completion_path)
                exact_stage = len(products["records"])
                reasons = Counter(item["reason"] for item in result["records"])
                assert exact_stage == 20 and len(result["records"]) == 20
                assert reasons == {"uncompletable row": 4,
                                   "mandatory singleton hook impossible": 16}
                assert result["remaining"] == 0
                conclusion = {"after_rows": 16, "after_hooks": 0}
                artifacts += [artifact(product_path), artifact(completion_path)]
            elif (name, k) == ("CSW24", 6):
                screen_path = "output/CSW24_k6_screened.json"
                verified_path = "output/CSW24_k6_verified_upper.json"
                screen = load(screen_path)
                result = load(verified_path)
                exact_stage = screen["products"]
                assert exact_stage == 15809
                assert screen["reasons"] == {"uncompletable row": 12457,
                                             "mandatory singleton hook impossible": 3345}
                assert len(screen["remaining"]) == 7
                assert result["remaining"] == 0 and result["upper_bound"] == 1721
                conclusion = {"after_rows": 3352, "after_hooks": 7,
                              "after_shared_bag": 0}
                artifacts += [artifact(screen_path), artifact(verified_path)]
            elif (name, k) == ("NWL23", 7):
                stage_path = "output/seven_completion_stage1.json"
                hooks_path = "output/seven_hooks/summary.json"
                tail_path = "output/seven_tail/rec74_reproduced.json"
                stage = load(stage_path)
                hooks = load(hooks_path)
                tail = load(tail_path)
                exact_stage = stage["products"]
                assert exact_stage == 3748
                assert stage["after_row_completion"] == 255
                assert stage["after_singleton_hooks"] == 34
                assert hooks["complete"] and len(hooks["reports"]) == 34
                assert sum(item["bases"] for item in hooks["reports"]) == 193
                assert tail["reduced_horizontal_bases"] == 193
                assert tail["total_connectivity_cores_enumerated"] == 24293
                assert tail["total_core_letter_assignments_checked"] == 5518820
                assert tail["surviving_core_assignments"] == 0 and tail["status"] == "OK"
                conclusion = {"after_rows": 255, "after_hooks": 34,
                              "reduced_boards": 193, "connecting_cores": 24293,
                              "core_assignments": 5518820, "remaining": 0}
                artifacts += [artifact(stage_path), artifact(hooks_path), artifact(tail_path)]
            elif (name, k) == ("CSW24", 7):
                screen_path = "output/CSW24_k7_screened.json"
                verified_path = "output/CSW24_k7_verified_upper.json"
                screen = load(screen_path)
                result = load(verified_path)
                exact_stage = screen["products"]
                assert exact_stage == 420538
                assert screen["reasons"] == {"uncompletable row": 408785,
                                             "mandatory singleton hook impossible": 11731,
                                             "centre forced empty": 13}
                assert len(screen["remaining"]) == 9
                assert result["remaining"] == 0 and result["upper_bound"] == 1787
                conclusion = {"after_rows": 11753, "after_hooks": 22,
                              "after_centre": 9, "after_shared_bag": 0}
                artifacts += [artifact(screen_path), artifact(verified_path)]
            else:
                raise AssertionError((name, k))

            rows.append({
                "dictionary": name,
                "k": k,
                "threshold_prebonus": THRESHOLD[name, k],
                "first_stage": EXPECTED_FIRST[name, k],
                "exact_stage": exact_stage,
                "conclusion": conclusion,
                "artifacts": artifacts,
            })
            if "largest_product" not in conclusion:
                assert THRESHOLD[name, k] == prebonus_exact + 1

    rows.sort(key=lambda item: (item["k"], item["dictionary"] != "NWL23"))
    assert len(rows) == 14
    payload = {
        "schema": "upper-bound-audit-v1",
        "claim": "Every numerical row in the manuscript's finite-reduction audit table is checked against its generated artifacts.",
        "exact_maxima": {name: {str(k): value for k, value in scores.items()}
                          for name, scores in EXACT.items()},
        "rows": rows,
    }
    if args.check_existing:
        assert json.loads(CERT.read_text()) == payload
        print(f"VERIFIED: 14 upper-bound audit rows; matched {CERT.relative_to(ROOT)}")
    else:
        CERT.parent.mkdir(exist_ok=True)
        temporary = CERT.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        temporary.replace(CERT)
        print(f"VERIFIED: 14 upper-bound audit rows; wrote {CERT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
