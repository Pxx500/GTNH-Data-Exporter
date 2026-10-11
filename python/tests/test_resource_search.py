import tempfile
import unittest
from pathlib import Path

from gtnh_data import Dataset
from .artifacts import resource, snapshot


class ResourceSearchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        records = []
        for id, display, registry in (
            ("a-broad", "Iron Plate Dust", "test:broad"),
            ("z-exact", "Iron Plate", "test:iron_plate"),
            ("z-variant", "Iron Plate", "test:iron_plate"),
            ("registry-only", None, "gregtech:metaitem_iron_plate"),
            ("resource:iron-plate", "Unnamed material", "test:other"),
            ("noise", "Iron Dust", "test:dust"),
            ("fluid", "Iron Plasma", "iron_plasma"),
        ):
            row = resource(id, registry_name=registry)
            row["display_name"] = display
            if id == "z-variant":
                row["metadata"] = 4
                row["nbt"] = {"type": "compound", "value": {"mode": {"type": "int", "value": 2}}}
            if id == "fluid":
                row.update(kind="fluid", metadata=None)
            records.append(row)
        self.dataset = Dataset.import_snapshot(snapshot(self.root / "snapshot", resources=records), self.root / "db.sqlite")

    def test_tolerant_autocomplete_preserves_ranked_pagination_and_variants(self):
        expected = {"a-broad", "z-exact", "z-variant", "registry-only", "resource:iron-plate"}
        typo = self.dataset.find_resources(q="iron pltae", limit=8)
        self.assertEqual({item["id"] for item in typo["items"]}, expected)
        exact = self.dataset.find_resources(q="iron plate", limit=8)
        self.assertEqual([item["id"] for item in exact["items"][:2]], ["z-exact", "z-variant"])
        self.assertEqual({item["id"] for item in exact["items"]}, expected)
        reversed_words = self.dataset.find_resources(q="plate iron", limit=8)
        self.assertEqual({item["id"] for item in reversed_words["items"]}, expected)
        partial = self.dataset.find_resources(q="ir pla", kind="item", limit=8)
        self.assertEqual({item["id"] for item in partial["items"]}, expected)
        self.assertEqual(self.dataset.find_resources(q="ir pla", kind="fluid")["items"][0]["id"], "fluid")
        self.assertEqual(exact["total"], len(expected))
        page = self.dataset.find_resources(q="iron plate", offset=1, limit=1)
        self.assertEqual(page["total"], exact["total"])
        self.assertEqual(page["items"], exact["items"][1:2])
        self.assertEqual(self.dataset.find_resources(q="gregtech:metaitem_iron_plate")["items"][0]["id"], "registry-only")
        self.assertEqual(self.dataset.find_resources(q="resource:iron-plate")["items"][0]["id"], "resource:iron-plate")
        self.assertNotEqual(exact["items"][0]["metadata"], exact["items"][1]["metadata"])
        self.assertEqual(self.dataset.find_resources(q="no_such_material")["total"], 0)


if __name__ == "__main__":
    unittest.main()
