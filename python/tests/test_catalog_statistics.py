import unittest
from copy import deepcopy
from fractions import Fraction

from gtnh_data.statistics import analyze_statistics
from .test_balance import recipe, slot


def process_row(id, batch, cost, *, conditions=None):
    record = recipe(id, [slot("water", batch), slot("tool", 1, "presence")],
                    [("hydrogen", batch * 2, Fraction(1))])
    record.update(family="gregtech:test", duration_ticks=1, eu_per_tick=cost,
                  amperage=2, provenance={"owner": "GTRecipe", "index": id})
    record["conditions"].update(conditions or {})
    return {"process": record, "recipe_tier": {"process_id": id, "status": "known", "tier": 1,
             "name": "LV", "scope": "recipe_voltage_not_machine_capability"}}


class CatalogStatisticsTests(unittest.TestCase):
    def test_overview_preserves_literal_namespaces_group_sizes_and_exact_quartiles(self):
        resources = [{"id": "a", "kind": "item", "registry_name": "gregtech:item"},
                     {"id": "b", "kind": "fluid", "registry_name": "water"}]
        groups = [{"id": "one", "kind": "unified", "members": ["a"]},
                  {"id": "two", "kind": "ore_dict", "members": ["a", "b"]}]
        rows = [process_row(str(i), 1, i, conditions={"variant": i}) for i in range(1, 6)]
        result = analyze_statistics(iter(resources), iter(groups), iter(rows))
        self.assertEqual(result["overview"]["resources"]["by_namespace"], {"gregtech": 1, "unqualified": 1})
        self.assertEqual(result["overview"]["groups"]["members_total"], 3)
        self.assertEqual(result["overview"]["groups"]["member_counts"]["median"], Fraction(3, 2))
        distribution = result["distributions"][0]
        self.assertEqual((distribution["count"], distribution["q1"], distribution["median"], distribution["q3"], distribution["iqr"]),
                         (5, Fraction(2), Fraction(3), Fraction(4), Fraction(2)))
        self.assertEqual(distribution["comparison"], "exploratory_across_products")

    def test_predicates_or_order_chances_and_presence_are_not_semantically_merged(self):
        original = process_row("original", 1, 10)
        original["process"]["inputs"][0]["choices"].append(slot("other", 2)["choices"][0])
        group = deepcopy(original)
        group["process"]["id"] = "different_group"
        group["process"]["eu_per_tick"] = 20
        group["process"]["inputs"][0]["choices"][0]["match"] = {"mode": "unified", "group_id": "group-a"}
        ordered = deepcopy(original)
        ordered["process"]["id"] = "different_order"
        ordered["process"]["eu_per_tick"] = 30
        ordered["process"]["inputs"][0]["choices"].reverse()
        chance = deepcopy(original)
        chance["process"]["id"] = "different_chance"
        chance["process"]["eu_per_tick"] = 40
        chance["process"]["outputs"][0]["chance"] = {"numerator": 1, "denominator": 2}
        tool = deepcopy(original)
        tool["process"]["id"] = "different_tool_quantity"
        tool["process"]["eu_per_tick"] = 50
        tool["process"]["inputs"][1]["choices"][0]["amount"] = 2
        nbt = deepcopy(original)
        nbt["process"]["id"] = "different_typed_condition"
        nbt["process"]["eu_per_tick"] = 60
        nbt["process"]["conditions"]["stack"] = {"type": "compound", "value": {"charge": {"type": "long", "value": "9007199254740993"}}}
        result = analyze_statistics([], [], [original, group, ordered, chance, tool, nbt])
        self.assertFalse(result["findings"])
        self.assertEqual(result["search"]["signature_buckets"], 6)

    def test_identical_group_predicates_and_native_quantities_normalize_but_members_are_not_guessed(self):
        rows = [process_row("one", 1, 20), process_row("two", 2, 60)]
        for row in rows:
            choice = row["process"]["inputs"][0]["choices"][0]
            choice["match"] = {"mode": "unified", "group_id": "group-a", "nbt_sensitive": True}
            choice["native_amount"] = choice["amount"]
        result = analyze_statistics([], [{"id": "group-a", "kind": "unified", "members": ["water", "other"]}], rows)
        finding = result["findings"][0]
        self.assertEqual(finding["cost_ratio"], Fraction(3, 2))
        choice = finding["normalized_signature"]["inputs"][0]["choices"][0]
        self.assertEqual(choice["native_amount"], 1)
        self.assertEqual(choice["match"]["group_id"], "group-a")
        self.assertEqual(finding["comparison_scope"], "identical_captured_predicates_and_conditions_normalized_batch")

    def test_missing_disabled_fake_dynamic_and_unknown_energy_stay_explicit(self):
        rows = [process_row("disabled", 1, 10), process_row("fake", 1, 10),
                process_row("dynamic", 1, 10), process_row("unknown", 1, 10),
                process_row("energy", 1, None), process_row("chance", 1, 10)]
        rows[0]["process"]["executable"] = False
        rows[1]["process"]["conditions"]["fake"] = True
        rows[2]["process"]["conditions"]["dynamic_output"] = "unresolved"
        rows[3]["process"]["executable"] = None
        rows[4]["process"]["duration_ticks"] = None
        rows[5]["process"]["outputs"][0]["chance"] = None
        result = analyze_statistics([], [], rows)
        overview = result["overview"]["processes"]
        self.assertEqual(overview["count"], 6)
        self.assertEqual(overview["by_executability"], {"true": 4, "false": 1, "unknown": 1})
        self.assertEqual(result["exclusions"]["inactive_fake_dynamic_or_unknown"], 4)
        self.assertEqual(result["exclusions"]["unknown_or_nonpositive_nominal_energy"], 1)
        self.assertEqual(result["exclusions"]["unknown_quantity_or_probability"], 1)
        self.assertFalse(result["findings"])

    def test_bucket_limit_keeps_overview_complete_and_record_timeout_is_partial(self):
        rows = [process_row("one", 1, 20), process_row("two", 1, 30),
                process_row("other", 1, 50, conditions={"heat": 10})]
        capped = analyze_statistics([], [], rows, max_signature_buckets=1)
        self.assertEqual(capped["overview"]["processes"]["count"], 3)
        self.assertTrue(capped["search"]["overview_complete"])
        self.assertFalse(capped["search"]["complete"])
        self.assertIn("signature_bucket_limit", capped["search"]["limit_reasons"])
        self.assertEqual(len(capped["findings"]), 1)
        partial = analyze_statistics([], [], rows, max_records=1)
        self.assertEqual(partial["search"]["records"], 1)
        self.assertFalse(partial["search"]["overview_complete"])
        limited = analyze_statistics([], [], rows, timeout_seconds=0.000001)
        self.assertIn("analysis_timeout", limited["search"]["limit_reasons"])

    def test_top_findings_are_bounded_by_within_cohort_spread_not_product_cost(self):
        rows = []
        for group, ratio in enumerate([2, 3, 4]):
            rows.extend([process_row(f"{group}low", 1, 10, conditions={"group": group}),
                         process_row(f"{group}high", 1, 10 * ratio, conditions={"group": group})])
        result = analyze_statistics([], [], rows, max_findings=2)
        self.assertEqual([finding["cost_ratio"] for finding in result["findings"]], [4, 3])
        self.assertEqual(result["search"]["findings_total"], 3)
        self.assertIn("finding_limit", result["search"]["limit_reasons"])

    def test_public_bounds_reject_boolean_and_invalid_limits(self):
        for kwargs in [{"max_records": True}, {"max_findings": 0}, {"max_signature_buckets": -1}, {"timeout_seconds": 61}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                analyze_statistics([], [], [], **kwargs)

    def test_cost_spread_normalizes_batches_without_dropping_presence_or_conditions(self):
        rows = [process_row("small", 1, 20), process_row("large", 2, 60),
                process_row("other_condition", 1, 100, conditions={"heat": 10})]
        result = analyze_statistics(iter([]), iter([]), iter(rows))
        self.assertEqual(len(result["findings"]), 1)
        finding = result["findings"][0]
        self.assertEqual(finding["process_ids"], ["small", "large"])
        self.assertEqual(finding["normalized_costs"], {"minimum": Fraction(20), "maximum": Fraction(30)})
        self.assertEqual(finding["cost_ratio"], Fraction(3, 2))
        self.assertEqual(finding["batch_scales"], {"small": Fraction(1), "large": Fraction(2)})
        self.assertEqual(finding["normalized_signature"]["inputs"][1]["choices"][0]["amount"], 1)
        self.assertFalse(finding["confirmed_bug"])


if __name__ == "__main__":
    unittest.main()
