import unittest
from copy import deepcopy
from fractions import Fraction

from gtnh_data.balance import chemical_ledger, find_loops, inspect_chemistry, ledger_json, net_ledger, witness_ledger


def slot(resource, amount, role="consume", *, chance=Fraction(1)):
    return {"role": role, "choices": [{"resource_id": resource, "amount": amount,
            "match": {"mode": "exact"}}], "consumption_chance":
            {"numerator": chance.numerator, "denominator": chance.denominator}}


def recipe(id, inputs, outputs):
    return {"id": id, "executable": True, "inputs": inputs,
            "outputs": [{"resource_id": resource, "amount": amount,
                         "chance": {"numerator": chance.numerator, "denominator": chance.denominator}}
                        for resource, amount, chance in outputs], "conditions": {}}


def element(name):
    return {"name": name, "element": {"id": name}, "components": [], "status": "complete",
            "component_unit_basis": "solid_material_unit", "density_gt_units": "3628800"}


def compound(name, components, basis="solid_material_unit", density="3628800"):
    return {"name": name, "element": None, "components": [
        {"coefficient": str(count), "material": material} for count, material in components],
        "status": "complete", "component_unit_basis": basis, "density_gt_units": density}


def facts(material, quantity=Fraction(1), basis="gt_material_units"):
    return {"schema_version": 1, "native_version": "5.09.54.221", "status": "associated",
            "gt_material_unit": "3628800", "chemistry_purity": "not_certified",
            "association": {"primary": {"material": material}}, "accounting": {
                "status": "eligible", "basis": basis,
                "quantity": {"numerator": str(quantity.numerator), "denominator": str(quantity.denominator)},
                "normalization": "native_top_level_component_parts" if basis == "gt_material_units" else "native_formula_unit"}}


