"""Bounded stoichiometric networks verified with the shared exact ledgers.

Dataset supplies concrete accounting views. This module doesn't resolve ingredient
predicates or discover catalog records. Solver optima apply to bounded candidate
variants, not the complete snapshot or every possible network.
"""

import json
import os
import subprocess
import sys
import time
from collections import deque
from fractions import Fraction
from math import lcm

from .balance import net_ledger, quantity, witness_ledger


def nominal_energy(process):
    """Return captured EU/t times duration, or an explicit unknown reason."""
    unit = process.get("conditions", {}).get("energy_unit", "eu")
    if not isinstance(unit, str) or unit.lower() != "eu":
        return None, "Native energy isn't declared in EU"
    try:
        duration = quantity(process.get("duration_ticks"))
        eut = quantity(process.get("eu_per_tick"))
    except ValueError:
        return None, "Native duration or EU/t is unknown"
    if duration <= 0 or eut <= 0:
        return None, "Zero or negative native energy isn't a free production operation"
    # Captured GT EU/t already includes recipe-map amperage.
    return duration * eut, None


def _count(value, name, upper):
    if type(value) is not int or not 1 <= value <= upper:
        raise ValueError(f"{name} must be between 1 and {upper}")
    return value


def _ids(values, name):
    if not isinstance(values, (list, set, tuple)) or any(not isinstance(v, str) or not v for v in values):
        raise ValueError(f"{name} must contain concrete resource IDs")
    return set(values)


def _ordered_steps(records, steps, ledger, feeds, scale, start_stock, yield_mode):
    """Schedule funded whole batches first, with explicit seeds on deadlock."""
    stock = {resource: -amount * scale for resource, amount in ledger["net"].items()
             if resource in feeds and amount < 0}
    for resource, amount in ledger["presence"].items():
        stock[resource] = stock.get(resource, Fraction()) + amount
    for resource, amount in (start_stock or {}).items():
        stock[resource] = max(stock.get(resource, Fraction()), quantity(amount))
    pending = [(step, net_ledger(records, {step["process_id"]: step["runs"]},
                selections={step["process_id"]: step["selections"]}, yield_mode=yield_mode)) for step in steps]
    ordered = []
    while pending:
        funded = [index for index, (_, accounting) in enumerate(pending)
                  if all(stock.get(resource, Fraction()) >= amount for resource, amount in accounting["requirements"].items())]
        # A deadlock can require cycle stock. The ledger reports these additions.
        step, accounting = pending.pop(funded[0] if funded else 0)
        for resource, amount in accounting["requirements"].items():
            stock[resource] = max(stock.get(resource, Fraction()), amount)
        for resource, amount in accounting["consumed"].items():
            stock[resource] -= amount
        for resource, amount in accounting["produced"].items():
            stock[resource] = stock.get(resource, Fraction()) + amount
        ordered.append(step)
    return ordered


def _canonical_ids(value, ids):
    if isinstance(value, dict):
        if value.get("process_id") in ids:
            value["variant_id"] = value["process_id"]
            value["process_id"] = ids[value["process_id"]]
        for child in value.values():
            _canonical_ids(child, ids)
    elif isinstance(value, list):
        for child in value:
            _canonical_ids(child, ids)


