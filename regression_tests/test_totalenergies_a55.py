"""Regression: the Total benefit belongs to Gignac Sud, not Eni Rebuty."""
import copy
from datetime import date
import json
import unittest
from unittest.mock import patch

import main
import update_totalenergies_avantage_carburant as updater


class A55BenefitTests(unittest.TestCase):
    def setUp(self):
        self.stations = updater.charger_stations_gouvernementales(updater.ROOT / "stations.csv")
        self.stations = [s for s in self.stations if s["id"] in {"13180001", "13700009"}]
        self.feature = {
            "properties": {
                "name": "REL.GIGNAC LA NERTHE",
                "user_properties": {"location_id": "NF059602", "brand": "TOTAL"},
                "address": {
                    "zipcode": "13180", "city": "GIGNAC LA NERTHE",
                    "lines": ["A55 - AIRE GIGNAC SUD LA NERTHE"],
                },
            },
            "geometry": {"coordinates": [5.258521, 43.390842]},
        }

    def test_generation_matches_total_even_when_eni_is_closer(self):
        document = updater.construire_document([self.feature], self.stations)
        self.assertEqual(set(document["stations"]), {"13700009"})
        self.assertEqual(document["stations"]["13700009"]["methode_rapprochement"], "identifiant_verifie")
        self.assertEqual(document["counts"]["unmatched_official_stations"], 0)

    def test_missing_total_never_assigns_its_benefit_to_eni(self):
        stations = [s for s in self.stations if s["id"] == "13180001"]
        station, _, reason = updater.rapprocher(self.feature, stations)
        self.assertIsNone(station)
        self.assertEqual(reason, "identifiant_verifie_absent")

    def test_changed_brand_requires_review(self):
        stations = copy.deepcopy(self.stations)
        for station in stations:
            if station["id"] == "13700009":
                station["enseigne"] = "Eni"
        result, _, reason = updater.rapprocher(self.feature, stations)
        self.assertIsNone(result)
        self.assertEqual(reason, "identifiant_verifie_incoherent")

    def test_ordinary_geographic_matching_is_unchanged(self):
        self.feature["properties"]["user_properties"]["location_id"] = "OTHER"
        self.feature["geometry"]["coordinates"] = [5.245, 43.388]
        station, distance, method = updater.rapprocher(self.feature, self.stations)
        self.assertEqual(station["id"], "13700009")
        self.assertLess(distance, 500)
        self.assertEqual(method, "coordonnees_et_code_postal")

    def test_saved_data_supplies_benefit_only_to_total_map_marker(self):
        document = json.loads((updater.ROOT / "totalenergies_avantage_carburant.json").read_text(encoding="utf-8"))
        self.assertNotIn("13180001", document["stations"])
        self.assertEqual(document["stations"]["13700009"]["locator_id"], "NF059602")
        with patch.object(main, "date") as clock:
            clock.today.return_value = date(2026, 10, 21)
            clock.fromisoformat.side_effect = date.fromisoformat
            stations = main.preparer_stations_pour_carte(self.stations, "gazole", 43.391, 5.257, 5)
        by_id = {s["id"]: s for s in stations}
        self.assertIsNone(by_id["13180001"]["avantage_totalenergies"])
        self.assertEqual(by_id["13700009"]["avantage_totalenergies"]["prix_plafond"], 1.99)


if __name__ == "__main__":
    unittest.main()
