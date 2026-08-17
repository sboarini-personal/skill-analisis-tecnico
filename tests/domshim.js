class El {
  constructor(tag){ this.tagName=tag; this.children=[]; this.attrs={}; this._cls='';
    this.style=new Proxy({},{set:(t,k,v)=>{t[k]=v;return true;},get:(t,k)=>t[k]||''});
    this.classList={add:()=>{},remove:()=>{},toggle:()=>{},contains:()=>false};
    this._html=''; this.textContent=''; this.value=''; this.offsetWidth=100; this.offsetHeight=40;
    this.parentElement=null; }
  set className(v){this._cls=v} get className(){return this._cls}
  set innerHTML(v){ this._html=String(v); if(/undefined|NaN|\[object/.test(this._html)) globalThis.__BAD.push(this._cls+' :: '+this._html.slice(0,140)); }
  get innerHTML(){return this._html}
  setAttribute(k,v){ if(v===undefined||v===null||(typeof v==='number'&&isNaN(v))||String(v).includes('NaN')) globalThis.__BAD.push('attr '+k+'='+v+' on <'+this.tagName+'>'); this.attrs[k]=v }
  getAttribute(k){return this.attrs[k]}
  appendChild(c){ c.parentElement=this; this.children.push(c); return c }
  addEventListener(t,fn){ (this._ev||(this._ev={}))[t]=(this._ev[t]||[]).concat(fn) }
  fire(t,ev){ ((this._ev||{})[t]||[]).forEach(fn=>fn(ev||{clientX:10,clientY:10})) }
  querySelector(){return new El('div')}
}
const REG={};
globalThis.__BAD=[];
globalThis.document={createElement:t=>new El(t),createElementNS:(ns,t)=>new El(t),
  querySelector:s=>{ if(!REG[s]){ const e=new El('div'); e.parentElement=new El('div'); REG[s]=e; } return REG[s]; }, body:new El('body')};
globalThis.window=globalThis; globalThis.innerWidth=1200; globalThis.innerHeight=900; globalThis.__REG=REG;
