"""Bounded descriptive catalog statistics and captured-recipe cost comparisons."""

import json
import time
from collections import Counter
from fractions import Fraction
from math import gcd, lcm
from statistics import quantiles

from .balance import quantity
from .network import nominal_energy


COMPARISON_SCOPE = "identical_captured_predicates_and_conditions_normalized_batch"


def _number(value):
    return value.numerator if value.denominator == 1 else {"numerator": value.numerator, "denominator": value.denominator}


def _summary(values):
    if not values:
        return {"count": 0, "min": None, "q1": None, "median": None, "q3": None, "max": None, "iqr": None}
    exact = [Fraction(value) for value in values]
    q1, middle, q3 = quantiles(exact, n=4, method="inclusive") if len(exact) > 1 else [exact[0]] * 3
    return {"count": len(exact), "min": min(exact), "q1": q1, "median": middle,
            "q3": q3, "max": max(exact), "iqr": q3 - q1}


def _gates(record):
    conditions = record.get("conditions", {})
    return {"disabled": record.get("executable") is False or conditions.get("enabled") is False,
            "fake": conditions.get("fake") is True,
            "unknown_executability": record.get("executable") is not True and record.get("executable") is not False,
            "dynamic_inputs": conditions.get("dynamic_inputs") == "unresolved",
            "dynamic_output": conditions.get("dynamic_output") == "unresolved"}


def _probability(value):
    chance = quantity(value)
    if not 0 <= chance <= 1:
        raise ValueError("unknown_probability")