def solve_network(variants, *, target_id, target_amount=1, allowed_feed_ids,
                  primary_feed_id=None, objective="nominal_eu", yield_mode="guaranteed",
                  max_solutions=8, max_solves=24, max_columns=128, max_rows=512,
                  timeout_seconds=10, start_stock=None):
    """Optimize complete AND recipes and verify each exact steady-state witness.

    ``process`` is a detached accounting view with selected predicates resolved
    by Dataset. Original slot/choice indexes remain intact in ``selections``.
    Unknown nominal energy excludes a variant from EU optimization, but remains
    explicitly unknown when minimizing recipe runs. Startup is an ordered,
    conservative integer-batch stock witness, not a minimum-stock schedule.
    """
    started = time.monotonic()
    if not isinstance(variants, list):
        raise ValueError("variants must be an array")
    if not isinstance(target_id, str) or not target_id:
        raise ValueError("target_id must be a concrete resource ID")
    target_amount = quantity(target_amount)
    if target_amount <= 0:
        raise ValueError("target_amount must be positive")
    feeds = _ids(allowed_feed_ids, "allowed_feed_ids")
    if target_id in feeds:
        raise ValueError("The target cannot also be an allowed feed")
    if primary_feed_id is not None and primary_feed_id not in feeds:
        raise ValueError("primary_feed_id must be an allowed feed")
    if objective not in ("nominal_eu", "recipe_runs"):
        raise ValueError("objective must be nominal_eu or recipe_runs")
    if yield_mode not in ("guaranteed", "expected"):
        raise ValueError("yield_mode must be guaranteed or expected")
    for value, name, upper in ((max_solutions, "max_solutions", 100), (max_solves, "max_solves", 100),
                              (max_columns, "max_columns", 512), (max_rows, "max_rows", 4096)):
        _count(value, name, upper)
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 30):
        raise ValueError("timeout_seconds must be positive and at most 30")
    if start_stock is not None:
        if not isinstance(start_stock, dict):
            raise ValueError("start_stock must map resource IDs to quantities")
        for resource, amount in start_stock.items():
            if not isinstance(resource, str) or not resource or quantity(amount) < 0:
                raise ValueError("start_stock must contain nonnegative concrete resource quantities")
    result = {"status": "unsupported", "solutions": [], "exclusions": [], "rejected_witnesses": [],
              "yield_mode": yield_mode, "target_id": target_id, "target_amount": target_amount,
              "allowed_feed_ids": sorted(feeds), "primary_feed_id": primary_feed_id,
              "optimization": {"objective": objective, "scope": "bounded_candidate_variants",
                               "global_optimum_proven": False,
                               "primary_feed_policy": "exact_negative_net_required" if primary_feed_id else None,
                               "alternative_policy": "bounded_support_exclusions"},
              "search": {"solves": 0, "max_solves": max_solves, "max_solutions": max_solutions,
                         "max_columns": max_columns, "max_rows": max_rows, "timeout_seconds": timeout_seconds,
                         "columns": 0, "rows": 0, "complete": False, "truncated": False, "limit_reasons": []},
              "limitations": ["All AND inputs, presence requirements and native machine conditions still apply",
                              "Steady-state regeneration doesn't provide initial inventory",
                              "Startup is a conservative ordered batch witness, not minimum seed stock",
                              "Expected yields cannot establish available stock",
                              "Nominal EU excludes overclocking, machine efficiency and infrastructure",
                              "Support exclusions don't enumerate every network or prove globally best feed-constrained yield"]}
    if len(variants) > max_columns:
        result["status"] = "incomplete"
        result["search"].update(truncated=True, limit_reasons=["candidate_column_limit"])
        return result
    columns, used_ids, resources = [], set(), {target_id}
    for variant in variants:
        vid, pid = variant.get("variant_id"), variant.get("process_id")
        if not isinstance(vid, str) or not vid or vid in used_ids or not isinstance(pid, str) or not pid:
            raise ValueError("Variants need distinct variant IDs and concrete process IDs")
        used_ids.add(vid)
        process = variant.get("process")
        if not isinstance(process, dict) or not isinstance(variant.get("selections"), dict):
            raise ValueError("Variants need a process accounting view and selections")
        record = dict(process, id=vid)
        selections = {vid: variant["selections"]}
        ledger = net_ledger({vid: record}, {vid: 1}, selections=selections, yield_mode=yield_mode)
        if ledger["status"] != "complete":
            result["exclusions"].append({"variant_id": vid, "process_id": pid, "kind": "unsupported_accounting",
                                         "reasons": ledger["unsupported"]})
            continue
        energy, reason = nominal_energy(record)
        if objective == "nominal_eu" and energy is None:
            result["exclusions"].append({"variant_id": vid, "process_id": pid,
                                         "kind": "unsupported_energy", "reason": reason})
            continue
        resources.update(ledger["consumed"])
        resources.update(ledger["produced"])
        resources.update(ledger["presence"])
        columns.append({**variant, "process": record, "ledger": ledger, "energy": energy, "energy_reason": reason})
    result["search"].update(columns=len(columns), rows=len(resources))
    if len(resources) > max_rows:
        result["status"] = "incomplete"
        result["search"].update(truncated=True, limit_reasons=["candidate_row_limit"])
        return result
    if not columns:
        return result
    row_ids = sorted(resources - feeds - {target_id})
    matrix = [[-column["ledger"]["net"].get(resource, Fraction()) for column in columns] for resource in row_ids]
    if not matrix:
        # SymPy's public LP entry point requires a shaped inequality matrix.
        matrix = [[Fraction()] * len(columns)]
    target_row = [column["ledger"]["net"].get(target_id, Fraction()) for column in columns]
    costs = [column["energy"] if objective == "nominal_eu" else Fraction(1) for column in columns]
    payload = {"A": [[str(v) for v in row] for row in matrix], "b": ["0"] * len(matrix),
               "target": [str(v) for v in target_row], "amount": str(target_amount),
               "costs": [str(v) for v in costs], "max_solutions": max_solutions, "max_solves": max_solves,
               "primary": [str(column["ledger"]["net"].get(primary_feed_id, Fraction())) for column in columns]
                          if primary_feed_id else None}
    remaining = timeout_seconds - (time.monotonic() - started)
    if remaining <= 0:
        result["status"] = "incomplete"
        result["search"].update(truncated=True, limit_reasons=["solver_timeout"])
        return result
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    worker = subprocess.Popen([sys.executable, "-m", "gtnh_data.network", "--solve"], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags)
    timed_out = False
    try:
        stdout, stderr = worker.communicate(json.dumps(payload), timeout=remaining)
    except subprocess.TimeoutExpired:
        timed_out = True
        worker.kill()
        stdout, stderr = worker.communicate()
    summary = None
    observed_solves = 0
    for line in stdout.splitlines():
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            result["rejected_witnesses"].append({"reason": "Malformed solver response"})
            continue
        observed_solves = max(observed_solves, message.get("solve", 0))
        if message["type"] == "summary":
            summary = message
        elif message["type"] == "primary_rejected":
            result["rejected_witnesses"].append({"reason": "primary_feed_not_net_consumed", "solve": message["solve"]})
        elif message["type"] == "solution":
            runs = [Fraction(v) for v in message["runs"]]
            active = [(column, count) for column, count in zip(columns, runs) if count > 0]
            records = {column["variant_id"]: column["process"] for column, _ in active}
            selections = {column["variant_id"]: column["selections"] for column, _ in active}
            ledger = net_ledger(records, {column["variant_id"]: count for column, count in active},
                                selections=selections, yield_mode=yield_mode)
            valid = (len(runs) == len(columns) and all(v >= 0 for v in runs) and ledger["status"] == "complete"
                     and ledger["net"].get(target_id, Fraction()) == target_amount
                     and all(amount >= 0 for resource, amount in ledger["net"].items() if resource not in feeds)
                     and (primary_feed_id is None or ledger["net"].get(primary_feed_id, Fraction()) < 0))
            total_objective = sum((cost * count for cost, count in zip(costs, runs)), Fraction())
            if not valid or total_objective != Fraction(message["objective"]):
                result["rejected_witnesses"].append({"reason": "Exact independent witness verification failed"})
                continue
            scale = lcm(*(count.denominator for _, count in active))
            normalized = witness_ledger(records, [{"process_id": column["variant_id"], "runs": count,
                                                   "selections": column["selections"]} for column, count in active],
                                        yield_mode=yield_mode)
            steps = [{"process_id": column["variant_id"], "runs": count * scale,
                      "selections": column["selections"]} for column, count in active]
            steps = _ordered_steps(records, steps, ledger, feeds, scale, start_stock, yield_mode)
            startup = witness_ledger(records, steps, start_stock=start_stock, yield_mode=yield_mode)
            startup.update(batch_scale=scale, target_amount=target_amount * scale,
                           ordering="funded_batches_first_conservative_deadlock_seeds")
            executions = [{"variant_id": column["variant_id"], "process_id": column["process_id"],
                           "runs": count, "selections": column["selections"],
                           "ledger": step["ledger"]} for (column, count), step in zip(active, normalized["steps"])]
            unknown = [{"process_id": column["process_id"], "variant_id": column["variant_id"],
                        "reason": column["energy_reason"]} for column, _ in active if column["energy"] is None]
            total_eu = None if unknown else sum((column["energy"] * count for column, count in active), Fraction())
            ids = {column["variant_id"]: column["process_id"] for column, _ in active}
            _canonical_ids(startup, ids)
            _canonical_ids(ledger, ids)
            for execution in executions:
                _canonical_ids(execution["ledger"], ids)
            result["solutions"].append({"executions": executions, "ledger": ledger,
                "net_imports": {resource: -amount for resource, amount in ledger["net"].items() if amount < 0},
                "net_coproducts": {resource: amount for resource, amount in ledger["net"].items()
                                   if amount > 0 and resource != target_id},
                "nominal_energy": {"status": "unknown" if unknown else "known", "total_eu": total_eu,
                                   "eu_per_target": total_eu / target_amount if total_eu is not None else None,
                                   "unknown_processes": unknown},
                "objective_value": total_objective, "integer_batch_scale": scale,
                "startup": startup, "witness_verified": True})
    limits = [] if summary is None else summary["limit_reasons"]
    if timed_out:
        limits.append("solver_timeout")
    if summary is None and not timed_out:
        result["rejected_witnesses"].append({"reason": "Solver failed before reporting completion",
                                             "detail": stderr[-1000:]})
    result["search"].update(solves=summary["solves"] if summary else observed_solves,
        complete=bool(summary and summary["complete"] and not timed_out), truncated=bool(limits),
        limit_reasons=sorted(set(limits)), elapsed_seconds=time.monotonic() - started)
    result["solutions"].sort(key=lambda solution: solution["objective_value"])
    result["status"] = ("complete" if result["solutions"] else "incomplete" if limits
                        else "infeasible" if summary else "unsupported")
    return result


