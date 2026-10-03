#!/usr/bin/env python3
"""Build promtool tests from the actual Grafana render alert expressions.

python3 ci/render-alert-tests.py --output /tmp/render-alerts
cd /tmp/render-alerts && promtool test rules render-alert-tests.yml

Fixtures contain expected behavior, never copies of the production PromQL.
The native alert rules also use production `for` and labels. Grafana templated
annotations are intentionally omitted: promtool cannot render those templates.
"""
import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UIDS = frozenset(("cs2-render-failed", "cs2-render-disk-unknown",
                  "cs2-render-disk-low", "cs2-render-first-try-low"))


def load_rules(path):
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    result = {}
    for group in config["groups"]:
        for rule in group["rules"]:
            uid = rule["uid"]
            if uid not in UIDS:
                continue
            if uid in result:
                raise ValueError(f"duplicate rule uid: {uid}")
            data = {query["refId"]: query for query in rule["data"]}
            model = data[rule["condition"]]["model"]
            # These four rules use a filtered instant PromQL vector. The C
            # threshold accepts all their nonnegative samples, including zero.
            # Stop if provisioning changes to a different evaluator or chain;
            # otherwise native Prometheus would test a different condition.
            conditions = model.get("conditions", [])
            if (rule["condition"] != "C" or model.get("type") != "threshold" or
                    model.get("expression") != "A" or len(conditions) != 1 or
                    conditions[0]["evaluator"] != {"type": "gt", "params": [-1000000000]} or
                    data["A"]["datasourceUid"] == "__expr__" or
                    data["A"]["model"].get("instant") is not True or
                    rule["noDataState"] != "OK"):
                raise ValueError(f"{uid}: unsupported Grafana evaluation chain")
            expression = data["A"]["model"]["expr"]
            if not isinstance(expression, str) or not expression.strip():
                raise ValueError(f"{uid}: missing PromQL")
            result[uid] = dict(alert=uid, expr=expression,
                               **{"for": rule["for"], "labels": rule["labels"]})
    if set(result) != UIDS:
        raise ValueError(f"missing rules: {sorted(UIDS - result.keys())}")
    return result


def build(output):
    rules = load_rules(ROOT / "grafana/provisioning/alerting/rules.yml")
    fixtures = yaml.safe_load((ROOT / "ci/render-alert-cases.yml").read_text(encoding="utf-8"))
    used_expressions = set()
    for case in fixtures["tests"]:
        for test in case.get("promql_expr_test", []):
            uid = test.pop("rule_uid")
            if uid not in rules:
                raise ValueError(f"unknown rule: {uid}")
            test["expr"] = rules[uid]["expr"]
            used_expressions.add(uid)
        for test in case.get("alert_rule_test", []):
            if test["alertname"] not in rules:
                raise ValueError(f"unknown alert: {test['alertname']}")
    if used_expressions != UIDS:
        raise ValueError("every selected rule needs a PromQL behavior test")
    fixtures["rule_files"] = ["render-alert-rules.yml"]
    output.mkdir(parents=True, exist_ok=True)
    files = {"render-alert-rules.yml": {"groups": [{"name": "cs2-render", "rules": list(rules.values())}]},
             "render-alert-tests.yml": fixtures}
    for filename, content in files.items():
        (output / filename).write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
    print(f"Built {len(rules)} actual rules and {len(fixtures['tests'])} fixture scenarios")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    build(parser.parse_args().output)
