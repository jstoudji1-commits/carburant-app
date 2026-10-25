import unittest
import main

class MotorwayGuidanceTests(unittest.TestCase):
    def step(self, instruction):
        return main.convertir_route_graphhopper({'paths':[{'points':{'coordinates':[[5,43],[5.01,43.01]]},'instructions':[instruction]}]})['legs'][0]['steps'][0]
    def test_keep_directions_are_not_roundabouts(self):
        for sign,side in [(7,'right'),(-7,'left')]:
            step=self.step({'sign':sign,'text':'Restez a '+side})
            self.assertEqual(step['maneuver']['type'],'fork')
            self.assertEqual(step['maneuver']['modifier'],side)
    def test_numbered_exit_preserved(self):
        for number in ['24','30.1','12A']:
            step=self.step({'sign':7,'text':'Restez a droite','motorway_junction':number,'street_name':'D 113'})
            self.assertEqual(step['maneuver']['type'],'off ramp')
            self.assertEqual(step['exits'],number)
            self.assertIsNone(step['maneuver']['exit'])
    def test_roundabout_keeps_ordinal_not_motorway_reference(self):
        step=self.step({'sign':6,'text':'Au rond-point prenez la sortie 2','exit_number':2,'motorway_junction':'24'})
        self.assertEqual(step['maneuver']['type'],'roundabout')
        self.assertEqual(step['maneuver']['exit'],2)
        self.assertEqual(step['exits'],'')
    def test_unnumbered_exit_not_given_road_number(self):
        step=self.step({'sign':7,'text':'Prenez la sortie','street_ref':'A7','street_name':'D113'})
        self.assertEqual(step['maneuver']['type'],'off ramp')
        self.assertEqual(step['exits'],'')

if __name__=='__main__':unittest.main()
