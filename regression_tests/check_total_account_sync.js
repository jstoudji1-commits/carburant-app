const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
for(const file of ['index.html','templates/index.html']){
 const s=fs.readFileSync(file,'utf8'),values=new Map();
 const c={localStorage:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},choixCarteTotalenergiesSession:null,carburantEligibleAvantageTotalenergies:()=>true,normaliserRayonStationsKm:x=>x};
 const apply=s.slice(s.indexOf('function appliquerDonneesCompte('),s.indexOf('function actualiserInterfaceCompte('));
 for(const match of apply.matchAll(/\b\w+Cle\b/g)) c[match[0]]=match[0];
 for(const name of ['chargerVehicule','actualiserBoutonsFavoris','actualiserLieuxTrajet','actualiserRayonPremium','actualiserPlanCompte','actualiserParrainageCompte','actualiserBadgeCompte','remplirFormulaireMonCompte','actualiserAlertesPrixPremium','actualiserStatistiquesPremium','actualiserBanniereEconomiesOptiPlein','calculerMeilleureStation'])c[name]=()=>{};
 vm.createContext(c);
 vm.runInContext(apply,c);
 vm.runInContext(s.slice(s.indexOf('function carteTotalenergiesActive()'),s.indexOf('function actualiserControleCarteTotalenergies()')),c);
 vm.runInContext(s.slice(s.indexOf('function prixRentabiliteAvecCarteTotalenergies('),s.indexOf('function formaterEurosRentabilite(')),c);
 vm.runInContext(s.slice(s.indexOf('function calculerEconomieMonetaireStation('),s.indexOf('function prixRentabiliteAvecCarteTotalenergies(')),c);
 vm.runInContext(s.slice(s.indexOf('function calculerCoutOptimisationStation('),s.indexOf('function ajouterExplicationRentabilite(')),c);
 vm.runInContext(s.slice(s.indexOf('function calculerRentabiliteStations('),s.indexOf('function afficherProchainRavitaillementTrajet(')),c);
 Object.assign(c,{stationElectrique:()=>false,modeElectriqueRentabiliteActif:()=>false,coutTempsRentabiliteEuroHeure:0,carburantRentabiliteActuel:()=> 'gazole',comptePremiumActif:()=>false,destinationNavigation:null,distancesRoutieresRentabilite:()=>({trajets:[{aller_km:1,suite_km:2,detour_km:3,duree_detour_minutes:5}]})});
 c.appliquerDonneesCompte({preferences:{carte_totalenergies:true}});
 assert.equal(c.carteTotalenergiesActive(),true);
 let station={id:'total',prix:2.25,avantageTotalenergies:{prix_plafond:1.99}};
 for(const enabled of [true,false,true,false]){
  c.choixCarteTotalenergiesSession=enabled;
  c.localStorage.setItem(c.carteTotalenergiesCle,String(enabled));
  // An older server response arrives after the user's click.
  c.appliquerDonneesCompte({preferences:{carte_totalenergies:!enabled}});
  assert.equal(c.carteTotalenergiesActive(),enabled);
  station=c.calculerRentabiliteStations([station],43,5,50,6,40).stationsCalculees[0];
  assert.equal(station.prix,enabled?1.99:2.25);
  assert.equal(station.prixPublic,2.25);
  assert.equal(station.coutCarburantAchete,enabled?79.6:90);
  assert.equal(station.avantageTotalenergiesApplique,enabled);
 }
 console.log(file+': reponse compte obsolete ignoree; classement et achat 2.25 / 1.99 verifies');
}
