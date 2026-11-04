const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
for(const file of ['index.html','templates/index.html']){
 const s=fs.readFileSync(file,'utf8'),values=new Map();
 const elements={};for(const id of ['stat-carburant','stat-prix-minimum','stat-station-minimum'])elements[id]={innerHTML:'',classList:{add(){},remove(){}},setAttribute(){}};
 const c={carburantSelectionne:'gazole',vehiculeActif:()=>({profil:'essence'}),carburantPourVehicule:()=> 'e10',carteTotalenergiesCle:'total',
 localStorage:{getItem:k=>values.get(k)||null},document:{getElementById:id=>elements[id]||null},
 prixStationDisponible:p=>Number.isFinite(p)&&p>0&&p!==9.999,echapperHtml:x=>String(x),creerLogoEnseigne:()=>'',
 carburantEligibleAvantageTotalenergies:f=>['gazole','e10','sp95','sp98'].includes(f),
 stationElectrique:()=>false,modeElectriqueRentabiliteActif:()=>false,coutTempsRentabiliteEuroHeure:9,comptePremiumActif:()=>true,
 rayonCalculEconomieKm:25,destinationNavigation:null,derniereComparaisonRoutiere:null,
 distancesRoutieresRentabilite:stations=>({trajets:stations.map(()=>({aller_km:1,suite_km:1,detour_km:2,duree_detour_minutes:4}))})};
 vm.createContext(c);
 for(const [start,end] of [
 ['function carburantRentabiliteActuel()', 'function modeElectriqueRentabiliteActif()'],
 ['function modeElectriqueActif()', 'function carburantRentabiliteActuel()'],
 ['function normaliserStationCarte(', 'function creerMarqueurStation'],
 ['function carteTotalenergiesActive()', 'function actualiserPastillesTotalenergies()'],
 ['function prixRentabiliteAvecCarteTotalenergies(', 'function formaterEurosRentabilite('],
 ['function actualiserPrixMinimumAutour(', 'function remplacerStationsSurCarte('],
 ['function calculerCoutOptimisationStation(', 'function ajouterExplicationRentabilite('],
 ['function calculerRentabiliteStations(', 'function afficherProchainRavitaillementTrajet(']
 ]){
  const a=s.indexOf(start);let b=s.indexOf(end,a);if(start.startsWith('function normaliserStationCarte'))b=s.indexOf('\n}',a)+2;
  assert(a>=0&&b>a,start);vm.runInContext(s.slice(a,b),c);
 }
 assert.equal(c.carburantRentabiliteActuel(),'gazole','GO on map must not calculate E10 from saved vehicle');
 const raw=[{id:'inter',prix:2.117,carburant:'gazole',latitude:43,longitude:5,enseigne:'Intermarche'},
 {id:'total',prix:2.25,carburant:'gazole',latitude:43.01,longitude:5,avantage_totalenergies:{prix_plafond:1.99}},
 {id:'wrong-fuel',prix:1.978,carburant:'e10',latitude:43,longitude:5}];
 const original=JSON.stringify(raw);
 for(const active of [false,true,false,true,false]){
  values.set('total',String(active));c.actualiserPrixMinimumAutour(raw);
  assert(elements['stat-prix-minimum'].innerHTML.includes(active?'1,990':'2,117'));
  const result=c.calculerRentabiliteStations(raw.map(c.normaliserStationCarte),43,5,55,6,46.75);
  assert.equal(result.stationsCalculees.length,2,'Other fuel excluded');
  const total=result.stationsCalculees.find(x=>x.id==='total');
  assert.equal(total.prix,active?1.99:2.25);
  assert.equal(total.coutCarburantAchete,46.75*(active?1.99:2.25));
  assert(Math.abs(total.coutTotal-(46.75+0.12)*(active?1.99:2.25))<1e-9);
  const best=result.stationsCalculees.reduce((a,b)=>a.coutTotal<b.coutTotal?a:b);
  assert(best.prix>=(active?1.99:2.117),'Recommendation cannot undercut same-fuel displayed minimum');
  assert.equal(JSON.stringify(raw),original,'Public prices never mutated');
 }
 c.carburantSelectionne='e10';assert.equal(c.carburantRentabiliteActuel(),'e10');
 c.actualiserPrixMinimumAutour(raw);assert(elements['stat-prix-minimum'].innerHTML.includes('1,978'));
 console.log(file+': same-fuel minimum, full purchase/return cost and Total ON/OFF passed');
}
