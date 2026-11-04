const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
(async()=>{for(const file of ['index.html','templates/index.html']){
 const s=fs.readFileSync(file,'utf8');let now=1000,interval,draws=0,stops=0,resolve;
 const els={};const classes=new Set();
 const button={insertAdjacentElement(where,e){els[e.id]=e},classList:{remove(){},add(){}}};els['economy-route-button']=button;
 const c={window:null,Date:{now:()=>now},document:{body:{classList:{contains:k=>classes.has(k),toggle(k,v){v?classes.add(k):classes.delete(k)}}},getElementById:id=>els[id]||null,createElement:()=>({setAttribute(){},remove(){delete els[this.id]}}),addEventListener(){}},
 setInterval:fn=>{interval=fn;return 1},clearInterval:()=>{interval=null},requestAnimationFrame:fn=>fn(),scrollTo(){},scrollY:40,map:{_map:{resize(){}},closePopup(){}},
 navigationActive:false,latitudeUtilisateur:43,longitudeUtilisateur:5,routeNavigation:null,destinationNavigation:null,
 trouverStationParCoordonnees:()=>({id:'total'}),effacerMarqueursRavitaillement(){},afficherInfoItineraire(){},capNavigationFiable:()=>0,
 demanderRouteItineraire:()=>new Promise(r=>resolve=r),normaliserRouteItineraire:d=>d.routes[0],dessinerItineraire(){draws++},
 actualiserNavigationPremium(){},actualiserEncadreDestinationNavigation(){},proposerRavitaillementTrajetPremium(){},definirEtapesNavigationDepuisRoute(){},formaterDuree:()=>'',demarrerGeolocalisation(){}};
 c.window=c;vm.createContext(c);
 vm.runInContext(s.slice(s.indexOf('var minuteurConfirmationItineraire ='),s.indexOf('window.demarrerNavigation =')),c);
 c.arreterNavigation=()=>{stops++;c.generationItineraire++;c.annulerChronoConfirmationItineraire();c.afficherModeGpsPleinEcran(false);c.navigationActive=false;c.routeNavigation=null;c.destinationNavigation=null};
 const start=s.indexOf('async function tracerItineraire('),end=s.indexOf('\n}',start)+2;
 vm.runInContext(s.slice(start,end),c);
 const pending=c.tracerItineraire(43.1,5.1,false,{id:'total'},2);
 assert(classes.has('gps-fullscreen'));assert.equal(els['route-start-countdown'].textContent,'20 s');
 now+=19000;interval();assert.equal(els['route-start-countdown'].textContent,'1 s');
 now+=1000;interval();assert(!classes.has('gps-fullscreen'));assert(!els['route-start-countdown']);
 resolve({routes:[{geometry:{coordinates:[]},distance:1000,duration:100}]});await pending;
 assert.equal(draws,0,'Late route cannot restore cancelled preview');assert.equal(c.routeNavigation,null);
 // Returning from background must enforce the wall-clock deadline too.
 c.commencerChronoConfirmationItineraire();now+=25000;c.actualiserChronoConfirmationItineraire();assert.equal(c.expirationConfirmationItineraire,0);
 // Confirmed start cancels the timeout; the existing guidance can then continue.
 c.commencerChronoConfirmationItineraire();c.annulerChronoConfirmationItineraire();const before=stops;now+=25000;c.actualiserChronoConfirmationItineraire();assert.equal(stops,before);
 // A successful preview exposes Start and retains the same deadline.
 c.demarrerNavigation=()=>{};
 const preview=c.tracerItineraire(43.1,5.1,false,{id:'total'},2);
 resolve({routes:[{geometry:{coordinates:[]},distance:1000,duration:100}]});await preview;
 assert.equal(button.textContent,'D\u00e9marrer');assert(c.expirationConfirmationItineraire>now);
 for(const id of ['navigation-panel','navigation-instruction','navigation-distance'])els[id]={};
 Object.assign(c,{derniereEconomieEstimee:2,relanceItineraireEnCours:false,
  enregistrerEconomiePremium(){},activerOrientationTelephone(){},stabiliserCapDepartNavigation(){},actualiserBoutonSuiviCarte(){},recentrerSurUtilisateur(){},actualiserGuidageNavigation(){},redessinerItineraireNavigationApresCamera(){}});
 vm.runInContext(s.slice(s.indexOf('window.demarrerNavigation ='),s.indexOf('window.arreterNavigation =')),c);
 const starting=c.demarrerNavigation();assert.equal(c.expirationConfirmationItineraire,0,'Start cancels countdown');
 c.arreterNavigation();resolve({routes:[{geometry:{coordinates:[]},distance:1000,duration:100}]});await starting;
 assert.equal(c.navigationActive,false);assert.equal(c.routeNavigation,null);assert.notEqual(button.textContent,'Arr\u00eater','Late start response cannot restore stop button');
 console.log(file+': countdown, background expiry, full-screen exit and late response cancellation passed');
}})().catch(e=>{console.error(e);process.exitCode=1});
