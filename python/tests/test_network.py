import unittest
from fractions import Fraction

from gtnh_data.network import nominal_energy, solve_network
from .test_balance import recipe, slot


def variant(id, inputs, outputs, eu, duration=1):
    record = recipe(id, inputs, [(resource, amount, Fraction(1)) for resource, amount in outputs])
    record.update(eu_per_tick=eu, duration_ticks=duration, amperage=4)
    return {"variant_id": id, "process_id": id, "process": record, "selections": {}}


class NetworkTests(unittest.TestCase):
    def test_base_plan_orders_producer_before_consumer_without_importing_its_parts(self):
        records = [variant("assembler", [slot("part", 2), slot("base", 1)], [("target", 1)], None),
                   variant("producer", [slot("base", 1), slot("tool", 1, "presence")], [("part", 1)], None)]
        plan = solve_network(records, target_id="target", allowed_feed_ids={"base"}, objective="recipe_runs")
        self.assertEqual(plan["status"], "complete")
        solution = plan["solutions"][0]
        self.assertEqual(solution["startup"]["required_start_stock"], {"base": 3, "tool": 1})
        self.assertEqual([step["process_id"] for step in solution["startup"]["steps"]], ["producer", "assembler"])

    def test_unrecycled_container_is_a_real_cofeed_and_closed_recycling_adds_energy(self):
        electrolysis = variant("electrolysis", [slot("water", 1000), slot("empty_cell", 1),
            slot("circuit", 1, "presence")], [("hydrogen", 2000), ("oxygen_cell", 1)], 30, 2000)
        open_result = solve_network([electrolysis], target_id="hydrogen", target_amount=2000,
                                    allowed_feed_ids={"water"}, primary_feed_id="water")
        self.assertEqual(open_result["status"], "infeasible")
        cofed = solve_network([electrolysis], target_id="hydrogen", target_amount=2000,
                              allowed_feed_ids={"water", "empty_cell"}, primary_feed_id="water")
        self.assertEqual(cofed["solutions"][0]["net_imports"], {"water": 1000, "empty_cell": 1})
        recycling = variant("recycling", [slot("oxygen_cell", 1)], [("empty_cell", 1), ("oxygen", 1000)], 16)
        closed = solve_network([electrolysis, recycling], target_id="hydrogen", target_amount=2000,
                               allowed_feed_ids={"water"}, primary_feed_id="water")
        solution = closed["solutions"][0]
        self.assertEqual(solution["nominal_energy"]["total_eu"], 60016)
        self.assertEqual(solution["nominal_energy"]["eu_per_target"], Fraction(3751, 125))
        self.assertEqual(solution["net_imports"], {"water": 1000})
        self.assertEqual(solution["startup"]["required_start_stock"], {"water": 1000, "empty_cell": 1, "circuit": 1})

    def test_lossy_regeneration_cannot_hide_an_external_reagent(self):
        records = [variant("a", [slot("water", 1), slot("x", 2)], [("y", 1), ("hydrogen", 1)], 1),
                   variant("b", [slot("y", 1)], [("x", 1)], 1)]
        result = solve_network(records, target_id="hydrogen", allowed_feed_ids={"water"})
        self.assertEqual(result["status"], "infeasible")
        cofed = solve_network(records, target_id="hydrogen", allowed_feed_ids={"water", "x"})
        self.assertEqual(cofed["solutions"][0]["net_imports"], {"water": 1, "x": 2})

    def test_unused_primary_feed_is_rejected_before_returning_other_networks(self):
        records = [variant("unrelated", [slot("x", 1)], [("x", 1), ("hydrogen", 1)], 1),
                   variant("water", [slot("water", 1)], [("hydrogen", 1)], 5)]
        result = solve_network(records, target_id="hydrogen", allowed_feed_ids={"water"}, primary_feed_id="water")
        self.assertEqual(result["status"], "complete")
        self.assertTrue(any(row["reason"] == "primary_feed_not_net_consumed" for row in result["rejected_witnesses"]))
        self.assertTrue(all(solution["ledger"]["net"]["water"] < 0 for solution in result["solutions"]))
        self.assertEqual(result["solutions"][0]["nominal_energy"]["eu_per_target"], 5)

    def test_unknown_and_nonpositive_energy_are_not_free_but_base_planning_keeps_them_unknown(self):
        records = [variant("unknown", [slot("base_a", 2), slot("base_b", 3)], [("widget", 2)], None),
                   variant("zero", [slot("base_a", 1)], [("widget", 1)], 0),
                   variant("negative", [slot("base_a", 1)], [("widget", 1)], -8)]
        audit = solve_network(records, target_id="widget", allowed_feed_ids={"base_a", "base_b"})
        self.assertEqual(audit["status"], "unsupported")
        self.assertEqual(len(audit["exclusions"]), 3)
        plan = solve_network(records[:1], target_id="widget", target_amount=3,
                             allowed_feed_ids={"base_a", "base_b"}, objective="recipe_runs",
                             start_stock={"base_a": 6, "base_b": 9})
        solution = plan["solutions"][0]
        self.assertEqual(solution["net_imports"], {"base_a": 3, "base_b": Fraction(9, 2)})
        self.assertEqual(solution["integer_batch_scale"], 2)
        self.assertIsNone(solution["nominal_energy"]["total_eu"])
        self.assertEqual(solution["nominal_energy"]["status"], "unknown")
        self.assertTrue(solution["startup"]["feasible"])

    def test_selected_or_quantity_presence_and_fractional_scaling_are_preserved(self):
        record = variant("or", [slot("unused", 1), slot("mold", 2, "presence")], [("hydrogen", 2)], 10)
        record["process"]["inputs"][0]["choices"].append(slot("water", 5)["choices"][0])
        record["selections"] = {"0": {"choice_index": 1, "resource_id": "water"}}
        result = solve_network([record], target_id="hydrogen", allowed_feed_ids={"water"})
        solution = result["solutions"][0]
        self.assertEqual(solution["net_imports"], {"water": Fraction(5, 2)})
        self.assertEqual(solution["executions"][0]["ledger"]["consumed"], {"water": Fraction(5, 2)})
        self.assertEqual(solution["ledger"]["presence"], {"mold": 2})
        self.assertEqual(solution["startup"]["required_start_stock"], {"water": 5, "mold": 2})
        self.assertEqual(solution["executions"][0]["selections"], record["selections"])

    def test_missing_chance_and_request_deadline_are_explicit(self):
        record = variant("unknown_chance", [slot("water", 1)], [("hydrogen", 1)], 1)
        record["process"]["outputs"][0]["chance"] = None
        unknown = solve_network([record], target_id="hydrogen", allowed_feed_ids={"water"})
        self.assertEqual(unknown["status"], "unsupported")
        self.assertEqual(unknown["exclusions"][0]["kind"], "unsupported_accounting")
        valid = variant("valid", [slot("water", 1)], [("hydrogen", 1)], 1)
        limited = solve_network([valid], target_id="hydrogen", allowed_feed_ids={"water"}, timeout_seconds=0.001)
        self.assertEqual(limited["status"], "incomplete")
        self.assertIn("solver_timeout", limited["search"]["limit_reasons"])
        self.assertFalse(limited["solutions"])

    def test_public_rational_inputs_and_energy_units_are_not_coerced(self):
        record = variant("valid", [slot("water", 1)], [("hydrogen", 1)], 1)
        for amount in [True, -1, {"numerator": 1, "denominator": 0}]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                solve_network([record], target_id="hydrogen", target_amount=amount, allowed_feed_ids={"water"})
        record["process"]["conditions"]["energy_unit"] = "rf"
        self.assertIsNone(nominal_energy(record["process"])[0])

    def test_expected_rates_are_not_guaranteed_stock(self):
        record = variant("chance", [slot("water", 1)], [("hydrogen", 2)], 100)
        record["process"]["outputs"][0]["chance"] = {"numerator": 1, "denominator": 2}
        guaranteed = solve_network([record], target_id="hydrogen", allowed_feed_ids={"water"})
        self.assertEqual(guaranteed["status"], "infeasible")
        expected = solve_network([record], target_id="hydrogen", allowed_feed_ids={"water"},
                                 yield_mode="expected", start_stock={"water": 1})
        self.assertEqual(expected["status"], "complete")
        solution = expected["solutions"][0]
        self.assertEqual(solution["nominal_energy"]["eu_per_target"], 100)
        self.assertIsNone(solution["startup"]["feasible"])
        self.assertTrue(solution["ledger"]["uncertainty"])

    def test_candidate_bounds_are_incomplete_instead_of_unsupported_or_infeasible(self):
        records = [variant("a", [slot("water", 1)], [("hydrogen", 1)], 10),
                   variant("b", [slot("water", 2)], [("hydrogen", 1)], 20)]
        result = solve_network(records, target_id="hydrogen", allowed_feed_ids={"water"}, max_columns=1)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["search"]["complete"])
        self.assertIn("candidate_column_limit", result["search"]["limit_reasons"])

    def test_joint_regeneration_is_verified_with_energy_coproducts_and_startup(self):
        variants = [variant("a", [slot("water", 1), slot("x", 1)], [("y", 1), ("hydrogen", 1)], 100),
                    variant("b", [slot("y", 1)], [("x", 1), ("oxygen", 1)], 10),
                    variant("direct", [slot("water", 1)], [("hydrogen", 1)], 200)]
        result = solve_network(variants, target_id="hydrogen", allowed_feed_ids={"water"},
                               primary_feed_id="water", max_solutions=1)
        self.assertEqual(result["status"], "complete")
        solution = result["solutions"][0]
        self.assertEqual({step["process_id"] for step in solution["executions"]}, {"a", "b"})
        self.assertEqual(solution["ledger"]["net"], {"water": Fraction(-1), "hydrogen": Fraction(1), "oxygen": Fraction(1)})
        self.assertEqual(solution["nominal_energy"]["total_eu"], Fraction(110))
        self.assertEqual(solution["nominal_energy"]["eu_per_target"], Fraction(110))
        self.assertEqual(solution["startup"]["required_start_stock"], {"water": Fraction(1), "x": Fraction(1)})
        self.assertTrue(solution["witness_verified"])


if __name__ == "__main__":
    unittest.main()