class BalanceTests(unittest.TestCase):
    def test_closed_conservation_keeps_nonconsumed_tool_out_of_net(self):
        processes = {
            "split": recipe("split", [slot("a", 2), slot("tool", 1, "presence")],
                            [("b", 1, Fraction(1))]),
            "join": recipe("join", [slot("b", 1)], [("a", 2, Fraction(1))]),
        }
        ledger = net_ledger(processes, {"split": 1, "join": 1})
        self.assertEqual(ledger["status"], "complete")
        self.assertEqual(ledger["net"], {})
        self.assertEqual(ledger["consumed"], {"a": Fraction(2), "b": Fraction(1)})
        self.assertEqual(ledger["presence"], {"tool": Fraction(1)})

    def test_gaining_return_loop_has_explicit_start_stock_and_no_external_consumption(self):
        processes = {
            "split": recipe("split", [slot("a", 2)], [("b", 1, Fraction(1))]),
            "join": recipe("join", [slot("b", 1)], [("a", 3, Fraction(1))]),
        }
        result = find_loops(processes, "a")
        self.assertEqual(len(result["witnesses"]), 1)
        witness = result["witnesses"][0]
        self.assertEqual(witness["classification"], "gaining")
        self.assertEqual(witness["return_ratio"], Fraction(3, 2))
        self.assertEqual(witness["required_start_stock"], {"a": Fraction(2)})
        self.assertEqual(witness["ledger"]["net"], {"a": Fraction(1)})
        self.assertEqual(witness["external_consumption"], {})
        self.assertTrue(witness["autonomous"])

    def test_losing_stock_is_not_a_self_sustaining_loop(self):
        p = {"return": recipe("return", [slot("a", 2)], [("a", 1, Fraction(1))])}
        witness = find_loops(p, "a")["witnesses"][0]
        self.assertEqual(witness["classification"], "lossy")
        self.assertEqual(witness["return_ratio"], Fraction(1, 2))
        self.assertFalse(witness["autonomous"])

    def test_all_cooutputs_count_towards_return_gain(self):
        p = {"split": recipe("split", [slot("a", 1)], [("b", 1, Fraction(1)), ("a", 1, Fraction(1))]),
             "join": recipe("join", [slot("b", 1)], [("a", 1, Fraction(1))])}
        witnesses = find_loops(p, "a")["witnesses"]
        witness = next(x for x in witnesses if len(x["steps"]) == 2)
        self.assertEqual(witness["classification"], "gaining")
        self.assertEqual(witness["return_ratio"], Fraction(2))

    def test_external_reagent_gain_is_not_an_autonomous_amplifier(self):
        p = {"fed": recipe("fed", [slot("a", 1), slot("reagent", 1)], [("a", 2, Fraction(1))])}
        known = {"a": facts(element("H")), "reagent": facts(element("H"))}
        witness = find_loops(p, "a", chemical_facts=known)["witnesses"][0]
        self.assertEqual(witness["classification"], "gaining")
        self.assertEqual(witness["external_consumption"], {"reagent": Fraction(1)})
        self.assertFalse(witness["autonomous"])
        self.assertEqual(witness["chemical_balance"]["classification"], "balanced")

    def test_element_surplus_without_return_path_is_not_loop_proof(self):
        p = {"oneway": recipe("oneway", [slot("a", 1)], [("b", 2, Fraction(1))])}
        known = {"a": facts(element("H")), "b": facts(element("H"))}
        chemistry = chemical_ledger(net_ledger(p, {"oneway": 1}), known)
        self.assertEqual(chemistry["element_delta"], {"H": Fraction(1)})
        self.assertEqual(find_loops(p, "a", chemical_facts=known)["witnesses"], [])

    def test_stock_prefix_keeps_consumed_side_input_and_nonconsumed_tool(self):
        p = {"first": recipe("first", [slot("a", 2), slot("tool", 1, "presence")], [("b", 1, Fraction(1))]),
             "second": recipe("second", [slot("b", 1), slot("side", 3)], [("a", 2, Fraction(1))])}
        steps = [{"process_id": "first", "runs": 1}, {"process_id": "second", "runs": 1}]
        insufficient = witness_ledger(p, steps, start_stock={"a": 2})
        self.assertFalse(insufficient["feasible"])
        self.assertEqual(insufficient["required_start_stock"], {"a": Fraction(2), "tool": Fraction(1), "side": Fraction(3)})
        complete = witness_ledger(p, steps, start_stock=insufficient["required_start_stock"])
        self.assertTrue(complete["feasible"])
        self.assertEqual(complete["final_stock"]["tool"], Fraction(1))
        self.assertEqual(complete["net"], {"side": Fraction(-3)})

    def test_expected_output_is_separate_from_guaranteed_stock(self):
        p = {"split": recipe("split", [slot("a", 1)], [("b", 1, Fraction(1, 2))]),
             "join": recipe("join", [slot("b", 1)], [("a", 4, Fraction(1))])}
        self.assertEqual(find_loops(p, "a")["witnesses"], [])
        witness = find_loops(p, "a", yield_mode="expected")["witnesses"][0]
        self.assertEqual(witness["return_ratio"], Fraction(2))
        self.assertIsNone(witness["ledger"]["feasible"])
        self.assertFalse(witness["autonomous"])
        self.assertEqual(witness["ledger"]["yield_mode"], "expected")

    def test_optional_consume_chance_is_certain_but_explicit_unknown_is_unsupported(self):
        input = slot("a", 1)
        input.pop("consumption_chance")
        p = {"one": recipe("one", [input], [("b", 1, Fraction(1))])}
        self.assertEqual(net_ledger(p, {"one": 1})["consumed"], {"a": Fraction(1)})
        input["consumption_chance"] = None
        self.assertEqual(net_ledger(p, {"one": 1})["status"], "unsupported")
        input["consumption_chance"] = {"numerator": 1, "denominator": 2}
        self.assertEqual(net_ledger(p, {"one": 1})["consumed"], {"a": Fraction(1)})
        self.assertEqual(net_ledger(p, {"one": 1}, yield_mode="expected")["consumed"], {"a": Fraction(1, 2)})

    def test_unknown_quantity_output_chance_and_dynamic_template_never_form_a_loop(self):
        for field in ("amount", "chance"):
            with self.subTest(field=field):
                p = {"one": recipe("one", [slot("a", 1)], [("a", 2, Fraction(1))])}
                p["one"]["outputs"][0][field] = None
                self.assertEqual(net_ledger(p, {"one": 1})["status"], "unsupported")
                self.assertEqual(find_loops(p, "a")["witnesses"], [])
        p = {"one": recipe("one", [slot("a", 1)], [("a", 2, Fraction(1))])}
        p["one"]["conditions"]["dynamic_output"] = "unresolved"
        self.assertEqual(net_ledger(p, {"one": 1})["status"], "unsupported")

    def test_or_choices_require_selection_and_group_member_identity_is_concrete(self):
        input = slot("a", 1)
        input["choices"].append({"resource_id": "c", "amount": 2, "match": {"mode": "exact"}})
        p = {"one": recipe("one", [input], [("b", 1, Fraction(1))])}
        self.assertEqual(net_ledger(p, {"one": 1})["status"], "unsupported")
        selected = {"one": {"0": {"choice_index": 1, "resource_id": "c"}}}
        self.assertEqual(net_ledger(p, {"one": 1}, selections=selected)["consumed"], {"c": Fraction(2)})
        input["choices"][1]["match"] = {"mode": "wildcard", "group_id": "g"}
        selected["one"]["0"]["resource_id"] = "concrete"
        ledger = net_ledger(p, {"one": 1}, selections=selected, groups={"g": {"members": ["concrete"]}})
        self.assertEqual(ledger["consumed"], {"concrete": Fraction(2)})
        self.assertEqual(net_ledger(p, {"one": 1}, selections=selected)["status"], "unsupported")

    def test_nested_solid_components_and_fluid_root_keep_source_unit_basis(self):
        bronze = compound("bronze", [(3, element("Cu")), (1, element("Sn"))])
        potin = compound("potin", [(2, element("Pb")), (2, bronze), (1, element("Sn"))])
        solid = inspect_chemistry(facts(potin, Fraction(5)))
        self.assertEqual(solid["vector"], {"Pb": Fraction(2), "Cu": Fraction(3, 2), "Sn": Fraction(3, 2)})
        water = compound("water", [(2, element("H")), (1, element("O"))], "solid_material_unit")
        fluid = inspect_chemistry(facts(water, Fraction(1, 1000), "formula_units"))
        self.assertEqual(fluid["vector"], {"H": Fraction(1, 500), "O": Fraction(1, 1000)})
        # Its child preference must not override the certified ordinary-fluid root basis.
        self.assertEqual(inspect_chemistry(facts(water))["vector"], {"H": Fraction(2, 3), "O": Fraction(1, 3)})

    def test_missing_facts_or_unknown_child_basis_cannot_certify_chemistry(self):
        p = {"one": recipe("one", [slot("a", 1)], [("b", 1, Fraction(1))])}
        chemical = chemical_ledger(net_ledger(p, {"one": 1}), {"a": facts(element("H"))})
        self.assertEqual(chemical["status"], "unsupported")
        self.assertEqual(chemical["element_delta"], {})
        child = compound("unknown", [(1, element("H"))], "unresolved")
        self.assertEqual(inspect_chemistry(facts(compound("outer", [(1, child)])))["status"], "unsupported")
        loop = {"return": recipe("return", [slot("a", 1)], [("a", 2, Fraction(1))])}
        filtered = find_loops(loop, "a", chemical_kind="gaining")
        self.assertEqual(filtered["status"], "unsupported")
        self.assertEqual(filtered["chemical_unsupported_count"], 1)
        self.assertFalse(filtered["coverage_complete"])
        self.assertEqual(filtered["witnesses"], [])

    def test_chemical_filter_precedes_accepted_path_limit_and_mixed_delta_is_explicit(self):
        p = {"balanced": recipe("balanced", [slot("a", 1)], [("a", 1, Fraction(1))]),
             "gain": recipe("gain", [slot("a", 1)], [("a", 2, Fraction(1))])}
        result = find_loops(p, "a", chemical_facts={"a": facts(element("H"))}, chemical_kind="gaining", max_paths=1)
        self.assertEqual(result["witnesses"][0]["process_ids"], ["gain"])
        self.assertIn("path_limit", result["limit_reasons"])
        p = {"change": recipe("change", [slot("a", 1)], [("b", 1, Fraction(1))])}
        mixed = chemical_ledger(net_ledger(p, {"change": 1}), {"a": facts(element("H")), "b": facts(element("O"))})
        self.assertEqual(mixed["classification"], "mixed")
        self.assertEqual(mixed["positive_element_delta"], {"O": Fraction(1)})
        self.assertEqual(mixed["negative_element_delta"], {"H": Fraction(-1)})

    def test_search_bounds_report_incompleteness_and_rationals_survive_json(self):
        p = {"one": recipe("one", [slot("a", 1)], [("b", 1, Fraction(1))]),
             "two": recipe("two", [slot("b", 1)], [("a", 1, Fraction(1))])}
        for options, reason in (({"max_depth": 1}, "depth"), ({"max_states": 1}, "state_limit"),
                                ({"max_processes": 1}, "process_limit")):
            with self.subTest(options=options):
                result = find_loops(p, "a", **options)
                self.assertEqual(result["status"], "limited")
                self.assertIn(reason, result["limit_reasons"])
        self.assertEqual(ledger_json({"net": {"a": Fraction(-2, 3)}}), {"net": {"a": {"numerator": -2, "denominator": 3}}})

    def test_invalid_public_counts_never_produce_feasible_witness_or_partial_net(self):
        p = {"one": recipe("one", [slot("a", 1)], [("a", 2, Fraction(1))])}
        for count in (True, 0, -1, 0.5, {"numerator": 1, "denominator": 0},
                      {"numerator": 1, "denominator": -2}):
            with self.subTest(count=count):
                ledger = net_ledger(p, {"one": count})
                self.assertEqual(ledger["status"], "unsupported")
                self.assertEqual(ledger["net"], {})
                witness = witness_ledger(p, [{"process_id": "one", "runs": count}], start_stock={"a": 1})
                self.assertEqual(witness["status"], "unsupported")
                self.assertIsNone(witness["feasible"])
        fractional = witness_ledger(p, [{"process_id": "one", "runs": Fraction(1, 2)}], start_stock={"a": 1})
        self.assertEqual(fractional["net"], {"a": Fraction(1, 2)})
        self.assertIsNone(fractional["feasible"])
        self.assertEqual(fractional["integer_batch_scale"], 2)
        self.assertTrue(fractional["requires_integer_batch_scaling"])

    def test_invalid_native_unit_conversion_cannot_become_chemical_fact(self):
        f = facts(element("H"))
        for numerator, denominator in ((True, "1"), ("1", "0"), ("-1", "-1"), (1.5, "1")):
            with self.subTest(numerator=numerator, denominator=denominator):
                f["accounting"]["quantity"] = {"numerator": numerator, "denominator": denominator}
                self.assertEqual(inspect_chemistry(f)["status"], "unsupported")

    def test_native_density_and_nested_solids_preserve_red_alloy_and_pyrotheum_decomposition(self):
        # Pinned native p45187 and p45161 quantities, using their component hierarchy.
        redstone = compound("Redstone", [(1, element("Si")),
            (5, compound("Pyrite", [(1, element("Fe")), (2, element("S"))])),
            (1, compound("Ruby", [(1, element("Cr")), (2, element("Al")), (3, element("O"))])),
            (3, element("Hg"))])
        red_alloy = compound("RedAlloy", [(1, element("Cu")), (4, redstone)], density="18144000")
        coal = compound("Coal", [(1, element("C"))], density="7257600")
        dark_ash = compound("DarkAsh", [(1, element("C"))], density="7257600")
        blaze = compound("Blaze", [(1, dark_ash), (1, element("S")), (1, element("Ma"))], density="5443200")
        pyrotheum = compound("Pyrotheum", [(1, coal), (1, redstone), (1, blaze), (1, element("S"))], density="14515200")
        native_facts = {"alloy": facts(red_alloy), "cu": facts(element("Cu")), "redstone": facts(redstone),
                        "pyro": facts(pyrotheum), "coal": facts(coal), "blaze": facts(blaze), "s": facts(element("S"))}
        p = {"p45187": recipe("p45187", [slot("alloy", 5)], [("cu", 5, Fraction(1)), ("redstone", 20, Fraction(1))]),
             "p45161": recipe("p45161", [slot("pyro", 1)], [(r, 1, Fraction(1)) for r in ["coal", "redstone", "blaze", "s"]])}
        for pid in p:
            with self.subTest(pid=pid):
                result = chemical_ledger(net_ledger(p, {pid: 1}), native_facts)
                self.assertEqual(result["status"], "complete")
                self.assertEqual(result["classification"], "balanced")
                self.assertEqual(result["element_delta"], {})
        self.assertEqual(inspect_chemistry(facts(coal))["vector"], {"C": Fraction(2)})

    def test_native_candidate_consensus_certifies_quantity_without_choosing_material(self):
        water = compound("Water", [(2, element("H")), (1, element("O"))], "fluid_formula_unit")
        ice = compound("Ice", [(1, water)], "solid_material_unit")
        candidates = [facts(water, Fraction(1, 1000), "formula_units"), facts(ice, Fraction(1, 1000), "formula_units")]
        ambiguous = deepcopy(candidates[0])
        ambiguous["status"] = "ambiguous"
        ambiguous["accounting"] = {"status": "unresolved", "reason": "Native material association is ambiguous"}
        ambiguous["association"] = {"primary": None, "candidates": [
            {"material": f["association"]["primary"]["material"], "phase": "fluid", "phases": ["fluid"],
             "accounting": f["accounting"], "evidence": {"dispatcher": i == 0, "phase_catalog": True}}
            for i, f in enumerate(candidates)]}
        result = inspect_chemistry(ambiguous)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["vector"], {"H": Fraction(1, 500), "O": Fraction(1, 1000)})
        self.assertEqual(result["association_resolution"], "equivalent_native_candidate_vectors")
        self.assertIsNone(ambiguous["association"]["primary"])
        for change in ("contradictory", "unknown", "quantity", "phase"):
            with self.subTest(change=change):
                changed = deepcopy(ambiguous)
                candidate = changed["association"]["candidates"][1]
                if change == "contradictory":
                    candidate["material"]["components"][0]["coefficient"] = "2"
                    candidate["material"]["formula_display"] = "H2O"
                elif change == "unknown":
                    candidate["material"]["status"] = "unresolved"
                elif change == "quantity":
                    candidate["accounting"]["quantity"]["denominator"] = "500"
                else:
                    candidate["accounting"] = {"status": "unresolved", "reason": "Native fluid phase is ambiguous"}
                self.assertEqual(inspect_chemistry(changed)["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