def _signature(record, tier):
    """Normalize explicit batch quantities while retaining captured predicates."""
    amounts = []
    for slot in record["inputs"]:
        if slot.get("role") not in ("consume", "presence", "tool") or not slot.get("choices"):
            raise ValueError("unsupported_input_slot")
        for choice in slot["choices"]:
            match = choice.get("match", {})
            if (match.get("mode") not in ("exact", "unified", "ore_dict", "wildcard")
                    or match.get("mode") in ("unified", "ore_dict") and not match.get("group_id")):
                raise ValueError("unsupported_input_predicate")
            if not choice.get("resource_id") and not match.get("group_id"):
                raise ValueError("unknown_resource_identity")
            try:
                amount = quantity(choice.get("amount"))
                _probability(choice.get("consumption_chance", slot.get("consumption_chance", 1)))
            except ValueError as error:
                raise ValueError("unknown_quantity_or_probability") from error
            if amount < 0:
                raise ValueError("unknown_quantity_or_probability")
            if slot["role"] == "consume" and amount > 0:
                amounts.append(amount)
    for output in record["outputs"]:
        if not output.get("resource_id"):
            raise ValueError("unknown_resource_identity")
        try:
            amount = quantity(output.get("amount"))
            _probability(output.get("chance"))
        except ValueError as error:
            raise ValueError("unknown_quantity_or_probability") from error
        if amount < 0:
            raise ValueError("unknown_quantity_or_probability")
        if amount > 0:
            amounts.append(amount)
    if not amounts:
        raise ValueError("no_positive_batch_quantity")
    denominator = lcm(*(amount.denominator for amount in amounts))
    factor = Fraction(gcd(*(amount.numerator * (denominator // amount.denominator) for amount in amounts)), denominator)

    def normalize(value):
        result = dict(value, amount=_number(quantity(value["amount"]) / factor))
        if value.get("native_amount") is not None:
            native = quantity(value["native_amount"])
            result["native_amount"] = _number(native / factor) if native > 0 else value["native_amount"]
        return result

    signature = {key: value for key, value in record.items()
                 if key not in ("id", "display_name", "duration_ticks", "eu_per_tick", "inputs", "outputs", "provenance")}
    signature["inputs"] = [dict(slot, choices=[normalize(choice) if slot["role"] == "consume" else dict(choice)
                                              for choice in slot["choices"]]) for slot in record["inputs"]]
    signature["outputs"] = [normalize(output) for output in record["outputs"]]
    signature["provenance"] = {key: value for key, value in record.get("provenance", {}).items() if key != "index"}
    signature["recipe_tier"] = {key: value for key, value in tier.items() if key != "process_id"}
    return json.dumps(signature, sort_keys=True, separators=(",", ":"), ensure_ascii=False), factor


def _bounded(value, name, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")


def analyze_statistics(resources_iter, groups_iter, processes_iter, *, max_records=600000,
                       max_findings=50, max_signature_buckets=50000, timeout_seconds=15):
    """Analyze pre-scoped streams without matching or changing resource identity.

    Process rows contain ``process`` and Dataset-owned ``recipe_tier``. Findings
    compare declarations, not concrete achievability or confirmed balance bugs.
    Family/tier distributions describe captured execution costs across products.
    They are not an economic ranking of different transformations.
    """
    for value, name, maximum in ((max_records, "max_records", 2000000), (max_findings, "max_findings", 500),
                                 (max_signature_buckets, "max_signature_buckets", 200000)):
        _bounded(value, name, maximum)
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 60):
        raise ValueError("timeout_seconds must be positive and at most 60")
    started = time.monotonic()
    counters = {name: Counter() for name in ("resource_kind", "namespace", "group_kind", "family", "tier",
        "executability", "gates", "energy", "energy_reasons", "exclusions", "counts")}
    counters["counts"].update(resources=0, groups=0, processes=0)
    counters["executability"].update({"true": 0, "false": 0, "unknown": 0})
    counters["gates"].update({name: 0 for name in _gates({})})
    counters["energy"].update(known_positive=0, unsupported=0)
    member_counts, distributions, buckets, limits = [], {}, {}, set()
    scanned = 0
    for collection, records in (("resources", resources_iter), ("groups", groups_iter), ("processes", processes_iter)):
        for row in records:
            if scanned >= max_records:
                limits.add("record_limit")
                break
            if time.monotonic() - started >= timeout_seconds:
                limits.add("analysis_timeout")
                break
            scanned += 1
            counters["counts"][collection] += 1
            if collection == "resources":
                counters["resource_kind"][row["kind"]] += 1
                registry = row.get("registry_name")
                namespace = registry.split(":", 1)[0] if isinstance(registry, str) and ":" in registry else "unqualified"
                counters["namespace"][namespace] += 1
                continue
            if collection == "groups":
                counters["group_kind"][row["kind"]] += 1
                member_counts.append(len(row["members"]))
                continue
            record, tier = row["process"], row["recipe_tier"]
            counters["family"][record["family"]] += 1
            tier_key = json.dumps({key: value for key, value in tier.items() if key != "process_id"}, sort_keys=True)
            counters["tier"][tier_key] += 1
            status = "true" if record.get("executable") is True else "false" if record.get("executable") is False else "unknown"
            counters["executability"][status] += 1
            gates = _gates(record)
            counters["gates"].update(name for name, present in gates.items() if present)
            cost, energy_reason = nominal_energy(record)
            counters["energy"]["known_positive" if cost is not None else "unsupported"] += 1
            if energy_reason:
                counters["energy_reasons"][energy_reason] += 1
            if any(gates.values()):
                counters["exclusions"]["inactive_fake_dynamic_or_unknown"] += 1
                continue
            if cost is None:
                counters["exclusions"]["unknown_or_nonpositive_nominal_energy"] += 1
                continue
            distribution_key = record["family"], tier_key
            distributions.setdefault(distribution_key, []).append(cost.numerator if cost.denominator == 1 else cost)
            try:
                signature, factor = _signature(record, tier)
            except (ValueError, KeyError, TypeError) as error:
                counters["exclusions"][str(error)] += 1
                continue
            normalized = cost / factor
            if signature not in buckets:
                if len(buckets) >= max_signature_buckets:
                    limits.add("signature_bucket_limit")
                    counters["exclusions"]["signature_bucket_limit"] += 1
                    continue
                buckets[signature] = {"count": 0, "minimum": normalized, "maximum": normalized,
                                      "min_id": record["id"], "max_id": record["id"],
                                      "min_factor": factor, "max_factor": factor}
            bucket = buckets[signature]
            bucket["count"] += 1
            if normalized < bucket["minimum"]:
                bucket.update(minimum=normalized, min_id=record["id"], min_factor=factor)
            if normalized > bucket["maximum"]:
                bucket.update(maximum=normalized, max_id=record["id"], max_factor=factor)
        if limits & {"record_limit", "analysis_timeout"}:
            break
    findings = []
    for signature, bucket in buckets.items():
        if bucket["minimum"] == bucket["maximum"]:
            continue
        findings.append({"kind": "normalized_capture_cost_spread", "comparison_scope": COMPARISON_SCOPE,
            "confirmed_bug": False, "process_ids": [bucket["min_id"], bucket["max_id"]],
            "normalized_signature": signature, "count": bucket["count"],
            "normalized_costs": {"minimum": bucket["minimum"], "maximum": bucket["maximum"]},
            "cost_ratio": bucket["maximum"] / bucket["minimum"],
            "batch_scales": {bucket["min_id"]: bucket["min_factor"], bucket["max_id"]: bucket["max_factor"]}})
    findings.sort(key=lambda value: (-value["cost_ratio"], value["process_ids"]))
    findings_total = len(findings)
    if findings_total > max_findings:
        limits.add("finding_limit")
    findings = findings[:max_findings]
    for finding in findings:
        finding["normalized_signature"] = json.loads(finding["normalized_signature"])
    overview = {"resources": {"count": counters["counts"]["resources"], "by_kind": dict(counters["resource_kind"]),
                    "by_namespace": dict(counters["namespace"]), "namespace_semantics": "literal_registry_prefix_unqualified_not_inferred"},
                "groups": {"count": counters["counts"]["groups"], "by_kind": dict(counters["group_kind"]),
                    "members_total": sum(member_counts), "member_counts": _summary(member_counts)},
                "processes": {"count": counters["counts"]["processes"], "by_family": dict(counters["family"]),
                    "by_tier": [{"recipe_tier": json.loads(key), "count": count} for key, count in sorted(counters["tier"].items())],
                    "by_executability": dict(counters["executability"]), "gates": dict(counters["gates"]),
                    "energy_status": dict(counters["energy"]), "energy_unknown_reasons": dict(counters["energy_reasons"])}}
    return {"overview": overview, "distributions": [{"family": family, "recipe_tier": json.loads(tier),
                "metric": "nominal_eu_per_captured_execution", "comparison": "exploratory_across_products", **_summary(values)}
                for (family, tier), values in sorted(distributions.items())],
            "findings": findings, "exclusions": dict(counters["exclusions"]),
            "search": {"records": scanned, "counts": dict(counters["counts"]), "max_records": max_records,
                "max_findings": max_findings, "max_signature_buckets": max_signature_buckets,
                "signature_buckets": len(buckets), "findings_total": findings_total,
                "timeout_seconds": timeout_seconds, "complete": not limits, "truncated": bool(limits),
                "overview_complete": not limits & {"record_limit", "analysis_timeout"},
                "limit_reasons": sorted(limits), "elapsed_seconds": time.monotonic() - started},
            "limitations": ["Findings are anomaly candidates, not confirmed bugs",
                "Identical captured predicates don't prove concrete matching, availability or achievability",
                "Presence and tool quantities aren't scaled as consumed batch material",
                "Family/tier execution-cost distributions compare different products descriptively",
                "Finding order prioritizes within-cohort cost spread, not economic value across products",
                "Missing, disabled, fake, dynamic and unresolved records remain explicit in exclusions",
                "Resource namespaces are literal registry prefixes and don't infer the owning mod"]}
