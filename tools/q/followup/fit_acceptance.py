"""Calibrate simple fit acceptance rules on pilot families and freeze before evaluation."""
import argparse
import json
from pathlib import Path
from statistics import mean
from time import perf_counter


def read(path):
    return json.loads(path.read_text())


def iou(record):
    return mean(value["iou"] for value in record["held_out"].values())


def cases(previous):
    rows = []
    for path in sorted((previous / "eval").glob("MBLab*.json")):
        doc = read(path)
        results = doc["results"]
        for count in (1, 4):
            native = results.get(f"native_{count}")
            if native:
                rows.append(("development", doc["subject"], count, native["native_report"],
                             iou(results["bootstrap"]), iou(native)))
    for record in read(previous / "holdout-results.json"):
        fixture = record["fixture"]
        if fixture["left_forearm_bend_deg"]:
            continue
        for count in (1, 4):
            native = record["native"][str(count)]
            held = lambda condition: mean(v for k, v in native[condition]["iou"].items() if float(k) != 0)
            report = read(previous / "holdout-native" / f"{fixture['subject']}-{count}" / "benchmark.json")
            rows.append(("evaluation", fixture["identity"], count, report, held("bootstrap"), held("neutral")))
    return rows


def make_rows(items):
    rows = []
    for split, name, count, report, baseline, fitted in items:
        fit = report["fit"]
        scores = list(fit["per_view_iou"].values())
        rows.append(dict(split=split, fixture=name, views=count, bootstrap_iou=baseline, fitted_iou=fitted,
            training_gain=fit["fitted_iou"] - fit["bootstrap_iou"], saturation=len(fit["saturated"]),
            control_l2=sum(v * v for v in fit["controls"].values()) ** .5,
            min_training_view_iou=min(scores), elapsed_fit_seconds=report["fit_seconds"]))
    return rows


def accept(row, rule):
    return (row["training_gain"] >= rule["gain"] and row["saturation"] <= rule["saturation"]
            and row["control_l2"] <= rule["l2"] and row["min_training_view_iou"] >= rule["min_view"])


def evaluate(rows, rule):
    scored = []
    for row in rows:
        start = perf_counter()
        accepted = accept(row, rule)
        elapsed = perf_counter() - start
        change = row["fitted_iou"] - row["bootstrap_iou"]
        truth = "beneficial" if change > .001 else "harmful" if change < -.001 else "tie"
        scored.append(row | dict(accepted=accepted, effect=truth, overhead_seconds=elapsed,
                                 selected_iou=row["fitted_iou"] if accepted else row["bootstrap_iou"]))
    return scored


def run(previous, output):
    rows = make_rows(cases(previous))
    dev = [r for r in rows if r["split"] == "development"]
    test = [r for r in rows if r["split"] == "evaluation"]
    rules = [{"gain": g, "saturation": s, "l2": n, "min_view": m}
             for g in (0, .01, .03, .06, 1) for s in (0, 3, 20) for n in (.5, 1, 3) for m in (0, .5, .6)]
    objective = lambda rule: mean(r["selected_iou"] for r in evaluate(dev, rule))
    selected = max(rules, key=objective)
    output.write_text(json.dumps(dict(rule=selected, development=evaluate(dev, selected),
                                      evaluation=evaluate(test, selected), tested_rules=len(rules)),
                                 indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
