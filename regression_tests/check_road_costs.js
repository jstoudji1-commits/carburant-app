const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
(async () => {
for (const file of ['index.html', 'templates/index.html']) {
  const source = fs.readFileSync(file, 'utf8');
  const c = {stationElectrique:()=>false, modeElectriqueRentabiliteActif:()=>false,
    coutTempsRentabiliteEuroHeure:0, carburantRentabiliteActuel:()=> 'diesel',
    carteTotalenergiesActive:()=>false, prixPublicStationRentabilite:s=>s.prix,
    prixRentabiliteAvecCarteTotalenergies:s=>s.prix, comptePremiumActif:()=>false,
    destinationNavigation:null, actualiserEconomieDestinationTotalenergies(){}, calculerMeilleureStation(){}};
  vm.createContext(c);
  vm.runInContext(source.slice(source.indexOf('function calculerEconomieMonetaireStation('), source.indexOf('function prixRentabiliteAvecCarteTotalenergies(')), c);
  vm.runInContext(source.slice(source.indexOf('function calculerCoutOptimisationStation('), source.indexOf('function afficherProchainRavitaillementTrajet(')), c);
  let resolve;
  c.fetchAvecDelai=()=>new Promise(r=>resolve=r);
  const stations=[{id:'cheap-long-road',prix:1.70,latitude:43,longitude:5}, {id:'accessible',prix:1.75,latitude:43.01,longitude:5.01}, {id:'reference',prix:2.10,latitude:43.02,longitude:5.02}];
  const compare=()=>c.calculerRentabiliteStations(stations,43,5,50,6,40);
  assert.equal(compare().enAttente,true);
  assert.equal(compare().stationsCalculees.length,0);
  resolve({ok:true,json:async()=>({trajets:[{aller_km:15,suite_km:25,detour_km:40,duree_detour_minutes:40},{aller_km:2,suite_km:3,detour_km:5,duree_detour_minutes:7},null]})});
  for(let i=0;i<12;i++) await Promise.resolve();
  const result=compare().stationsCalculees;
  assert.equal(result.length,2);
  assert(result[1].economieMonetaire>result[0].economieMonetaire);
  assert.equal(result[0].distanceDetourKm,40);
  assert.equal(result[1].tempsPerduMinutes,7);
  assert.equal(result[1].distanceCalculee,2);
  c.cacheDistancesStations.clear(); c.fetchAvecDelai=async()=>({ok:false});
  assert.equal(compare().enAttente,true);
  for(let i=0;i<12;i++) await Promise.resolve();
  assert.equal(compare().erreur,true);
  assert.equal(compare().stationsCalculees.length,0);
  console.log(file+': road-based ranking, asymmetric journeys, missing routes and failure verified');
}
})().catch(error=>{console.error(error);process.exitCode=1;});
