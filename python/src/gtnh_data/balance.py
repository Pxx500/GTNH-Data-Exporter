"""Exact recipe accounting shared by loop audits and recycling plans."""

from fractions import Fraction
from collections import defaultdict
from collections import deque
from math import lcm

_NATIVE_ACCOUNTING_VERSIONS = ("5.09.54.221", "5.09.54.223", "5.09.54.225")


def _native_integer(value):
    if type(value) is int:
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    raise ValueError("Native accounting value isn't a decimal integer")


def quantity(value):
    """Read an exact quantity. Binary floats and booleans aren't quantity facts."""
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if isinstance(value, dict) and type(value.get("numerator")) is int and type(value.get("denominator")) is int:
        if value["denominator"] <= 0:
            raise ValueError("Quantity denominator must be positive")
        return Fraction(value["numerator"], value["denominator"])
    raise ValueError("Quantity is missing or not an exact integer/rational")


def ledger_json(value):
    """Serialize exact results at the Dataset transport seam."""
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, dict):
        return {key: ledger_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [ledger_json(item) for item in value]
    return value


def _positive(value, *, zero=False):
    result = quantity(value)
    if result < 0 or (not zero and result == 0):
        raise ValueError("Quantity must be nonnegative" if zero else "Quantity must be positive")
    return result


def _chance(value):
    result = quantity(value)
    if not 0 <= result <= 1:
        raise ValueError("Chance must be an exact rational between zero and one")
    return result


def _chosen(slot, index, selections, groups):
    choices = slot.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Input slot has no declared choices")
    selected = selections.get(str(index), selections.get(index))
    if selected is None:
        if len(choices) != 1:
            raise ValueError("OR input requires an explicit choice")
        choice = choices[0]
        if choice.get("match", {}).get("mode") != "exact":
            raise ValueError("Grouped input requires a concrete resolved selection")
        resource = choice.get("resource_id")
    else:
        ci = selected.get("choice_index")
        if type(ci) is not int or not 0 <= ci < len(choices):
            raise ValueError("Selected input choice index is invalid")
        choice, resource = choices[ci], selected.get("resource_id")
        match = choice.get("match", {})
        if match.get("mode") not in ("exact", "unified", "wildcard", "ore_dict"):
            raise ValueError("Input matching predicate isn't supported")
        if resource != choice.get("resource_id"):
            members = groups.get(match.get("group_id"), {}).get("members", [])
            if match.get("mode") == "exact" or resource not in members:
                raise ValueError("Selected resource isn't a declared input/group member")
    if not isinstance(resource, str) or not resource:
        raise ValueError("Input has no concrete resource identity")
    return resource, choice


def _empty(yield_mode):
    return {"status": "complete", "yield_mode": yield_mode, "consumed": {}, "produced": {},
            "net": {}, "presence": {}, "requirements": {}, "unsupported": [], "uncertainty": [],
            "assumptions": ["Captured machine conditions are retained, not evaluated", "Energy and fuel supply aren't verified",
                            "Expected quantities are accounting scenarios, not guaranteed stock"] if yield_mode == "expected"
                           else ["Captured machine conditions are retained, not evaluated", "Energy and fuel supply aren't verified",
                                 "Certain outputs and maximum possible input consumption"]}


def native_projection_issue(process):
    """Describe recognized native models without a supported operation ledger."""
    conditions = process.get("conditions", {})
    provenance = process.get("provenance", {})
    special = conditions.get("special_items")
    if (provenance.get("owner") == "GTRecipe"
            and process.get("family") == "gregtech:gt.recipe.eyeofharmony"
            and isinstance(special, dict) and special.get("type") == "tectech.recipe.EyeOfHarmonyRecipe"):
        return {"status": "unsupported_accounting", "native_model": "tectech.recipe.EyeOfHarmonyRecipe",
                "reason": "Eye of Harmony custom-machine projection has unresolved execution quantities, yield and voltage",
                "voltage_unresolved": True}
    metadata = conditions.get("native_metadata")
    if (provenance.get("owner") == "GTRecipe" and provenance.get("map") == "gt.recipe.spaceMining"
            and isinstance(metadata, dict) and any(isinstance(value, dict)
                and value.get("type") == "gtnhintergalactic.recipe.SpaceMiningData" for value in metadata.values())):
        return {"status": "unsupported_accounting", "native_model": "gtnhintergalactic.recipe.SpaceMiningData",
                "reason": "Space Mining operation quantities are unmodeled. Captured output amounts and weights "
                          "are not a supported per-operation yield model.",
                "voltage_unresolved": False}
    return None


def net_ledger(processes, executions, *, selections=None, groups=None, yield_mode="guaranteed"):
    """Account selected AND inputs, OR choices, cooutputs and presence exactly."""
    if yield_mode not in ("guaranteed", "expected"):
        raise ValueError("yield_mode must be guaranteed or expected")
    selections, groups = selections or {}, groups or {}
    result = _empty(yield_mode)
    consumed, produced, presence, requirements = (defaultdict(Fraction) for _ in range(4))
    for pid, count in executions.items():
        try:
            runs = _positive(count)
            process = processes[pid]
            issue = native_projection_issue(process)
            if issue:
                raise ValueError(issue["reason"])
            if process.get("executable") is not True:
                raise ValueError("Native recipe executability is false or unresolved")
            conditions = process.get("conditions", {})
            if any(conditions.get(key) == "unresolved" for key in ("dynamic_inputs", "dynamic_output")):
                raise ValueError("Native dynamic recipe declarations are unresolved")
            if conditions.get("enabled") is False or conditions.get("fake") is True:
                raise ValueError("Native recipe is disabled or display-only")
            for index, slot in enumerate(process["inputs"]):
                resource, choice = _chosen(slot, index, selections.get(pid, {}), groups)
                amount = _positive(choice.get("amount"), zero=True)
                role = slot.get("role")
                if role == "presence":
                    presence[resource] = max(presence[resource], amount)
                elif role == "consume":
                    probability = _chance(choice.get("consumption_chance", slot.get("consumption_chance", Fraction(1))))
                    consumed[resource] += amount * runs * (probability if yield_mode == "expected" else int(probability > 0))
                    if probability == 0:
                        presence[resource] = max(presence[resource], amount)
                    else:
                        requirements[resource] += amount * runs
                    if probability < 1:
                        result["uncertainty"].append({"process_id": pid, "slot_index": index,
                                                     "kind": "input_consumption", "chance": probability})
                else:
                    raise ValueError("Input role isn't consume or presence")
            for index, output in enumerate(process["outputs"]):
                resource = output.get("resource_id")
                if not isinstance(resource, str) or not resource:
                    raise ValueError("Output has no concrete resource identity")
                amount, probability = _positive(output.get("amount"), zero=True), _chance(output.get("chance"))
                produced[resource] += amount * runs * (probability if yield_mode == "expected" else int(probability == 1))
                if probability < 1:
                    result["uncertainty"].append({"process_id": pid, "output_index": index,
                                                 "kind": "output_production", "chance": probability})
        except (KeyError, ValueError, TypeError) as error:
            result["unsupported"].append({"process_id": pid, "reason": str(error)})
    if result["unsupported"]:
        result["status"] = "unsupported"
        return result
    result.update(consumed={k: v for k, v in consumed.items() if v},
                  produced={k: v for k, v in produced.items() if v},
                  presence={k: v for k, v in presence.items() if v},
                  requirements={k: requirements[k] + presence[k] for k in requirements.keys() | presence.keys()
                                if requirements[k] + presence[k]},
                  net={k: produced[k] - consumed[k] for k in produced.keys() | consumed.keys()
                       if produced[k] != consumed[k]})
    return result


def find_loops(processes, start_id, *, chemical_facts=None, groups=None, selections=None,
               kind="any", chemical_kind="any", yield_mode="guaranteed", max_depth=6, max_processes=200, max_paths=20, max_states=5000):
    """Enumerate bounded simple material-return paths and verify their ledgers.

    Dataset supplies a start-local candidate set and resolves native predicates.
    This isn't an exhaustive reaction-network or inventory optimizer.
    """
    if kind not in ("any", "gaining", "lossy", "conserving"):
        raise ValueError("Unknown loop classification")
    if chemical_kind not in ("any", "balanced", "gaining", "lossy", "mixed", "unsupported"):
        raise ValueError("Unknown chemical balance classification")
    for value, maximum in ((max_depth, 20), (max_processes, 1000), (max_paths, 100), (max_states, 100000)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError("Loop search bounds must be positive and within supported limits")
    if yield_mode not in ("guaranteed", "expected"):
        raise ValueError("yield_mode must be guaranteed or expected")
    selections, groups = selections or {}, groups or {}
    result = {"status": "complete", "yield_mode": yield_mode, "witnesses": [], "unsupported": [],
              "chemical_unsupported_count": 0,
              "limit_reasons": [], "scope": "bounded_simple_material_return_paths",
              "search": {"examined_processes": 0, "examined_states": 0, "process_limit": max_processes,
                         "state_limit": max_states, "expansion_work": 0, "work_limit": 100000}}
    limits, using = set(), defaultdict(list)
    for index, (pid, process) in enumerate(processes.items()):
        if index >= max_processes:
            limits.add("process_limit")
            break
        result["search"]["examined_processes"] += 1
        unit = net_ledger(processes, {pid: 1}, selections=selections, groups=groups, yield_mode=yield_mode)
        if unit["status"] != "complete":
            result["unsupported"].extend(unit["unsupported"])
            continue
        for resource, amount in unit["consumed"].items():
            if amount > 0:
                using[resource].append((pid, unit))
    queue = deque([(start_id, Fraction(1), [], [start_id])])
    admitted_states, seen = 1, set()
    while queue:
        resource, available, steps, resource_ids = queue.popleft()
        result["search"]["examined_states"] += 1
        for pid, unit in using[resource]:
            if any(step["process_id"] == pid for step in steps):
                continue
            runs = available / unit["consumed"][resource]
            for output, amount in unit["produced"].items():
                result["search"]["expansion_work"] += 1
                if result["search"]["expansion_work"] > result["search"]["work_limit"]:
                    limits.add("work_limit")
                    queue.clear()
                    break
                if amount <= 0:
                    continue
                next_steps = steps + [{"process_id": pid, "runs": runs,
                                       "selections": selections.get(pid, {})}]
                next_amount = amount * runs
                if output == start_id:
                    signature = tuple((s["process_id"], s["runs"]) for s in next_steps), tuple(resource_ids)
                    if signature in seen:
                        continue
                    seen.add(signature)
                    scale = lcm(*(s["runs"].denominator for s in next_steps))
                    integral_steps = [{**s, "runs": s["runs"] * scale} for s in next_steps]
                    ledger = witness_ledger(processes, integral_steps, groups=groups, yield_mode=yield_mode)
                    if ledger["status"] != "complete":
                        result["unsupported"].extend(ledger["unsupported"])
                        continue
                    ledger = witness_ledger(processes, integral_steps, start_stock=ledger["required_start_stock"],
                                            groups=groups, yield_mode=yield_mode)
                    ratio = ledger["produced"].get(start_id, 0) / ledger["consumed"][start_id]
                    classification = "gaining" if ratio > 1 else "lossy" if ratio < 1 else "conserving"
                    if kind != "any" and classification != kind:
                        continue
                    external = {r: -q for r, q in ledger["net"].items() if r != start_id and q < 0}
                    chemistry = chemical_ledger(ledger, chemical_facts or {})
                    chemical_classification = chemistry["classification"] if chemistry["status"] == "complete" else "unsupported"
                    if chemical_kind != "any" and chemical_classification != chemical_kind:
                        if chemical_classification == "unsupported":
                            result["chemical_unsupported_count"] += 1
                            if sum(item.get("kind") == "chemical_accounting" for item in result["unsupported"]) < 50:
                                result["unsupported"].append({"kind": "chemical_accounting", "process_ids": [s["process_id"] for s in integral_steps],
                                    "reason": "Closed witness can't be classified with the available native chemical accounting facts"})
                        continue
                    result["witnesses"].append({"steps": integral_steps, "process_ids": [s["process_id"] for s in integral_steps],
                        "resource_ids": resource_ids + [start_id], "classification": classification,
                        "return_ratio": ratio, "ledger": ledger,
                        "required_start_stock": ledger["required_start_stock"], "external_consumption": external,
                        "autonomous": yield_mode == "guaranteed" and all(q >= 0 for q in ledger["net"].values()) and ledger["feasible"] is True,
                        "autonomy_scope": "material_net_only_with_declared_start_stock",
                        "chemical_balance": chemistry})
                    if len(result["witnesses"]) >= max_paths:
                        limits.add("path_limit")
                        queue.clear()
                        break
                elif output not in resource_ids:
                    if len(next_steps) >= max_depth:
                        if using[output]:
                            limits.add("depth")
                        continue
                    if admitted_states >= max_states:
                        limits.add("state_limit")
                        continue
                    queue.append((output, next_amount, next_steps, resource_ids + [output]))
                    admitted_states += 1
            if "path_limit" in limits or "work_limit" in limits:
                break
        if "path_limit" in limits or "work_limit" in limits:
            break
    result["limit_reasons"] = sorted(limits)
    if limits:
        result["status"] = "limited"
    elif not result["witnesses"] and result["unsupported"]:
        result["status"] = "unsupported"
    result["coverage_complete"] = not result["unsupported"]
    return result


def _material_vector(material, basis, active):
    if not isinstance(material, dict) or material.get("status") != "complete":
        raise ValueError("Native material tree isn't complete")
    identity = id(material)
    if identity in active:
        raise ValueError("Native material tree contains a cycle")
    active = active | {identity}
    element = material.get("element")
    components = material.get("components")
    if element is not None:
        if not isinstance(element.get("id"), str) or not element["id"] or components:
            raise ValueError("Element leaf identity/components aren't supported")
        return {element["id"]: Fraction(1)}
    if not isinstance(components, list) or not components:
        raise ValueError("Native material has no element or component definition")
    weights = [Fraction(_native_integer(c["coefficient"])) for c in components]
    if any(weight <= 0 for weight in weights):
        raise ValueError("Native component coefficients must be positive")
    if basis == "solid_material_unit":
        density = Fraction(_native_integer(material["density_gt_units"]), 3628800)
        if density <= 0:
            raise ValueError("Native material density must be positive")
        factor = density / sum(weights)
    elif basis == "fluid_formula_unit":
        factor = Fraction(1)
    else:
        raise ValueError("Native component unit basis is unresolved")
    vector = defaultdict(Fraction)
    for component, weight in zip(components, weights):
        child = component["material"]
        child_basis = child.get("component_unit_basis")
        # Element leaves contribute one native accounting element unit.
        if child.get("element") is not None:
            child_basis = "solid_material_unit"
        for element_id, amount in _material_vector(child, child_basis, active).items():
            vector[element_id] += amount * weight * factor
    return dict(vector)


def _accounting_vector(material, accounting):
    if accounting.get("status") != "eligible":
        raise ValueError(accounting.get("reason") or "Native quantity accounting isn't eligible")
    basis = accounting["basis"]
    normalization = {"gt_material_units": "native_top_level_component_parts", "formula_units": "native_formula_unit"}
    if basis not in normalization or accounting.get("normalization") != normalization[basis]:
        raise ValueError("Native quantity basis/normalization isn't supported")
    scale = accounting["quantity"]
    numerator, denominator = _native_integer(scale["numerator"]), _native_integer(scale["denominator"])
    if numerator <= 0 or denominator <= 0:
        raise ValueError("Native resource unit conversion must be positive")
    unit = Fraction(numerator, denominator)
    vector = _material_vector(material, "solid_material_unit" if basis == "gt_material_units" else "fluid_formula_unit", set())
    return basis, unit, normalization[basis], {k: q * unit for k, q in vector.items()}


def inspect_chemistry(material_facts):
    """Inspect source-backed GT accounting. This doesn't certify chemical purity."""
    result = {"status": "unsupported", "basis": None, "vector": {}, "unsupported": [], "association_resolution": None}
    try:
        facts = material_facts
        if (not isinstance(facts, dict) or type(facts.get("schema_version")) is not int or facts["schema_version"] != 1
                or facts.get("status") not in ("associated", "ambiguous")):
            raise ValueError("Native material association is missing or unsupported")
        if facts.get("native_version") not in _NATIVE_ACCOUNTING_VERSIONS or facts.get("gt_material_unit") != "3628800":
            raise ValueError("Native chemical accounting version/unit isn't source-proven")
        if facts["status"] == "ambiguous":
            candidates = facts["association"].get("candidates")
            if not isinstance(candidates, list) or not candidates:
                raise ValueError("Ambiguous native association has no candidate evidence")
            profiles = [_accounting_vector(candidate["material"], candidate["accounting"]) for candidate in candidates]
            if any(profile != profiles[0] for profile in profiles[1:]):
                raise ValueError("Native association candidates disagree on chemical vector or quantity basis")
            basis, _, _, vector = profiles[0]
            resolution = "equivalent_native_candidate_vectors"
            result["candidate_count"] = len(candidates)
        else:
            basis, _, _, vector = _accounting_vector(facts["association"]["primary"]["material"], facts["accounting"])
            resolution = "native_primary"
        result.update(status="complete", basis=basis, vector=vector, association_resolution=resolution)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, AttributeError) as error:
        result["unsupported"].append(str(error))
    return result


def chemical_ledger(ledger, chemical_facts):
    """Explain elemental imbalance separately from material-return loop evidence."""
    result = {"status": "unsupported", "classification": None, "element_inputs": {}, "element_outputs": {},
              "element_delta": {}, "unsupported": [], "scope": "source_backed_gt_chemical_accounting_not_physical_moles"}
    if ledger.get("status") != "complete":
        result["unsupported"] = [{"reason": "Resource ledger is unsupported"}]
        return result
    inputs, outputs = defaultdict(Fraction), defaultdict(Fraction)
    for name, totals in (("consumed", inputs), ("produced", outputs)):
        for resource, quantity in ledger[name].items():
            facts = inspect_chemistry(chemical_facts.get(resource))
            if facts["status"] != "complete":
                result["unsupported"].append({"resource_id": resource, "reason": ", ".join(facts["unsupported"])})
                continue
            for element, amount in facts["vector"].items():
                totals[element] += amount * quantity
    if result["unsupported"]:
        return result
    delta = {e: outputs[e] - inputs[e] for e in inputs.keys() | outputs.keys() if outputs[e] != inputs[e]}
    positive, negative = any(v > 0 for v in delta.values()), any(v < 0 for v in delta.values())
    classification = "mixed" if positive and negative else "gaining" if positive else "lossy" if negative else "balanced"
    result.update(status="complete", classification=classification, element_inputs=dict(inputs), element_outputs=dict(outputs), element_delta=delta,
                  positive_element_delta={e: q for e, q in delta.items() if q > 0}, negative_element_delta={e: q for e, q in delta.items() if q < 0})
    return result


def witness_ledger(processes, steps, *, start_stock=None, groups=None, yield_mode="guaranteed"):
    """Compute an ordered stock witness without treating expected yield as stock."""
    result = _empty(yield_mode)
    consumed, produced, presence, required, balance = (defaultdict(Fraction) for _ in range(5))
    result["steps"] = []
    for step in steps:
        pid = step["process_id"]
        ledger = net_ledger(processes, {pid: step["runs"]},
                            selections={pid: step.get("selections", {})}, groups=groups, yield_mode=yield_mode)
        result["steps"].append({**step, "ledger": ledger})
        result["unsupported"].extend(ledger["unsupported"])
        result["uncertainty"].extend(ledger["uncertainty"])
        if ledger["status"] != "complete":
            continue
        for resource, amount in ledger["requirements"].items():
            required[resource] = max(required[resource], amount - balance[resource])
        for resource, amount in ledger["presence"].items():
            presence[resource] = max(presence[resource], amount)
        for resource, amount in ledger["consumed"].items():
            consumed[resource] += amount
            balance[resource] -= amount
        for resource, amount in ledger["produced"].items():
            produced[resource] += amount
            balance[resource] += amount
    result.update(required_start_stock={}, final_stock={}, feasible=None,
                  start_stock_declared=start_stock is not None,
                  final_stock_semantics="declared_stock_plus_batch_net" if start_stock is not None
                                        else "batch_net_change_without_declared_stock",
                  integer_batch_scale=None, requires_integer_batch_scaling=None,
                  startup_scope="conservative_batch_prefix_not_minimum_scheduling_stock",
                  feasibility_scope="ordered_stoichiometric_stock_only")
    if result["unsupported"]:
        result["status"] = "unsupported"
        return result
    initial = {k: _positive(v, zero=True) for k, v in (start_stock or {}).items()}
    required = {k: v for k, v in required.items() if v > 0}
    result.update(consumed=dict(consumed), produced=dict(produced), presence=dict(presence),
                  net={k: v for k, v in balance.items() if v}, required_start_stock=required,
                  final_stock={k: initial.get(k, 0) + balance.get(k, 0) for k in initial.keys() | balance.keys()})
    integral = all(quantity(step["runs"]).denominator == 1 for step in steps)
    scale = lcm(*(quantity(step["runs"]).denominator for step in steps)) if steps else 1
    result.update(integer_batch_scale=scale, requires_integer_batch_scaling=not integral)
    if not integral:
        result["assumptions"].append("Fractional runs describe continuous scaling, not native recipe executions")
    if start_stock is not None and yield_mode == "guaranteed" and integral:
        result["feasible"] = all(initial.get(k, 0) >= v for k, v in required.items())
    return result
