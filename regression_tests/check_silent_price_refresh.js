const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
(async()=>{for(const file of ['index.html','templates/index.html']){
 const s=fs.readFileSync(file,'utf8');let timers=0,ok=false;
 const c={window:{location:{replace(){throw Error('Page reload forbidden')}}},console,
 fetchAvecDelai:async()=>({ok:true,json:async()=>({update_pending:true,updated_at:'new',data_version:'new'})}),
 programmerSynchronisationPrix(){timers++},appliquerDateMiseAJourServeur:()=> 'new',actualiserCompteurMiseAJour(){},
 actualiserStationsSelonPosition:async()=>ok,versionDonneesChargees:'old',dateDonneesChargees:'old',navigationActive:false,trajetPrepare:null,
 calculRentabiliteBloquePrixAnciens:false,afficherInfoItineraire(){throw Error('Visible price refresh message forbidden')}};
 vm.createContext(c);vm.runInContext(s.slice(s.indexOf('function rechargerAvecPositionActuelle()'),s.indexOf('async function forcerRafraichissementStationsVisibles()')),c);
 await c.synchroniserDateMiseAJour();assert.equal(c.versionDonneesChargees,'old');assert(timers>0);
 ok=true;await c.synchroniserDateMiseAJour();assert.equal(c.versionDonneesChargees,'new');
 console.log(file+': background price refresh, retry and no page reload passed');
}})().catch(e=>{console.error(e);process.exitCode=1});
