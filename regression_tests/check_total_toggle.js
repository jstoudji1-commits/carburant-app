const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
(async()=>{for(const file of ['index.html','templates/index.html']){
const s=fs.readFileSync(file,'utf8');let value='false',checked=true,calculs=0,release;
const c={window:null,document:{getElementById:()=>({checked})},localStorage:{getItem:()=>value,setItem:(k,v)=>value=v},carteTotalenergiesCle:'total',navigationActive:false,trajetPrepare:null,stationNavigationActive:null,validationTrajetPrepareEnCours:false,recalculTrajetPrepareAvantageEnCours:false,latitudeUtilisateur:43,longitudeUtilisateur:5,latitudeDerniereRecherche:43,longitudeDerniereRecherche:5,actualiserPastillesTotalenergies(){},programmerSauvegardeCompte(){},calculerMeilleureStation(){calculs++},actualiserStationsEconomieVehicule:()=>new Promise(r=>release=r),afficherInfoItineraire(){},setTimeout,carteTotalenergiesActive:()=>value==='true'};c.window=c;vm.createContext(c);
vm.runInContext(s.slice(s.indexOf('var revisionOptionTotalenergies ='),s.indexOf('function masquerPubliciteVide()')),c);
vm.runInContext(s.slice(s.indexOf('async function recalculerTrajetPrepareApresChangementAvantageTotalenergies()'),s.indexOf('window.annulerPreparationTrajet')),c);
let p=c.modifierCarteTotalenergies();assert.equal(calculs,1);assert.equal(value,'true');await Promise.resolve();
checked=false;assert.equal(c.modifierCarteTotalenergies(),p);assert.equal(value,'false');release(false);
for(let i=0;i<6;i++)await Promise.resolve();release(false);await p;assert.equal(c.traitementOptionTotalenergies,null);assert(calculs>=4);
// Prepared route and active guidance must update both savings and geometry.
c.actualiserStationsEconomieVehicule=async()=>true;
for(const active of [false,true]){
 c.navigationActive=active;c.trajetPrepare={destination:{latitude:44,longitude:6},jauge:50,routeDirecte:{geometry:{coordinates:[[5,43],[6,44]]}}};c.jaugeTrajetTemporaire=40;
 c.chargerStationsTrajetFrance=async()=>[];
 c.calculerArretsRavitaillementRoute=()=>({arrets:[],economieTotale:value==='true'?10:2,autonomieKm:100,distanceTrajetKm:150});
 c.calculerRouteAvecCoordonnees=async()=>({distance:150000,duration:6000,geometry:{coordinates:[[5,43],[6,44]]}});
 for(const key of ['afficherMarqueursRavitaillement','masquerStationsClassiquesSurCarte','configurerBoutonsNavigationExterneTrajetPrepare','afficherEtatPlanificateurCalcule','afficherTrajetPrepareDansEncadre','definirEtapesNavigationDepuisRoute','actualiserEncadreDestinationNavigation','actualiserGuidageNavigation'])c[key]=()=>{};
 c.carburantRentabiliteActuel=()=> 'diesel';c.htmlArretsRavitaillement=()=>'';let preview;c.dessinerItineraire=(coords,p)=>preview=p;
 for(const enabled of [true,false]){checked=enabled;await c.modifierCarteTotalenergies();assert.equal(c.trajetPrepare.carteTotalenergies,enabled);assert.equal(c.trajetPrepare.economieTotale,enabled?10:2);assert.equal(preview,!active);if(active)assert.equal(c.economieEstimeeFigee,enabled?10:2);}
}
// Cancellation while loading must not restore an abandoned trip.
let finish;let calls=0;c.calculerRouteAvecCoordonnees=()=>++calls===1?new Promise(r=>finish=r):Promise.resolve({geometry:{coordinates:[]}});
const pending=c.recalculerTrajetPrepareApresChangementAvantageTotalenergies();c.trajetPrepare=null;finish({geometry:{coordinates:[]}});await pending;assert.equal(c.trajetPrepare,null);
c.stationNavigationActive={id:'total'};c.stationsEconomie=[{id:'total'}];
c.nombreVehiculeEnregistre=()=>50;c.memeStation=(a,b)=>a.id===b.id;
c.calculerRentabiliteStations=()=>({stationsCalculees:[{id:'total',economieMonetaire:value==='true'?8:1}]});
for(const enabled of [true,false]){value=String(enabled);c.actualiserEconomieDestinationTotalenergies();assert.equal(c.economieEstimeeFigee,enabled?8:1);}
console.log(file+': bascules rapides, recalcul immediat, trajet et guidage verifies');
}})().catch(e=>{console.error(e);process.exitCode=1});
