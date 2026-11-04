const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
(async()=>{for(const file of ['index.html','templates/index.html']){
 const s=fs.readFileSync(file,'utf8');let fuel='gazole',resolve,published=[];
 const c={URLSearchParams,carburantSelectionne:'gazole',carburantRentabiliteActuel:()=>fuel,rayonCalculEconomieKm:25,actualisationStationsEconomieEnCours:null,
 fetchAvecDelai:()=>new Promise(r=>resolve=r),definirStationsEconomie:stations=>published.push(stations),remplacerStationsSurCarte:stations=>published.push(stations)};
 vm.createContext(c);vm.runInContext(s.slice(s.indexOf('async function actualiserStationsEconomieVehicule('),s.indexOf('async function actualiserStationsSelonPosition(')),c);
 const first=c.actualiserStationsEconomieVehicule(43,5,null);fuel='e10';
 resolve({ok:true,json:async()=>({stations:[{id:'old',prix:2.117,carburant:'gazole'}]})});
 assert.equal(await first,false);assert.equal(published.length,0,'Late response for old fuel cannot publish');
 const second=c.actualiserStationsEconomieVehicule(43,5,null);
 resolve({ok:true,json:async()=>({stations:[{id:'wrong',prix:2.117,carburant:'gazole'},{id:'correct',prix:1.978,carburant:'e10'}]})});
 assert.equal(await second,true);assert.equal(published.length,2);
 assert.equal(published[0].length,1);assert.equal(published[0][0].id,'correct');
 assert.equal(JSON.stringify(published[0]),JSON.stringify(published[1]),'Map and recommendation share one response');
 console.log(file+': stale fuel response rejected; map and calculation share prices');
}})().catch(e=>{console.error(e);process.exitCode=1});
