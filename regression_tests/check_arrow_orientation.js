const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
for (const file of ['index.html', 'templates/index.html']) {
    const source = fs.readFileSync(file, 'utf8');
    const start = source.indexOf('function actualiserOrientationFlecheUtilisateur(');
    const end = source.indexOf('function stabiliserCapDepartNavigation(', start);
    const arrow = {style: {}};
    let bearing = 0;
    const context = {
        Number, capFlecheUtilisateur: 0, capCarte: 90,
        suiviCarteActif: true, orientationAutomatiqueActive: true,
        navigationActive: false,
        map: {getBearing: () => bearing},
        marqueurUtilisateur: {getElement: () => ({querySelector: () => arrow})}
    };
    vm.createContext(context);
    vm.runInContext(source.slice(start, end), context);
    const update = context.actualiserOrientationFlecheUtilisateur;
    update(45);
    assert.equal(arrow.rotationGpsAffichee, 45, 'virage hors guidage avec camera encore a 0');
    bearing = 30; update();
    assert.equal(arrow.rotationGpsAffichee, 15, 'retour progressif pendant la rotation camera');
    bearing = 45; update();
    assert.equal(arrow.rotationGpsAffichee, 0, 'retour vers le haut apres alignement');
    context.navigationActive = true;
    bearing = 90; update(45);
    assert.equal(arrow.rotationGpsAffichee, -45, 'virage gauche en guidage');
    context.orientationAutomatiqueActive = false;
    bearing = 0; update(90);
    assert.equal(arrow.rotationGpsAffichee, 90, 'cap respecte en carte fixe');
    delete arrow.rotationGpsAffichee;
    update(179); update(181);
    assert.equal(arrow.rotationGpsAffichee, 181, 'pas de tour complet au passage de 180');
    delete arrow.rotationGpsAffichee;
    update(359); update(1);
    assert.equal(arrow.rotationGpsAffichee, 1, 'passage du nord');
    assert.equal(context.capCarte, 90, 'cap camera jamais modifie');
    console.log(file + ': 7 scenarios valides');
}
