"""Road distances for station comparison; no geographic fallback."""
import math
import requests


def station_road_costs(origin, stations, destination=None, heading=None):
    points = [origin] + stations + ([destination] if destination else [])
    target = len(points) - 1 if destination else 0
    coords = ';'.join(f'{p.longitude},{p.latitude}' for p in points)
    url = 'https://router.project-osrm.org/table/v1/driving/' + coords
    params = {'annotations': 'distance,duration', 'radiuses': ';'.join(['200'] * len(points))}
    if heading is not None and math.isfinite(heading):
        params['bearings'] = ';'.join([f'{round(heading) % 360},45'] + [''] * (len(points)-1))
    def table(sources, destinations):
        response = requests.get(url, params={**params, 'sources':sources, 'destinations':destinations}, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get('code') != 'Ok' or data.get('fallback_speed_cells'):
            raise ValueError('Distances routieres indisponibles')
        return data
    indices = ';'.join(str(i) for i in range(1,len(stations)+1))
    outward = table('0', indices + (';' + str(target) if destination else ''))
    onward = table(indices, str(target))
    def valid(value):
        return isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value) and value >= 0
    direct = outward['distances'][0][-1] if destination else 0
    direct_time = outward['durations'][0][-1] if destination else 0
    results=[]
    for i in range(len(stations)):
        a,b=outward['distances'][0][i],onward['distances'][i][0]
        ta,tb=outward['durations'][0][i],onward['durations'][i][0]
        if not all(valid(x) for x in (a,b,ta,tb,direct,direct_time)):
            results.append(None)
        else:
            results.append({'aller_km':a/1000,'suite_km':b/1000,
                'detour_km':max(0,a+b-direct)/1000,
                'duree_detour_minutes':max(0,ta+tb-direct_time)/60})
    return {'trajets':results,'distance_directe_km':direct/1000 if valid(direct) else None}
