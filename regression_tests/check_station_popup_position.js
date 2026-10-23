const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
for(const file of ['index.html','templates/index.html']) {
 const s=fs.readFileSync(file,'utf8');
 const start=s.indexOf('function positionnerPopupStation(');
 const end=s.indexOf('window.fermerPopupStation',start);
 const styles={}; let callback, removed=false, disconnected=false;
 let bounds={top:100,height:600}; let tools={bottom:155,height:43};
 const element={querySelector:()=>({}),classList:{add:c=>assert.equal(c,'station-popup-centree')},style:{setProperty:(k,v)=>styles[k]=v}};
 const context={document:{querySelector:()=>({getBoundingClientRect:()=>tools})},window:{addEventListener:(n,fn)=>{callback=fn},removeEventListener:(n,fn)=>{removed=fn===callback}}, ResizeObserver: class {observe(){} disconnect(){disconnected=true}}};
 vm.createContext(context);vm.runInContext(s.slice(start,end),context);
 const cleanup=context.positionnerPopupStation({getElement:()=>element},{getBoundingClientRect:()=>bounds});
 assert.equal(styles['--station-popup-top'],'65px');
 assert.equal(styles['--station-popup-height'],'465px');
 bounds={top:100,height:300};tools={bottom:190,height:78};callback();
 assert.equal(styles['--station-popup-top'],'100px');
 assert.equal(styles['--station-popup-height'],'130px');
 cleanup();assert(removed&&disconnected);
 let frame, movement;
 context.requestAnimationFrame=fn=>{frame=fn;return 1};
 context.cancelAnimationFrame=()=>{};
 context.appliquerMouvementCarteAutomatique=fn=>fn();
 element.getBoundingClientRect=()=>({bottom:330});
 const cameraCleanup=context.positionnerPopupStation(
     {getElement:()=>element},{getBoundingClientRect:()=>bounds},
     {easeTo:options=>{movement=options}},[2,48]
 );
 frame();
 assert.deepEqual(Array.from(movement.center),[2,48]);
 assert.equal(movement.offset[0],0);
 assert.equal(movement.offset[1],108);
 assert.equal(movement.zoom,undefined);
 assert.equal(movement.bearing,undefined);
 assert.equal(movement.pitch,undefined);
 cameraCleanup();
 const before=JSON.stringify(styles);element.querySelector=()=>null;
 context.positionnerPopupStation({getElement:()=>element},{});
 assert.equal(JSON.stringify(styles),before);
 console.log(file+': position sous les boutons, redimensionnement et nettoyage valides');
}
