"""Documented national corrections, including opposite motorway service areas."""
import copy
import json
from pathlib import Path
import unittest

import update_totalenergies_avantage_carburant as updater


class NationalTotalEnergiesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = updater.charger_stations_gouvernementales(updater.ROOT / "stations.csv")
        cls.fixtures = json.loads(
            Path(__file__).with_name("totalenergies_verified_fixtures.json").read_text(encoding="utf-8")
        )

    def test_all_verified_associations_survive_regeneration(self):
        result = updater.construire_document([f["feature"] for f in self.fixtures], self.rows)
        self.assertEqual(result["unmatched"], [])
        self.assertEqual(result["conflicts"], [])
        for fixture in self.fixtures:
            locator = fixture["feature"]["properties"]["user_properties"]["location_id"]
            with self.subTest(locator=locator):
                self.assertEqual(result["stations"][fixture["target_id"]]["locator_id"], locator)

    def test_saved_associations_match_verified_sources(self):
        document = json.loads((updater.ROOT / "totalenergies_avantage_carburant.json").read_text(encoding="utf-8"))
        for fixture in self.fixtures:
            locator = fixture["feature"]["properties"]["user_properties"]["location_id"]
            with self.subTest(locator=locator):
                self.assertEqual(document["stations"][fixture["target_id"]]["locator_id"], locator)

    def test_missing_or_changed_verified_station_is_never_replaced_by_a_neighbour(self):
        for fixture in self.fixtures:
            locator = fixture["feature"]["properties"]["user_properties"]["location_id"]
            with self.subTest(locator=locator):
                rows = [r for r in self.rows if r["id"] != fixture["target_id"]]
                self.assertIsNone(updater.rapprocher(fixture["feature"], rows)[0])
                original = next(r for r in self.rows if r["id"] == fixture["target_id"])
                changed = {**original, "adresse": "Une autre aire sur la même autoroute"}
                self.assertIsNone(updater.rapprocher(fixture["feature"], rows + [changed])[0])


if __name__ == "__main__":
    unittest.main()
