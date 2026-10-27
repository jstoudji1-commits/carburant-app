const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
for(const file of ['index.html','templates/index.html']){
 const source=fs.readFileSync(file,'utf8');let enabled=false;
 const badges=[{style:{display:''}},{style:{display:''}}];
 const c={localStorage:{getItem:key=>{assert.equal(key,'optiplein-carte-totalenergies');return String(enabled)}},carteTotalenergiesCle:undefined,document:{querySelectorAll:()=>badges},carburantEligibleAvantageTotalenergies: fuel=>fuel==='gazole'};
 vm.createContext(c);
 for(const [start,end] of [['function carteTotalenergiesActive()', 'function actualiserControleCarteTotalenergies()'],['function htmlAvantageCarburantTotal(', 'var logoStationPrixMinimum'],['function prixRentabiliteAvecCarteTotalenergies(', 'function formaterEurosRentabilite(']]) vm.runInContext(source.slice(source.indexOf(start),source.indexOf(end)),c);
 const advantage={prix_plafond:1.99};
 for(const publicPrice of [2.25,2.15,1.99,1.85]){
  let station={prix:publicPrice,avantageTotalenergies:advantage};
  for(const active of [true,false,true,false]){
   enabled=active;
   station=c.appliquerAvantageTotalenergiesStationsTrajet([station],active,'gazole')[0];
   assert.equal(station.prix,active?Math.min(publicPrice,1.99):publicPrice);
   assert.equal(station.prixPublic,publicPrice);
   c.actualiserPastillesTotalenergies();
   assert.equal(badges[0].style.display,active?'':'none');
   assert.equal(c.htmlAvantageCarburantTotal(advantage).includes('display:none'),!active);
  }
 }
 assert.equal(c.prixRentabiliteAvecCarteTotalenergies({prix:1.99,prix_public:2.15,avantageTotalenergies:advantage},false,'gazole'),2.15);
 assert.equal(c.prixRentabiliteAvecCarteTotalenergies({prix:2.15,avantageTotalenergies:advantage},true,'e85'),2.15);
 console.log(file+': plafond conditionnel, prix public restaure et pastilles actualisees');
}
