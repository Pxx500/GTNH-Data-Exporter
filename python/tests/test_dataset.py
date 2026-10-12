import tempfile
import unittest
import json
from pathlib import Path

from gtnh_data import Dataset, DatasetError
from .artifacts import choice, process, resource, slot, snapshot


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_presence_and_group_only_inputs_remain_discoverable(self):
        nbt = {"type": "compound", "value": {"mode": {"type": "int", "value": 7}}}
        artifact = snapshot(self.root / "capture", resources=[resource("mold", nbt=nbt), resource("copper"), resource("plate")],
                            groups=[{"id": "metals", "kind": "ore_dict", "name": "ingotCopper", "members": ["copper"], "provenance": {}}],
                            processes=[process("plate-making", [slot(choice("mold"), role="presence"), slot(choice(None, "ore_dict", group="metals"))], ["plate"])])
        dataset = Dataset.import_snapshot(artifact, self.root / "dataset.sqlite")
        self.assertEqual([r["id"] for r in dataset.find_processes(input_id="mold")["items"]], ["plate-making"])
        self.assertEqual([r["id"] for r in dataset.find_processes(input_id="copper")["items"]], ["plate-making"])
        self.assertEqual(dataset.get_resource("mold")["item"]["nbt"], nbt)
        self.assertEqual(dataset.get_process("plate-making")["item"]["inputs"][0]["role"], "presence")

    def test_invalid_import_preserves_previous_snapshot(self):
        database = self.root / "dataset.sqlite"
        original = snapshot(self.root / "original", id="original", resources=[resource("kept")])
        dataset = Dataset.import_snapshot(original, database)
        replacement = snapshot(self.root / "invalid", id="invalid", resources=[resource("wrong")])
        manifest_path = replacement / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["resources.jsonl.gz"]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(DatasetError, "checksum"):
            Dataset.import_snapshot(replacement, database)
        self.assertEqual(dataset.status()["snapshot_id"], "original")
        self.assertEqual(Dataset(database).get_resource("kept")["item"]["id"], "kept")

    def test_invalid_references_and_counts_do_not_activate(self):
        database = self.root / "dataset.sqlite"
        Dataset.import_snapshot(snapshot(self.root / "good", resources=[resource("kept")]), database)
        broken = snapshot(self.root / "broken", processes=[process("bad", [], ["missing"])])
        with self.assertRaisesRegex(DatasetError, "reference"):
            Dataset.import_snapshot(broken, database)
        self.assertEqual(Dataset(database).get_resource("kept")["item"]["id"], "kept")
        wrong_count = snapshot(self.root / "count", resources=[resource("wrong")])
        file = wrong_count / "manifest.json"
        manifest = json.loads(file.read_text())
        manifest["files"]["resources.jsonl.gz"]["records"] = 2
        file.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(DatasetError, "count"):
            Dataset.import_snapshot(wrong_count, database)
        self.assertEqual(Dataset(database).get_resource("kept")["item"]["id"], "kept")

    def test_replaced_snapshot_requires_a_new_handle(self):
        database = self.root / "dataset.sqlite"
        old = Dataset.import_snapshot(snapshot(self.root / "old", id="old", resources=[resource("before")]), database)
        new = Dataset.import_snapshot(snapshot(self.root / "new", id="new", resources=[resource("after")]), database)
        with self.assertRaisesRegex(DatasetError, "replaced"):
            old.find_resources()
        self.assertEqual(new.find_resources()["snapshot_id"], "new")
        self.assertEqual(new.find_resources()["items"][0]["id"], "after")

    def test_wildcards_exact_nbt_and_unresolved_matching_are_distinct(self):
        tag = {"type": "compound", "value": {"serial": {"type": "long", "value": "9223372036854775807"}}}
        rows = [resource("wild", registry_name="test:ore", metadata=32767),
                resource("concrete", registry_name="test:ore", metadata=3),
                resource("tagged", registry_name="test:ore", metadata=3, nbt=tag), resource("product")]
        rows[2]["custom_owner_data"] = {"not_lost": [1, 2]}
        insensitive = choice("tagged")
        insensitive["match"]["nbt_sensitive"] = False
        processes = [process("wildcard", [slot(choice("wild", "wildcard"))], ["product"]),
                     process("exact", [slot(choice("tagged"))], ["product"]),
                     process("nbt-ignored", [slot(insensitive)], ["product"]),
                     process("unknown", [slot(choice("concrete", "native_unknown"))], ["product"])]
        dataset = Dataset.import_snapshot(snapshot(self.root / "capture", resources=rows, processes=processes), self.root / "db.sqlite")
        found = dataset.find_processes(input_id="concrete")
        self.assertEqual({r["id"] for r in found["items"]}, {"wildcard", "nbt-ignored"})
        self.assertFalse(found["matching_complete"])
        self.assertEqual(found["unresolved_matches"], 1)
        self.assertEqual({r["id"] for r in dataset.find_processes(input_id="tagged")["items"]}, {"exact", "nbt-ignored"})
        self.assertEqual(dataset.get_resource("tagged")["item"]["nbt"], tag)
        self.assertEqual(dataset.get_resource("tagged")["item"]["custom_owner_data"], {"not_lost": [1, 2]})
        trace = dataset.trace_processes(start_id="concrete", target_id="product")
        self.assertTrue(any(entry["domain"] == "trace.matching" and entry["status"] == "partial" for entry in trace["coverage"]))

    def test_dependency_cycle_cannot_ground_its_own_seed(self):
        rows = [resource(id) for id in ("start", "locked", "loop", "product")]
        processes = [process("finish", [slot(choice("start")), slot(choice("locked"))], ["product", "locked"]),
                     process("cycle-out", [slot(choice("locked"))], ["loop"]),
                     process("cycle-in", [slot(choice("loop"))], ["locked"])]
        dataset = Dataset.import_snapshot(snapshot(self.root / "capture", resources=rows, processes=processes), self.root / "db.sqlite")
        trace = dataset.trace_processes(start_id="start", target_id="product")
        leaves = {r["resource_id"]: r for r in trace["leaves"]}
        self.assertEqual(leaves["locked"]["status"], "unresolved")
        self.assertEqual({p['id'] for p in trace['processes']}, {'finish'})
        self.assertTrue(trace["cycles"])
        self.assertFalse(trace["truncated"])

    def test_generated_blocks_remain_inspectable_but_do_not_seed_inventory_grounding(self):
        marker = 'generated_ore_block_not_mining_drop'
        sources = [
            {'id': 'generation', 'kind': 'ore_vein', 'display_name': 'configured vein',
             'outputs': [{'resource_id': 'generated', 'resource_semantics': marker}],
             'environment_ids': [], 'status': 'conditional', 'conditions': {'dimension': 7}, 'parameters': {}, 'provenance': {}},
            {'id': 'drop', 'kind': 'drop', 'display_name': 'real item drop',
             'outputs': [{'resource_id': 'real_drop', 'amount': 1}, {'resource_id': 'generated', 'resource_semantics': marker}],
             'environment_ids': [], 'status': 'active', 'conditions': {}, 'parameters': {}, 'provenance': {}},
        ]
        records = [process('first', [slot(choice('start')), slot(choice('generated')), slot(choice('real_drop'))], ['middle']),
                   process('finish', [slot(choice('middle'))], ['product', 'middle'])]
        coverage = [{'id': 'sources', 'domain': 'acquisition', 'status': 'complete', 'records': 2,
                     'reason': 'Synthetic source declarations are complete', 'provenance': {}}]
        artifact = snapshot(self.root / 'capture', resources=[resource(id) for id in ('start', 'generated', 'real_drop', 'middle', 'product')],
                            processes=records, sources=sources, coverage=coverage)
        dataset = Dataset.import_snapshot(artifact, self.root / 'db.sqlite')
        self.assertEqual(dataset.find_sources(resource_id='generated')['items'], [sources[1], sources[0]])
        result = dataset.trace_processes(start_id='start', target_id='product')
        leaves = {leaf['resource_id']: leaf for leaf in result['leaves']}
        self.assertEqual(leaves['generated']['status'], 'unresolved')
        self.assertEqual(leaves['generated']['sources'], ['drop', 'generation'])
        self.assertIn('generation', leaves['generated']['reason'])
        self.assertEqual(leaves['real_drop']['status'], 'available')
        self.assertIn('middle', leaves)
        self.assertIn('cycle needs', leaves['middle']['reason'])
        self.assertEqual({row['id'] for row in result['processes']}, {'first', 'finish'})

    def test_opaque_dynamic_producer_keeps_an_unresolved_boundary(self):
        for with_cycle in (False, True):
            with self.subTest(with_cycle=with_cycle):
                resources = [resource(id) for id in ("start", "locked", "loop", "product")]
                processes = [process("finish", [slot(choice("start")), slot(choice("locked"))], ["product"]),
                             process("opaque", [], ["locked"], executable=None, conditions={"dynamic_inputs": "unresolved"})]
                if with_cycle:
                    processes += [process("cycle-out", [slot(choice("locked"))], ["loop"]),
                                  process("cycle-in", [slot(choice("loop"))], ["locked"])]
                coverage = [{"id": "sources", "domain": "acquisition", "status": "complete", "records": 0,
                             "reason": "No sources in this fixture", "provenance": {}}]
                artifact = snapshot(self.root / f"capture-{with_cycle}", resources=resources, processes=processes, coverage=coverage)
                dataset = Dataset.import_snapshot(artifact, self.root / f"db-{with_cycle}.sqlite")
                self.assertIn("opaque", {item["id"] for item in dataset.find_processes()["items"]})
                trace = dataset.trace_processes(start_id="start", target_id="product")
                leaves = {leaf["resource_id"]: leaf for leaf in trace["leaves"]}
                self.assertIn("locked", leaves)
                self.assertEqual(leaves["locked"]["status"], "unresolved")
                self.assertEqual({p['id'] for p in trace['processes']}, {'finish'})
                lookup = dataset.find_processes(input_id="start")
                self.assertFalse(lookup["matching_complete"])
                self.assertEqual(lookup["unresolved_matches"], 1)
                self.assertTrue(any(entry["domain"] == "trace.matching" and entry["status"] == "partial" for entry in trace["coverage"]))

    def test_dynamic_output_template_is_inspectable_but_cannot_establish_a_path(self):
        template = process("template", [slot(choice("start"))], ["product"], executable=None,
                           conditions={"dynamic_output": "unresolved"})
        coverage = [{"id": "sources", "domain": "acquisition", "status": "complete", "records": 0,
                     "reason": "No sources in this fixture", "provenance": {}}]
        dataset = Dataset.import_snapshot(snapshot(self.root / "capture", resources=[resource("start"), resource("product")],
                                                   processes=[template], coverage=coverage), self.root / "db.sqlite")
        self.assertEqual([item["id"] for item in dataset.find_processes(input_id="start")["items"]], ["template"])
        self.assertEqual(dataset.get_process("template")["item"]["outputs"], template["outputs"])
        trace = dataset.trace_processes(start_id="start", target_id="product")
        self.assertEqual(trace["paths"], [])
        self.assertEqual(trace["processes"], [])
        leaves = {leaf["resource_id"]: leaf for leaf in trace["leaves"]}
        self.assertEqual(leaves["product"]["status"], "unresolved")
        self.assertTrue(any(entry["domain"] == "trace.outputs" and entry["status"] == "partial" for entry in trace["coverage"]))

    def test_wildcard_group_members_connect_the_concrete_trace_resource(self):
        resources = [resource("group-wild", registry_name="test:log", metadata=32767),
                     resource("concrete-log", registry_name="test:log", metadata=4), resource("plank")]
        groups = [{"id": "logs", "kind": "ore_dict", "name": "logWood", "members": ["group-wild"], "provenance": {}}]
        processes = [process("cut", [slot(choice(None, "ore_dict", group="logs"))], ["plank"])]
        dataset = Dataset.import_snapshot(snapshot(self.root / "capture", resources=resources, groups=groups, processes=processes), self.root / "db.sqlite")
        self.assertEqual(dataset.find_processes(input_id="concrete-log")["total"], 1)
        trace = dataset.trace_processes(start_id="concrete-log", target_id="plank")
        self.assertTrue(any(edge["source"] == "resource:concrete-log" and edge["target"] == "process:cut" for edge in trace["edges"]))

    def test_group_matching_honors_explicit_nbt_sensitivity(self):
        for mode in ("ore_dict", "unified"):
            with self.subTest(mode=mode):
                def tag(value):
                    return {"type": "compound", "value": {"mode": {"type": "int", "value": value}}}
                resources = [resource("one", registry_name="test:part", nbt=tag(1)),
                             resource("two", registry_name="test:part", nbt=tag(2)), resource("product"), resource("default-product")]
                groups = [{"id": "parts", "kind": "ore_dict", "name": "part", "members": ["one"], "provenance": {}}]
                strict = choice("one", mode, group="parts")
                strict["match"]["nbt_sensitive"] = True
                processes = [process("strict", [slot(strict)], ["product"], family="strict"),
                             process("default", [slot(choice("one", mode, group="parts"))], ["default-product"], family="default")]
                dataset = Dataset.import_snapshot(snapshot(self.root / mode, resources=resources, groups=groups, processes=processes), self.root / f"{mode}.sqlite")
                self.assertEqual(dataset.find_processes(input_id="two", family="strict")["total"], 0)
                self.assertEqual(dataset.find_processes(input_id="one", family="strict")["total"], 1)
                self.assertEqual(dataset.find_processes(input_id="two", family="default")["total"], 1)
                trace = dataset.trace_processes(start_id="one", target_id="product")
                strict_inputs = {edge["source"] for edge in trace["edges"] if edge["target"] == "process:strict"}
                self.assertEqual(strict_inputs, {"resource:one"})
                default_trace = dataset.trace_processes(start_id="one", target_id="default-product")
                default_inputs = {edge["source"] for edge in default_trace["edges"] if edge["target"] == "process:default"}
                self.assertEqual(default_inputs, {"resource:one", "resource:two"})

    def test_trace_preserves_branch_inputs_cycles_and_reports_limits(self):
        rows = [resource(id) for id in ("ore", "mold", "acid", "a", "b", "product", "byproduct")]
        processes = [process("smelt", [slot(choice("ore")), slot(choice("mold"), role="presence"), slot(choice("acid"))], ["a", "byproduct"]),
                     process("forward", [slot(choice("a"))], ["b", "a"]),
                     process("recycle", [slot(choice("b"))], ["a"]),
                     process("finish", [slot(choice("b"))], ["product"], conditions={"cleanroom": True})]
        sources = [{"id": "mold-source", "kind": "trade", "display_name": "mold", "outputs": [{"resource_id": "mold"}],
                    "environment_ids": [], "status": "conditional", "conditions": {"villager": True}, "parameters": {}, "provenance": {}}]
        coverage = [{"id": "partial-sources", "domain": "acquisition", "status": "partial", "records": 1,
                     "reason": "other mods not captured", "provenance": {}}]
        dataset = Dataset.import_snapshot(snapshot(self.root / "capture", resources=rows, processes=processes, sources=sources, coverage=coverage), self.root / "db.sqlite")
        result = dataset.trace_processes(start_id="ore", target_id="product")
        self.assertEqual({r["id"] for r in result["processes"]}, {"smelt", "forward", "finish"})
        self.assertIn("byproduct", {r["id"] for r in result["resources"]})
        leaves = {r["resource_id"]: r for r in result["leaves"]}
        self.assertEqual(leaves["ore"]["status"], "assumed")
        self.assertEqual(leaves["mold"]["status"], "conditional")
        self.assertEqual(leaves["acid"]["status"], "unresolved")
        self.assertTrue(any({"resource:a", "process:forward"} <= set(cycle) for cycle in result["cycles"]))
        self.assertFalse(result["truncated"])
        limited = dataset.trace_processes(start_id="ore", target_id="product", max_depth=1, max_processes=1)
        self.assertTrue(limited["truncated"])
        self.assertLessEqual(len(limited["processes"]), 1)


if __name__ == "__main__":
    unittest.main()
