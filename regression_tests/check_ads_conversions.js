const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('static/google-ads.js','utf8');
const ids=['a'.repeat(32),'b'.repeat(32)];
function page(choice, storage=new Map(), native=false){
 const scripts=[],body=[],buttons=['denied','granted'].map(choice=>({dataset:{choice}}));let calls=0;
 const doc={cookie:choice?'optiplein_ads_consent='+choice:'',referrer:'https://www.optiplein.fr/api/compte/validation-email?token=secret',
  createElement:tag=>({tag,setAttribute(){},querySelectorAll:()=>buttons}),head:{appendChild:x=>scripts.push(x)},body:{appendChild:x=>body.push(x)}};
 const c={document:doc,location:{href:'https://www.optiplein.fr/web?email_verifie=1&token=secret&gclid=click',protocol:'https:',reload(){c.reloaded=true}},URL,Set,Date,
  localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
  fetch:async()=>{calls++;return {ok:true,json:async()=>({conversions:ids.map((id,i)=>({id,kind:i?'testeur':'compte'}))})}}};
 c.window=c;if(native)c.Capacitor={isNativePlatform:()=>true};vm.createContext(c);vm.runInContext(source,c);
 return {c,scripts,body,buttons,storage,calls:()=>calls,events:()=>c.dataLayer.filter(x=>x[0]==='event')};
}
(async()=>{
 for(const choice of ['', 'denied']){const p=page(choice);assert.equal(p.scripts.length,0);assert.equal(p.calls(),0);assert.equal(p.events().length,0);}
 const p=page('');p.buttons[1].onclick();assert.equal(p.scripts.length,1);assert.match(p.scripts[0].src,/AW-18540838649/);
 await p.scripts[0].onload();assert.equal(p.events().length,2);
 for(const e of p.events()){assert.equal(e[2].send_to,'AW-18540838649/bgDvCM746KsdEPn9-ohF');e[2].event_callback();}
 const config=p.c.dataLayer.find(x=>x[0]==='config')[2];assert(!config.page_location.includes('secret'));assert(!config.page_referrer.includes('secret'));assert(config.page_location.includes('gclid=click'));
 const reload=page('granted',p.storage);await reload.scripts[0].onload();assert.equal(reload.events().length,0);
 p.buttons[0].onclick();assert.equal(p.c.reloaded,true);
 const native=page('granted',new Map(),true);assert.equal(native.scripts.length,0);assert.equal(native.body.length,0);
 console.log('Google Ads: consentement, deux conversions, doublons, retrait, URLs sensibles et exclusion native valides');
})().catch(e=>{console.error(e);process.exitCode=1});