def _solver_main(payload):
    """Run bounded exact LP subproblems in a disposable worker process."""
    from sympy import Matrix, Rational
    from sympy.solvers.simplex import InfeasibleLPError, UnboundedLPError, linprog

    def emit(message):
        print(json.dumps(message), flush=True)

    costs = [Rational(v) for v in payload["costs"]]
    matrix = [[Rational(v) for v in row] for row in payload["A"]]
    bounds_rhs = [Rational(v) for v in payload["b"]]
    target = [[Rational(v) for v in payload["target"]]]
    amount = [Rational(payload["amount"])]
    primary = [Rational(v) for v in payload["primary"]] if payload["primary"] is not None else None
    queue, queued, solutions = deque([frozenset()]), {frozenset()}, set()
    solves, limits = 0, set()
    while queue and solves < payload["max_solves"] and len(solutions) < payload["max_solutions"]:
        excluded = queue.popleft()
        solves += 1
        emit({"type": "progress", "solve": solves})
        try:
            optimum, runs = linprog(costs, Matrix(matrix) if matrix else None,
                Matrix(bounds_rhs) if matrix else None, target, amount,
                bounds={i: (0, 0) for i in excluded} or None)
        except InfeasibleLPError:
            continue
        except UnboundedLPError:
            limits.add("solver_unbounded")
            continue
        active = [i for i, count in enumerate(runs) if count > 0]
        for index in active:
            next_exclusion = excluded | {index}
            if next_exclusion not in queued:
                if len(queued) >= payload["max_solves"]:
                    limits.add("alternative_support_limit")
                    break
                queued.add(next_exclusion)
                queue.append(next_exclusion)
        if primary is not None and sum(v * n for v, n in zip(primary, runs)) >= 0:
            emit({"type": "primary_rejected", "solve": solves})
            continue
        signature = tuple(runs)
        if signature not in solutions:
            solutions.add(signature)
            emit({"type": "solution", "runs": [str(v) for v in runs], "objective": str(optimum), "solve": solves})
    if queue:
        limits.add("solution_limit" if len(solutions) >= payload["max_solutions"] else "solve_limit")
    emit({"type": "summary", "solves": solves, "limit_reasons": sorted(limits), "complete": not limits})


if __name__ == "__main__":
    _solver_main(json.load(sys.stdin))
