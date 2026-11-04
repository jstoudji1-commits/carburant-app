const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
(async()=>{for(const file of ['index.html','templates/index.html']){
 const s=fs.readFileSync(file,'utf8');let now=10000,resolve,requests=0;
 const c={Date:{now:()=>now},trajetPrepare:null,latitudeUtilisateur:43,longitudeUtilisateur:5,navigationActive:false,routeNavigation:null,
 carburantRentabiliteActuel:()=> 'gazole',carteTotalenergiesActive:()=>false,
 prixRentabiliteAvecCarteTotalenergies:x=>x.prix,stationElectrique:()=>false,modeElectriqueRentabiliteActif:()=>false,coutTempsRentabiliteEuroHeure:9,
 fetchAvecDelai:()=>{requests++;return new Promise(r=>resolve=r)},ajouterExplicationRentabilite(){}};
 vm.createContext(c);
 vm.runInContext(s.slice(s.indexOf('function calculerCoutOptimisationStation('),s.indexOf('function ajouterExplicationRentabilite(')),c);
 vm.runInContext(s.slice(s.indexOf('var stationRentableSuivie ='),s.indexOf('function actualiserRentabiliteDepuisGps()')),c);
 const station={id:'station',latitude:43,longitude:5,prix:2},reference={id:'reference',latitude:43.1,longitude:5,prix:2.2};
 const suivi={station,reference,carburant:'gazole',reservoir:50,consommation:6,quantite:40,distance:{},libelle:{},montant:{},ligne:{classList:{toggle(){}}},conteneur:{querySelector:()=>null}};
 c.stationRentableSuivie=suivi;
 const reply=(a,b)=>({ok:true,json:async()=>({trajets:[a,b].map(km=>({aller_km:km,suite_km:km,detour_km:km*2,duree_detour_minutes:km*3}))})});
 let p=c.actualiserStationRentableDepuisGps();resolve(reply(5,2));await p;
 assert.equal(suivi.distance.textContent,'5,0 km · ');assert(Math.abs(station.economieMonetaire-7.328)<1e-9);
 now+=3100;c.latitudeUtilisateur=43.01;p=c.actualiserStationRentableDepuisGps();resolve(reply(3,3));await p;
 assert.equal(suivi.distance.textContent,'3,0 km · ');assert(Math.abs(station.economieMonetaire-8.072)<1e-9);
 await c.actualiserStationRentableDepuisGps();assert.equal(requests,2,'Throttle GPS requests');
 now+=3100;p=c.actualiserStationRentableDepuisGps();const previous=suivi.distance.textContent;c.stationRentableSuivie={...suivi};resolve(reply(1,5));await p;assert.equal(suivi.distance.textContent,previous,'Ignore result for replaced recommendation');
 c.stationRentableSuivie=suivi;now+=3100;p=c.actualiserStationRentableDepuisGps();resolve({ok:false});await p;assert.equal(suivi.distance.textContent,previous,'Keep last verified value on network error');
 console.log(file+': GPS distance and net savings evolve without station ranking; stale replies rejected');
}})().catch(e=>{console.error(e);process.exitCode=1});
