import asyncio
import copy
import unittest
from unittest.mock import patch, Mock
import main


def route():
    return {"routes": [{"legs": [{"steps": [
        {"maneuver": {"type": "depart", "bearing_after": 90}},
        {"maneuver": {"type": "turn", "modifier": "uturn", "location": [2, 48]},
         "intersections": [{"location": [2, 48], "bearings": [0, 90, 270],
                            "entry": [True, False, True], "out": 2}]}
    ]}]}]}


class ReturnIntersectionTests(unittest.TestCase):
    def test_accepts_intersection(self):
        data = route()
        self.assertIs(main.valider_retour_intersection(data, 90), data)

    def test_rejects_midroad_and_forbidden_turn(self):
        for change in [
            {"bearings": [90, 270]}, {"entry": [True, False, False]},
            {"location": [3, 48]}, {"out": None}
        ]:
            with self.subTest(change=change):
                data = route()
                data['routes'][0]['legs'][0]['steps'][1]['intersections'][0].update(change)
                with self.assertRaises(ValueError):
                    main.valider_retour_intersection(data, 90)

    def test_rejects_reverse_departure(self):
        with self.assertRaises(ValueError):
            main.valider_retour_intersection(route(), 270)

    def test_allows_route_without_uturn(self):
        data = route()
        data['routes'][0]['legs'][0]['steps'].pop()
        main.valider_retour_intersection(data, 90)

    def test_protected_request_never_falls_back_to_unconstrained_provider(self):
        request = main.RequeteItineraire(points=[
            {"latitude": 48, "longitude": 2}, {"latitude": 48.1, "longitude": 2.1}
        ], cap_depart=90, retour_intersection=True)
        with patch.object(main, 'calculer_itineraire_openstreetmap', return_value=route()) as osm, \
             patch.object(main, 'calculer_itineraire_graphhopper') as gh:
            asyncio.run(main.calculer_itineraire(request))
            osm.assert_called_once()
            gh.assert_not_called()
        with patch.object(main, 'calculer_itineraire_openstreetmap', side_effect=ValueError), \
             patch.object(main, 'calculer_itineraire_graphhopper') as gh:
            with self.assertRaises(main.HTTPException):
                asyncio.run(main.calculer_itineraire(request))
            gh.assert_not_called()

    def test_bearing_list_matches_all_waypoints(self):
        points = [main.PointItineraire(latitude=48, longitude=2)] * 3
        response = Mock()
        response.json.return_value = {}
        with patch.object(main.http_requests, 'get', return_value=response) as get:
            main.calculer_itineraire_osrm(points, 359.9)
            self.assertEqual(get.call_args.kwargs['params']['bearings'], '0,45;;')

if __name__ == '__main__':
    unittest.main()
