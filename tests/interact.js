const fs=require('fs');
require('./domshim.js');
const f=process.argv[2];
const js=fs.readFileSync(f,'utf8').match(/<script>\n([\s\S]*)<\/script>/)[1];
document.querySelector('#c-risk').value='1'; document.querySelector('#sim-range').value='500';
try{ new Function(js)(); }catch(e){ console.log('❌ carga: '+e.message); process.exit(1); }

function clicks(sel,label){
  const tools=document.querySelector(sel);
  if(!tools||!tools.children.length){ console.log('   (sin toggles en '+sel+')'); return; }
  const btns=tools.children;
  // apagar de a uno hasta dejar todo apagado, despues volver a prender
  for(const pass of ['off','on']){
    for(let i=0;i<btns.length;i++){
      try{ btns[i].onclick && btns[i].onclick(); }
      catch(e){ console.log(`❌ ${label} boton ${i} (${pass}): ${e.message}`); process.exit(1); }
    }
  }
  console.log(`   ${label}: ${btns.length} toggles x2 pasadas OK`);
}
clicks('#g-tools','grafico de precio');
clicks('#k-tools','koncorde');

// el simulador con valores extremos
const rng=document.querySelector('#sim-range');
[0,1,250,999,1000].forEach(v=>{
  rng.value=String(v);
  try{ rng.fire('input'); }catch(e){ console.log('❌ simulador en '+v+': '+e.message); process.exit(1); }
});
console.log('   simulador: 5 posiciones OK -> '+document.querySelector('#sim-px').textContent);
// tooltips: disparar hover sobre cada elemento con listener registrado
let hov=0;
for(const key in globalThis.__REG){}
(function walk(n){ if(!n||typeof n!=='object')return;
  if(n._ev&&n._ev.mouseenter){ n.fire('mouseenter'); n.fire('mousemove'); n.fire('mouseleave'); hov++; }
  (n.children||[]).forEach(walk); })({children:Object.values(globalThis.__REG)});
console.log('   tooltips: '+hov+' disparados');
console.log('✅ '+f.split('/').pop()+' | anomalias:'+globalThis.__BAD.length);
globalThis.__BAD.slice(0,8).forEach(b=>console.log('    ⚠ '+b));
