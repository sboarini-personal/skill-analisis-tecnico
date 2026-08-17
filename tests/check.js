const fs=require('fs');
require('./domshim.js');
const f=process.argv[2];
const html=fs.readFileSync(f,'utf8');
const js=html.match(/<script>\n([\s\S]*)<\/script>/)[1];
document.querySelector('#c-risk').value='1'; document.querySelector('#sim-range').value='500';
try{ new Function(js)(); }catch(e){ console.log('❌ ERROR JS en '+f+': '+e.message); process.exit(1); }
const bad=globalThis.__BAD;
const L=s=>{const e=document.querySelector(s); if(!e) return -1;
  return (e.innerHTML||'').length + (e.children?e.children.length:0);};
console.log('✅ '+f.split('/').pop()+
  ' | calc:'+L('#calc-out')+
  ' rr:'+L('#rr-table')+
  ' sim:"'+document.querySelector('#sim-px').textContent+'"'+
  ' pat:'+L('#pat-list')+
  ' vpchart:'+L('#vpchart')+
  ' vpread:'+L('#vp-read')+
  ' kchart:'+L('#kchart')+
  ' kread:'+L('#k-read')+
  ' ktools:'+L('#k-tools')+
  ' | anomalias:'+bad.length);
bad.slice(0,8).forEach(b=>console.log('    ⚠ '+b));
