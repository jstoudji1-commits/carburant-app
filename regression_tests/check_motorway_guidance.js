const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
for(const file of ['index.html','templates/index.html']){
 const s=fs.readFileSync(file,'utf8');
 function el(){return {children:[],style:{},appendChild(e){this.children.push(e)},setAttribute(k,v){this[k]=v},set innerHTML(v){this.children=[]}};}
 const icon=el();const c={document:{getElementById:()=>icon,createElement:el}};vm.createContext(c);
 vm.runInContext(s.slice(s.indexOf('function sortieManeuvre('),s.indexOf('function calculerTrajetRestant(')),c);
 for(const number of ['24','30.1','12A']){
  const step={maneuver:{type:'off ramp',modifier:'right'},exits:number,name:'D113'};
  assert.equal(c.typeIconeManeuvre(step),'exit');
  assert(c.texteManeuvre(step).includes('Prenez la sortie '+number));
  c.definirIconeGuidage(step);assert.equal(icon.children[0].children[1].textContent,number);
 }
 const fork={maneuver:{type:'fork',modifier:'left'},instruction:'Restez à gauche',name:'A7'};
 assert.equal(c.typeIconeManeuvre(fork),'left');assert(!c.texteManeuvre(fork).includes('rond-point'));
 const exit={maneuver:{type:'off ramp',modifier:'right'},instruction:'Prenez la sortie 12A vers Lyon'};
 assert.equal(c.sortieManeuvre(exit),'12A');assert(c.texteManeuvre(exit).includes('sortie 12A'));
 const unknown={maneuver:{type:'off ramp',modifier:'right'},name:'A7',instruction:'Prenez la sortie'};
 assert.equal(c.sortieManeuvre(unknown),'');c.definirIconeGuidage(unknown);assert.equal(icon.children[0].children[1].textContent,'↗');
 const roundabout={maneuver:{type:'roundabout',exit:2},exits:'24'};
 assert.equal(c.typeIconeManeuvre(roundabout),'roundabout');assert(c.texteManeuvre(roundabout).includes('2e sortie'));
 c.definirIconeGuidage(roundabout);assert.equal(icon.children[0].children[0].textContent,'2');
 assert.notEqual(c.typeIconeManeuvre({maneuver:{type:'turn',modifier:'right'},name:'Rue du Rond-Point'}),'roundabout');
 console.log(file+': sorties autoroutieres, numeros et vrais ronds-points valides');
}
