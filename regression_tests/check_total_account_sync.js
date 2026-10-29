const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
for(const file of ['index.html','templates/index.html']){
 const s=fs.readFileSync(file,'utf8'),values=new Map();
 const c={localStorage:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},choixCarteTotalenergiesSession:null,derniereComparaisonRoutiere:null,carburantEligibleAvantageTotalenergies:()=>true,normaliserRayonStationsKm:x=>x};
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

 // Exercise the complete recommendation renderer, including a slow road refresh.
 function element(){return {textContent:'',hidden:false,disabled:false,children:[],appendChild(x){this.children.push(x)},classList:{add(){},remove(){}}};}
 const elements=Object.fromEntries(['economy-title','economy-subtitle','economy-route-button','economy-waze-button','economy-google-button'].map(k=>[k,element()]));
 c.window=c;
 Object.assign(c,{document:{getElementById:id=>elements[id],createElement:element,createTextNode:text=>({textContent:text})},
  nombreVehiculeEnregistre:key=>key==='vehicule-reservoir'?50:6,
  afficherDestinationNavigationDansEncadre:()=>false,definirModeDestinationEncadre(){},afficherProchainRavitaillementTrajet:()=>false,afficherTrajetPrepareDansEncadre:()=>false,
  prixTropAnciensPourCalcul:()=>false,latitudeUtilisateur:43,longitudeUtilisateur:5,stationsEconomie:[{id:'total',enseigne:'Total',adresse:'Test',latitude:43,longitude:5,prix:2.25,avantageTotalenergies:{prix_plafond:1.99}}],
  distanceDeplacementKm:()=>1,rayonCalculEconomieKm:25,navigationActive:false,routeNavigation:null,
  proposerStationPlusRentablePendantNavigation(){},ajouterExplicationRentabilite(){},economiePrecedentePourSeuil:null,declencherRecalculSousSeuil(){},actualiserNavigationPremium(){},programmerSynchronisationPrix(){},memeStation:(a,b)=>a.id===b.id,
  enregistrerEconomiePremium(){},tracerItineraire:(lat,lon,flag,station)=>{c.stationTracee=station;}});
 vm.runInContext(s.slice(s.indexOf('function choisirMeilleureStationRentabilite('),s.indexOf('window.enregistrerVehicule =')),c);
 c.choixCarteTotalenergiesSession=true;c.calculerMeilleureStation();
 assert.match(elements['economy-subtitle'].textContent,/1,990/);
 c.distancesRoutieresRentabilite=()=>({enAttente:true});
 c.choixCarteTotalenergiesSession=false;
 // Deliberately keep stale storage enabled: the latest explicit choice wins.
 c.localStorage.setItem(c.carteTotalenergiesCle,'true');
 c.calculerMeilleureStation();
 assert.match(elements['economy-title'].textContent,/Total/);
 assert.match(elements['economy-subtitle'].textContent,/2,250/);
 assert.equal(elements['economy-route-button'].hidden,false);
 assert.equal(elements['economy-route-button'].disabled,false);
 elements['economy-route-button'].onclick();assert.equal(c.stationTracee.prix,2.25);
 // A price refresh and network failure must also keep a usable recommendation.
 c.prixTropAnciensPourCalcul=()=>true;
 c.distancesRoutieresRentabilite=()=>({erreur:true});c.calculerMeilleureStation();
 assert.match(elements['economy-subtitle'].textContent,/2,250/);
 assert.equal(elements['economy-route-button'].disabled,false);
 c.choixCarteTotalenergiesSession=true;c.calculerMeilleureStation();
 assert.match(elements['economy-subtitle'].textContent,/1,990/);

 console.log(file+': reponse compte obsolete ignoree; classement et achat 2.25 / 1.99 verifies');
}
