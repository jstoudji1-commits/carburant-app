import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from road_costs import station_road_costs

class RoadCostsTests(unittest.TestCase):
    def test_asymmetric_return_not_doubled_outward(self):
        a=Mock();a.json.return_value={'code':'Ok','distances':[[5000]],'durations':[[300]]}
        b=Mock();b.json.return_value={'code':'Ok','distances':[[12000]],'durations':[[800]]}
        p=SimpleNamespace(latitude=43,longitude=5)
        with patch('road_costs.requests.get',side_effect=[a,b]) as get:
            result=station_road_costs(p,[p],heading=90)['trajets'][0]
            self.assertEqual(result['detour_km'],17)
            self.assertEqual(result['aller_km'],5)
            self.assertNotIn('fallback_speed',get.call_args.kwargs['params'])
    def test_destination_subtracts_direct_road_route(self):
        a=Mock();a.json.return_value={'code':'Ok','distances':[[5000,20000]],'durations':[[300,1200]]}
        b=Mock();b.json.return_value={'code':'Ok','distances':[[22000]],'durations':[[1500]]}
        p=SimpleNamespace(latitude=43,longitude=5)
        with patch('road_costs.requests.get',side_effect=[a,b]):
            result=station_road_costs(p,[p],p)['trajets'][0]
        self.assertEqual(result['detour_km'],7)
        self.assertEqual(result['duree_detour_minutes'],10)
    def test_unreachable_is_not_zero(self):
        a=Mock();a.json.return_value={'code':'Ok','distances':[[None]],'durations':[[None]]}
        b=Mock();b.json.return_value={'code':'Ok','distances':[[1000]],'durations':[[60]]}
        p=SimpleNamespace(latitude=43,longitude=5)
        with patch('road_costs.requests.get',side_effect=[a,b]):
            self.assertEqual(station_road_costs(p,[p])['trajets'],[None])
    def test_geographical_fallback_rejected(self):
        a=Mock();a.json.return_value={'code':'Ok','fallback_speed_cells':[[0,0]]}
        p=SimpleNamespace(latitude=43,longitude=5)
        with patch('road_costs.requests.get',return_value=a):
            with self.assertRaises(ValueError):station_road_costs(p,[p])

if __name__=='__main__':unittest.main()
