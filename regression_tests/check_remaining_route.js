const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
for (const file of ['index.html', 'templates/index.html']) {
    const source = fs.readFileSync(file, 'utf8');
    const start = source.indexOf('function calculerTrajetRestant(');
    const end = source.indexOf('function actualiserGuidageNavigation()', start);
    const context = {};
    vm.createContext(context);
    vm.runInContext(source.slice(start, end), context);
    const remaining = context.calculerTrajetRestant;
    const route = {distance: 2000, duration: 600, legs: [{steps: [
        {distance: 1000, duration: 100},
        {distance: 1000, duration: 500}
    ]}]};
    function check(route, progress, distance, duration) {
        const result = remaining(route, progress);
        assert.equal(result.distance, distance);
        assert.ok(Math.abs(result.duration - duration) < 1e-8);
    }
    check(route, 0, 2000, 600);
    check(route, 500, 1500, 550);
    check(route, 1000, 1000, 500);
    check(route, 1500, 500, 250);
    check(route, 2000, 0, 0);
    check(route, 2300, 0, 0);
    check(route, -20, 2000, 600);
    check({distance: 1000, duration: 100}, 500, 500, 50);
    check({distance: 0, duration: 0}, 0, 0, 0);
    check({distance: 4000, duration: 1200, legs: route.legs}, 2000, 2000, 1000);
    // A newly calculated route uses its own distance and time, without stale state.
    check({distance: 3000, duration: 900}, 0, 3000, 900);
    const guidanceEnd = source.indexOf('function distanceItineraireMetres()', end);
    new Function(source.slice(end, guidanceEnd));
    assert(source.slice(end, guidanceEnd).includes('afficherInfoItineraire('));
    console.log(file + ': 11 cas de progression et syntaxe du guidage valides');
}
