// Run from the repository: node regression_tests/check_free_accounts.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

for (const file of ['index.html', 'templates/index.html']) {
    const html = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
    function extract(start, end) {
        const from = html.indexOf(start);
        assert(from >= 0, start);
        const to = html.indexOf(end, from);
        assert(to >= 0, end);
        return html.slice(from, to + end.length);
    }
    const store = new Map();
    let connected = true;
    let ios = false;
    let purchases = 0;
    let status = '';
    const context = vm.createContext({
        localStorage: {
            getItem: key => store.get(key) ?? null,
            setItem: (key, value) => store.set(key, value),
        },
        planCompteCle: 'plan', premiumCompteCle: 'premium',
        compteUtilisateurConnecte: () => connected,
        estPlateformeIOS: () => ios,
        acheterPremiumIOS: () => { purchases++; },
        definirStatutCompte: text => { status = text; },
        actualiserPlanCompte: () => {},
        window: {},
    });
    for (const name of ['planCompteActuel', 'lirePremiumCompte', 'comptePremiumActif']) {
        vm.runInContext(extract(`function ${name}() {`, '\n}'), context);
    }
    vm.runInContext(extract('window.changerPlanCompte = function(plan) {', '\n};'), context);

    assert.equal(context.comptePremiumActif(), false, 'New connected account stays free');
    context.window.changerPlanCompte('premium');
    assert.equal(context.comptePremiumActif(), false, 'Web/Android choice cannot grant Premium');
    assert.equal(store.has('plan'), false);
    assert.match(status, /abonnement/);
    ios = true;
    context.window.changerPlanCompte('premium');
    assert.equal(purchases, 1, 'iOS still invokes the purchase flow');
    assert.equal(context.comptePremiumActif(), false, 'Pending purchase does not grant Premium');
    store.set('premium', JSON.stringify({active: true}));
    assert.equal(context.comptePremiumActif(), true, 'Server-authorized bonus remains active');
    store.set('premium', JSON.stringify({active: false}));
    store.set('plan', 'premium');
    assert.equal(context.comptePremiumActif(), true, 'Existing Premium plan remains active');
    connected = false;
    assert.equal(context.comptePremiumActif(), false, 'Logged-out account has no Premium');
    console.log(`${file}: account access checks passed`);
}
