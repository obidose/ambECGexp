'use strict';
const els = {
  file:document.getElementById('file'), leads:document.getElementById('leads'), fs:document.getElementById('fs'), uv:document.getElementById('uv'),
  win:document.getElementById('win'), vfill:document.getElementById('vfill'), vfillVal:document.getElementById('vfillVal'), autoGain:document.getElementById('autoGain'), gainMode:document.getElementById('gainMode'),
  showHR:document.getElementById('showHR'), hrLock:document.getElementById('hrLock'), hrSmooth:document.getElementById('hrSmooth'), robustHR:document.getElementById('robustHR'), hrTol:document.getElementById('hrTol'),
  baseline:document.getElementById('baseline'), toolPan:document.getElementById('toolPan'), toolTime:document.getElementById('toolTime'), toolVolt:document.getElementById('toolVolt'),
  showScale:document.getElementById('showScale'), showL0:document.getElementById('showL0'), showL1:document.getElementById('showL1'), showL2:document.getElementById('showL2'),
  theme:document.getElementById('theme'), sample:document.getElementById('sample'), reset:document.getElementById('reset'), printBtn:document.getElementById('print'),
  canvas:document.getElementById('ecg'), overview:document.getElementById('overview'), status:document.getElementById('status'), scroll:document.getElementById('scroll')
};
const state = {
  fs:200, uvPerLSB:2, leadCount:3, winSecs:10, vfill:0.65,
  autoGain:true, gainMode:'global',
  showHR:true, hrLockScale:true, hrSmooth:5, robustHR:true, hrTol:30,
  baselineMode:'hp', showScaleBar:true, showLeads:[true,true,true],
  raw:null, csv:null, totalSamples:0, viewStart:0,
  dpr:window.devicePixelRatio||1, width:0, height:0,
  tool:'pan', caliper:{a:null,b:null,active:false}, caliperV:{lead:0,yA:null,yB:null,active:false},
  overview:{pts:[],building:false,progress:0,ovStartSec:0,ovSpanSec:0,range:null}
};
function setStatus(msg,err){ els.status.textContent=msg; els.status.className='status'+(err?' err':''); }
window.onerror=(m,src,l,c)=>setStatus('JS error: '+m+' @'+l+':'+c,true);
window.addEventListener('unhandledrejection',e=>setStatus('Promise error: '+(e?.reason?.message||e?.reason||''),true));

const clamp=(v,min,max)=>Math.max(min,Math.min(max,v));
function hasData(){ return (state.raw||state.csv) && state.totalSamples>0; }
function maxViewStart(){ return Math.max(0,state.totalSamples - Math.max(1,Math.round(state.winSecs*state.fs))); }
function syncScroll(){ const maxS=maxViewStart(); els.scroll.max=String(maxS); els.scroll.step=String(Math.max(1,Math.round(state.fs*0.05))); els.scroll.value=String(Math.max(0,Math.min(state.viewStart,maxS))); }
function updateWinInput(){ els.win.value=(Math.round(state.winSecs*100)/100).toString(); }
function xToTime(x){ const t0=state.viewStart/state.fs; return t0 + (x/Math.max(1,state.width))*state.winSecs; }
function percentile(arr,p){ const tmp=Array.from(arr); if(!tmp.length) return 0; tmp.sort((a,b)=>a-b); const idx=Math.max(0,Math.min(tmp.length-1,Math.floor(p*(tmp.length-1)))); return tmp[idx]; }
function highpassIIR(arr, dt, fc){ const tau=1/(2*Math.PI*fc); const alpha=tau/(tau+dt); const out=new Float32Array(arr.length); let y=0,prev=arr[0]||0; for(let i=0;i<arr.length;i++){ const x=arr[i]; y=alpha*(y + x - prev); out[i]=y; prev=x; } return out; }

function sampleMV(leadIndex, s){
  if(state.csv){ const a=state.csv[leadIndex]||[]; const S=a.length; const ss=Math.max(0,Math.min(S-1,s|0)); return a[ss]; }
  if(!state.raw) return 0; const total=state.totalSamples|0; const ss=Math.max(0,Math.min(total-1,s|0)); const idx=ss*state.leadCount+leadIndex; if(idx<0||idx>=state.raw.length) return 0; return state.raw[idx]*(state.uvPerLSB/1000);
}
function windowSeries(leadIndex){
  const fs=state.fs,W=state.width; const start=Math.max(0,state.viewStart|0); const nSamp=Math.max(1,Math.round(state.winSecs*fs)); const seg=new Float32Array(W); const denom=Math.max(1,W); const spp=nSamp/denom;
  for(let x=0;x<W;x++){
    if(spp>2){ const s0=start+Math.floor(x*nSamp/denom), s1=start+Math.floor((x+1)*nSamp/denom)-1; const span=Math.max(0,s1-s0);
      let acc=0; acc+=sampleMV(leadIndex, s0+Math.floor(0.2*span)); acc+=sampleMV(leadIndex, s0+Math.floor(0.5*span)); acc+=sampleMV(leadIndex, s0+Math.floor(0.8*span)); seg[x]=acc/3;
    } else { const s=start+Math.floor((x+0.5)*nSamp/denom); seg[x]=sampleMV(leadIndex,s); }
  }
  const dtpx=state.winSecs/Math.max(1,W);
  if(state.baselineMode==='hp') return highpassIIR(seg, dtpx, 0.5);
  const tmp=Array.from(seg).sort((a,b)=>a-b); const med=tmp.length%2? tmp[(tmp.length-1)>>1] : 0.5*(tmp[tmp.length/2-1]+tmp[tmp.length/2]); for(let i=0;i<seg.length;i++) seg[i]-=med; return seg;
}
function windowRawSegMulti(leads){
  const fs=state.fs|0; const start=Math.max(0,state.viewStart|0); const nSamp=Math.max(1,Math.round(state.winSecs*fs)); const a=new Float32Array(nSamp); const L=leads.length;
  for(let i=0;i<nSamp;i++){ if(L===1){ a[i]=sampleMV(leads[0],start+i); } else { const vals=new Array(L); for(let j=0;j<L;j++) vals[j]=sampleMV(leads[j],start+i); vals.sort((x,y)=>x-y); const mid=L>>1; a[i]=(L%2? vals[mid] : 0.5*(vals[mid-1]+vals[mid])); } }
  if(state.baselineMode==='hp') return highpassIIR(a, 1/Math.max(1,fs), 0.5);
  const tmp=Array.from(a).sort((u,v)=>u-v); const med=tmp.length%2? tmp[(tmp.length-1)>>1] : 0.5*(tmp[tmp.length/2-1]+tmp[tmp.length/2]); for(let i=0;i<a.length;i++) a[i]-=med; return a;
}
function detectHR(seg, dtpx, smoothBeats, robust=true, tolPct=30){
  const n=seg.length; if(n<5) return {pts:[],avg:NaN,totalRaw:0,keptRaw:0,keepRatio:0};
  let maxV=-1e9,minV=1e9; for(let i=0;i<n;i++){ const v=seg[i]; if(v>maxV) maxV=v; if(v<minV) minV=v; }
  const flip=(-minV)>maxV; const sq=new Float32Array(n);
  for(let i=1;i<n;i++){ const a=flip?-seg[i]:seg[i]; const b=flip?-seg[i-1]:seg[i-1]; const dv=a-b; sq[i]=dv*dv; }
  const integ=new Float32Array(n); let acc=0; const winI=Math.max(3,Math.round(0.12/dtpx));
  for(let i=0;i<n;i++){ acc+=sq[i]; if(i>=winI) acc-=sq[i-winI]; integ[i]=acc/Math.min(winI,i+1); }
  const thr=Math.max(1e-7,0.35*percentile(integ,0.98)); const refrPx=Math.max(1,Math.round(0.28/dtpx)); const searchPx=Math.max(1,Math.round(0.05/dtpx));
  const peaks=[]; let last=-1e9; for(let i=1;i<n-1;i++) if(integ[i]>=thr && integ[i]>=integ[i-1] && integ[i]>=integ[i+1] && (i-last)>=refrPx){ let j=i,best=-1e9; const j0=Math.max(0,i-searchPx), j1=Math.min(n-1,i+searchPx); for(let k=j0;k<=j1;k++){ const val=flip?-seg[k]:seg[k]; if(val>best){ best=val; j=k; } } peaks.push(j*dtpx); last=j; i+=Math.floor(refrPx*0.3); }
  const bpmRaw=[]; for(let k=1;k<peaks.length;k++){ const rr=peaks[k]-peaks[k-1]; if(rr>0.25 && rr<2.5) bpmRaw.push({t:peaks[k], bpm:60/rr}); }
  let arr=bpmRaw; if(robust && arr.length){ const w=Math.max(3,(smoothBeats|0)*2-1); const keep=[]; for(let i=0;i<arr.length;i++){ const lo=Math.max(0,i-w), hi=Math.min(arr.length-1,i+w); const sub=arr.slice(lo,hi+1).map(p=>p.bpm).sort((a,b)=>a-b); const med=sub.length%2? sub[(sub.length-1)>>1] : 0.5*(sub[sub.length/2-1]+sub[sub.length/2]); if(!isFinite(med)||med<=0){ keep.push(arr[i]); continue; } const dev=Math.abs(arr[i].bpm-med)/med*100; if(dev<=tolPct) keep.push(arr[i]); } arr=keep; }
  const m=Math.max(1,smoothBeats|0); if(arr.length<m){ const avgSmall=arr.length?arr.reduce((a,p)=>a+p.bpm,0)/arr.length:NaN; return {pts:arr,avg:avgSmall,totalRaw:bpmRaw.length,keptRaw:arr.length,keepRatio:(bpmRaw.length?arr.length/bpmRaw.length:0)}; }
  const pts=[]; for(let i=m-1;i<arr.length;i++){ let s=0; for(let j=i-m+1;j<=i;j++) s+=arr[j].bpm; pts.push({t:arr[i].t,bpm:s/m}); }
  const avg=pts.length?pts.reduce((a,p)=>a+p.bpm,0)/pts.length:NaN; return {pts,avg,totalRaw:bpmRaw.length,keptRaw:arr.length,keepRatio:(bpmRaw.length?arr.length/bpmRaw.length:0)};
}
function getVisibleLeads(){ const v=[]; for(let i=0;i<Math.min(3,state.leadCount);i++){ if(state.showLeads[i]) v.push(i); } if(!v.length) v.push(0); return v; }
function getOverviewRange(){ const pts=state.overview.pts||[]; let minB=Infinity,maxB=-Infinity; for(const p of pts){ if(!isFinite(p?.bpm)) continue; if(p.bpm<minB) minB=p.bpm; if(p.bpm>maxB) maxB=p.bpm; } if(!isFinite(minB)||!isFinite(maxB)){ minB=60; maxB=180; } const pad=10; minB=Math.max(30,Math.floor((minB-pad)/10)*10); maxB=Math.min(230,Math.ceil((maxB+pad)/10)*10); if(maxB-minB<40){ const mid=(maxB+minB)/2; minB=Math.max(30,mid-30); maxB=Math.min(230,mid+30); } return {minB,maxB}; }
function getHRScale(windowRes){ if(state.hrLockScale && state.overview && state.overview.range) return state.overview.range; let minB=60,maxB=180; if(windowRes&&windowRes.pts&&windowRes.pts.length){ minB=Math.min(...windowRes.pts.map(p=>p.bpm)); maxB=Math.max(...windowRes.pts.map(p=>p.bpm)); const pad=10; minB=Math.max(30,Math.floor((minB-pad)/10)*10); maxB=Math.min(230,Math.ceil((maxB+pad)/10)*10); if(maxB-minB<40){ const mid=(maxB+minB)/2; minB=Math.max(30,mid-30); maxB=Math.min(230,mid+30); } } return {minB,maxB}; }

function drawPaperGrid(ctx,y0,h,laneH,pxPerSec){
  const t0=state.viewStart/state.fs; const t1=t0+state.winSecs; const smallT=0.04;
  const cs=getComputedStyle(document.body);
  for(let t=Math.floor(t0/smallT)*smallT;t<=t1+1e-9;t+=smallT){ const x=(t-t0)*pxPerSec; const big=(Math.round(t/smallT)%5===0); ctx.strokeStyle=big?cs.getPropertyValue('--grid-strong'):'#999'; ctx.lineWidth=big?1:0.5; ctx.beginPath(); ctx.moveTo(x,y0); ctx.lineTo(x,y0+h); ctx.stroke(); }
  const gridPxPerMV=(laneH*state.vfill)/6; const step=gridPxPerMV*0.1;
  for(let y=y0,k=0;y<=y0+h+1;y+=step,k++){ const big=(k%5===0); ctx.strokeStyle=big?cs.getPropertyValue('--grid-strong'):'#999'; ctx.lineWidth=big?1:0.5; ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(state.width,y); ctx.stroke(); }
}

function draw(){
  const ctx=els.canvas.getContext('2d'); const dpr=state.dpr; ctx.setTransform(dpr,0,0,dpr,0,0);
  const W=els.canvas.clientWidth||800, H=els.canvas.clientHeight||400; state.width=W; state.height=H;
  const cs=getComputedStyle(document.body);
  ctx.clearRect(0,0,W,H); ctx.fillStyle=cs.getPropertyValue('--bg')||'#0b1021'; ctx.fillRect(0,0,W,H);
  if(!hasData()){ ctx.fillStyle='#94a3b8'; ctx.fillText('Open sample or load an ECG…',12,18); return; }
  const hrPane=state.showHR?Math.round(H*0.18):0; const mainH=H-hrPane; const vis=getVisibleLeads(); const shown=vis.length; const laneH=mainH/Math.max(1,shown); const pxPerSec=W/Math.max(0.2,state.winSecs);
  drawPaperGrid(ctx,0,mainH,laneH,pxPerSec);
  const segs=[],amps=[];
  for(let k=0;k<shown;k++){ const li=vis[k]; const seg=windowSeries(li); segs.push(seg); const abs=seg.map(Math.abs).sort((a,b)=>a-b); const p95=abs[Math.max(0,Math.floor(0.95*(abs.length-1)))]; amps.push(p95||0.5); }
  const gains=new Array(shown);
  if(state.autoGain){ if(state.gainMode==='global'){ const a=Math.max(...amps); const target=Math.max(0.2,a*1.2); const g=(laneH*state.vfill)/(2*target); for(let i=0;i<shown;i++) gains[i]=g; } else { for(let i=0;i<shown;i++){ const target=Math.max(0.2,amps[i]*1.2); gains[i]=(laneH*state.vfill)/(2*target); } } } else { const g=(laneH*state.vfill)/6; for(let i=0;i<shown;i++) gains[i]=g; }
  const comp=clamp((pxPerSec/120),0.3,1); const gainsPlot=gains.map(g=>g*comp);
  ctx.strokeStyle=cs.getPropertyValue('--trace')||'#a5b4fc'; ctx.lineWidth=1.2;
  const leadNames=['V1','V3','V5'];
  for(let k=0;k<shown;k++){ const baseY=(k+0.5)*laneH; const seg=segs[k]; const gain=gainsPlot[k]; ctx.beginPath(); for(let x=0;x<W;x++){ const y=baseY - seg[x]*gain; if(x===0) ctx.moveTo(0,y); else ctx.lineTo(x,y); } ctx.stroke();
    const gridGain=(laneH*state.vfill)/6; const x0=20,x1=x0+0.2*pxPerSec; const y0=baseY,y1=y0-1.0*gridGain; ctx.strokeStyle=cs.getPropertyValue('--ink')||'#e5e7eb'; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x0,y1); ctx.lineTo(x1,y1); ctx.lineTo(x1,y0); ctx.stroke(); ctx.fillStyle=cs.getPropertyValue('--muted')||'#94a3b8'; ctx.font='12px system-ui,sans-serif'; ctx.fillText(leadNames[vis[k]]||('Lead '+(vis[k]+1)), 10, baseY - laneH*0.35); }
  if(state.showScaleBar){ const barLen=pxPerSec; const barX=Math.max(8,W-barLen-12); const barY=Math.max(20,mainH-16); ctx.strokeStyle=cs.getPropertyValue('--ink')||'#e5e7eb'; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(barX,barY); ctx.lineTo(barX+barLen,barY); ctx.stroke(); for(let k=0;k<=5;k++){ const x=barX+k*(barLen/5), len=(k%5===0)?10:6; ctx.beginPath(); ctx.moveTo(x,barY); ctx.lineTo(x,barY+len); ctx.stroke(); } ctx.fillStyle=cs.getPropertyValue('--muted')||'#94a3b8'; ctx.fillText('1 s', barX+barLen/2-10, barY-4); }
  if(state.caliper && state.caliper.a!=null && state.caliper.b!=null){ const t0=state.viewStart/state.fs; const a=Math.min(state.caliper.a,state.caliper.b), b=Math.max(state.caliper.a,state.caliper.b); const xA=(a-t0)*pxPerSec, xB=(b-t0)*pxPerSec; const dt=b-a; const bpm=dt>0?60/dt:NaN; ctx.strokeStyle='#22d3ee'; ctx.setLineDash([4,3]); ctx.beginPath(); ctx.moveTo(xA,0); ctx.lineTo(xA,mainH); ctx.stroke(); ctx.beginPath(); ctx.moveTo(xB,0); ctx.lineTo(xB,mainH); ctx.stroke(); ctx.setLineDash([]); const text=`Δt ${(dt*1000).toFixed(0)} ms • ≈${isFinite(bpm)?bpm.toFixed(1):'—'} bpm`; ctx.font='12px system-ui,sans-serif'; const pad=6; const tw=ctx.measureText(text).width+pad*2; const bx=Math.min(W-tw-8, Math.max(8,(xA+xB)/2 - tw/2)); const by=8; ctx.fillStyle=cs.getPropertyValue('--overlay-fill'); ctx.strokeStyle=cs.getPropertyValue('--overlay-stroke'); ctx.lineWidth=1; ctx.fillRect(bx,by,tw,18); ctx.strokeRect(bx,by,tw,18); ctx.fillStyle=cs.getPropertyValue('--overlay-text'); ctx.fillText(text, bx+pad, by+13); }
  if(state.caliperV && state.caliperV.yA!=null && state.caliperV.yB!=null){ const li=Math.max(0, Math.min(shown-1, state.caliperV.lead|0)); const baseY=(li+0.5)*laneH; const gain=gainsPlot[li]||1; const yA=state.caliperV.yA,yB=state.caliperV.yB; const dv=(yA-yB)/gain; const vtxt=`ΔV ${dv.toFixed(2)} mV (${leadNames[vis[li]]||('Lead '+(vis[li]+1))})`; const pad=6; const vw=ctx.measureText(vtxt).width+pad*2; const vx=12; const vy=Math.max(16, baseY - laneH*0.35); ctx.strokeStyle='#22d3ee'; ctx.setLineDash([4,3]); ctx.beginPath(); ctx.moveTo(0,yA); ctx.lineTo(W,yA); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0,yB); ctx.lineTo(W,yB); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle=cs.getPropertyValue('--overlay-fill'); ctx.strokeStyle=cs.getPropertyValue('--overlay-stroke'); ctx.lineWidth=1; ctx.fillRect(vx,vy,vw,18); ctx.strokeRect(vx,vy,vw,18); ctx.fillStyle=cs.getPropertyValue('--overlay-text'); ctx.fillText(vtxt, vx+pad, vy+13); }
  const hrPane2 = state.showHR?Math.round(H*0.18):0; if(hrPane2>0){ const paneY=mainH; const h=hrPane2; const leads=getVisibleLeads(); const segHR=windowRawSegMulti(leads); const dt=1/Math.max(1,state.fs); const res=detectHR(segHR, dt, state.hrSmooth, state.robustHR, state.hrTol); let {minB,maxB}=getHRScale(res); ctx.fillStyle=cs.getPropertyValue('--bg'); ctx.fillRect(0,paneY,W,h); for(let b=Math.ceil(minB/20)*20; b<=maxB; b+=20){ const y=paneY+h - (b-minB)/(maxB-minB)*h; ctx.strokeStyle=cs.getPropertyValue('--grid-weak'); ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); ctx.fillStyle=cs.getPropertyValue('--muted'); ctx.font='11px system-ui,sans-serif'; ctx.fillText(String(b)+' bpm', 6, y-2); } if(res.pts.length){ const firstY=paneY+h - (res.pts[0].bpm-minB)/(maxB-minB)*h; const lastY=paneY+h - (res.pts[res.pts.length-1].bpm-minB)/(maxB-minB)*h; ctx.strokeStyle=cs.getPropertyValue('--hr')||'#34d399'; ctx.lineWidth=1.8; ctx.beginPath(); ctx.moveTo(0,firstY); for(let i=0;i<res.pts.length;i++){ const x=(res.pts[i].t/state.winSecs)*W; const y=paneY+h - (res.pts[i].bpm-minB)/(maxB-minB)*h; ctx.lineTo(x,y); } ctx.lineTo(W,lastY); ctx.stroke(); const avg=res.avg; ctx.fillStyle=cs.getPropertyValue('--muted'); ctx.font='12px system-ui,sans-serif'; ctx.fillText('HR '+(isFinite(avg)?avg.toFixed(0)+' bpm':'—'), W-90, paneY+14); } }
}
function drawOverview(){ const ctx=els.overview.getContext('2d'); const dpr=state.dpr; ctx.setTransform(dpr,0,0,dpr,0,0); const W=els.overview.clientWidth||600,H=els.overview.clientHeight||80; const cs=getComputedStyle(document.body); ctx.clearRect(0,0,W,H); ctx.fillStyle=cs.getPropertyValue('--bg'); ctx.fillRect(0,0,W,H); if(!hasData()){ ctx.fillStyle=cs.getPropertyValue('--muted'); ctx.fillText('Load a file to build HR overview…',12,16); return; } const totalSec=state.totalSamples/state.fs; const T0=Math.max(0,state.overview.ovStartSec||0); const Tspan=Math.max(1e-6,state.overview.ovSpanSec||totalSec); const Tend=Math.min(totalSec,T0+Tspan); const pts=state.overview.pts||[]; if(!pts.length){ ctx.fillStyle=cs.getPropertyValue('--muted'); const msg=state.overview.building?('Building HR overview… '+Math.round((state.overview.progress||0)*100)+'%'):'HR overview not built'; ctx.fillText(msg,12,16); } else { const range=state.overview.range||getOverviewRange(); const minB=range.minB,maxB=range.maxB; for(let b=Math.ceil(minB/20)*20; b<=maxB; b+=20){ const y=H - (b-minB)/(maxB-minB)*H; ctx.strokeStyle=cs.getPropertyValue('--grid-weak'); ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); ctx.fillStyle=cs.getPropertyValue('--muted'); ctx.font='10px system-ui,sans-serif'; ctx.fillText(b+' bpm',4,y-2); } ctx.strokeStyle=cs.getPropertyValue('--hr-ov')||'#93c5fd'; ctx.lineWidth=1.5; ctx.beginPath(); let moved=false; for(const p of pts){ const t=p.t; if(t<T0||t>Tend||!isFinite(p?.bpm)) continue; const x=((t-T0)/Tspan)*W; const y=H - (p.bpm-minB)/(maxB-minB)*H; if(!moved){ ctx.moveTo(x,y); moved=true; } else ctx.lineTo(x,y); } if(moved) ctx.stroke(); } const t0=state.viewStart/state.fs, t1=t0+state.winSecs; const x0=((t0-(state.overview.ovStartSec||0))/Math.max(1e-6,state.overview.ovSpanSec||totalSec))*W; const x1=((t1-(state.overview.ovStartSec||0))/Math.max(1e-6,state.overview.ovSpanSec||totalSec))*W; const rx0=Math.max(0,Math.min(W,x0)), rx1=Math.max(0,Math.min(W,x1)); ctx.fillStyle='rgba(59,130,246,0.15)'; ctx.fillRect(rx0,0,Math.max(3,rx1-rx0),H); ctx.strokeStyle='rgba(59,130,246,0.6)'; ctx.strokeRect(rx0,0,Math.max(3,rx1-rx0),H); }
function startOverviewBuild(){ if(!hasData()) return; state.overview={pts:[],building:true,progress:0,ovStartSec:0,ovSpanSec:state.totalSamples/state.fs,range:null}; const totalSec=state.totalSamples/state.fs; const stepSec=4,winSec=8; let iStep=0; const totalSteps=Math.max(1,Math.ceil(totalSec/stepSec)); const perChunk=120; function chunk(){ const Wp=600; let done=0; for(;iStep<totalSteps && done<perChunk;iStep++,done++){ const center=iStep*stepSec; const t0=Math.max(0,center-winSec/2), t1=Math.min(totalSec,center+winSec/2); const dur=Math.max(1e-6,t1-t0); const seg=new Float32Array(Wp); for(let x=0;x<Wp;x++){ const t=t0+(x/Wp)*dur; const s=Math.min(state.totalSamples-1,Math.floor(t*state.fs)); const L=Math.max(1,state.leadCount|0); if(L===1){ seg[x]=sampleMV(0,s); } else { const vals=new Array(L); for(let j=0;j<L;j++) vals[j]=sampleMV(j,s); vals.sort((a,b)=>a-b); const mid=L>>1; seg[x]=(L%2? vals[mid] : 0.5*(vals[mid-1]+vals[mid])); } } const dt=dur/Math.max(1,Wp); const segBP=(state.baselineMode==='hp')?highpassIIR(seg,dt,0.5):(function(){ const tmp=Array.from(seg).sort((a,b)=>a-b); const med=tmp.length%2? tmp[(tmp.length-1)>>1] : 0.5*(tmp[tmp.length/2-1]+tmp[tmp.length/2]); for(let k=0;k<Wp;k++) seg[k]-=med; return seg; })(); const res=detectHR(segBP, dur/Wp, Math.max(3,state.hrSmooth|0), true, state.hrTol); const bpm=isFinite(res.avg)?res.avg:NaN; if(isFinite(bpm)) state.overview.pts.push({t:center,bpm}); } state.overview.progress=iStep/totalSteps; drawOverview(); if(iStep<totalSteps){ setTimeout(chunk,0); } else { state.overview.building=false; state.overview.range=getOverviewRange(); drawOverview(); } } chunk(); }
function resize(){ const r=els.canvas.getBoundingClientRect(); state.width=Math.max(320,r.width|0); state.height=Math.max(240,r.height|0); els.canvas.width=Math.round(state.width*state.dpr); els.canvas.height=Math.round(state.height*state.dpr); const ro=els.overview.getBoundingClientRect(); els.overview.width=Math.round(Math.max(320,ro.width|0)*state.dpr); els.overview.height=Math.round(Math.max(60,ro.height|0)*state.dpr); draw(); drawOverview(); }
window.addEventListener('resize', resize);
function setTool(name){ state.tool=name; [els.toolPan,els.toolTime,els.toolVolt].forEach(b=>b.classList.remove('active')); (name==='pan'?els.toolPan:(name==='time'?els.toolTime:els.toolVolt)).classList.add('active'); state.caliper.active=false; state.caliperV.active=false; }
els.toolPan.addEventListener('click',()=>setTool('pan'));
els.toolTime.addEventListener('click',()=>setTool('time'));
els.toolVolt.addEventListener('click',()=>setTool('volt'));
[els.showL0,els.showL1,els.showL2].forEach((cb,i)=>cb.addEventListener('change',()=>{ state.showLeads[i]=!!cb.checked; draw(); }));
els.scroll.addEventListener('input',()=>{ state.viewStart=Math.max(0, Math.min(+els.scroll.value|0, maxViewStart())); draw(); drawOverview(); });
els.reset.addEventListener('click',()=>{ state.viewStart=0; state.winSecs=+els.win.value||10; syncScroll(); draw(); drawOverview(); });
els.canvas.addEventListener('wheel', ev=>{ if(!hasData()) return; ev.preventDefault(); const viewS=Math.max(1,Math.round(state.winSecs*state.fs)); const center=state.viewStart+Math.floor(viewS*(ev.offsetX/Math.max(1,state.width))); const factor=ev.deltaY<0?0.9:1.1; state.winSecs=clamp(viewS*factor/state.fs,0.2,600); const newView=Math.max(1,Math.round(state.winSecs*state.fs)); state.viewStart=clamp(center-Math.floor(newView*(ev.offsetX/Math.max(1,state.width))),0,maxViewStart()); updateWinInput(); syncScroll(); draw(); drawOverview(); }, {passive:false});
let dragging=false, dragStartX=0, dragViewStart=0;
els.canvas.addEventListener('mousedown', ev=>{ if(!hasData()) return; const H=state.height; const hrPane=state.showHR?Math.round(H*0.18):0; const mainH=H-hrPane; const shown=Math.min(3,state.leadCount); const laneH=mainH/Math.max(1,shown); if(ev.shiftKey || state.tool==='time'){ state.caliper={a:xToTime(ev.offsetX), b:null, active:true}; draw(); return; } if(ev.ctrlKey || state.tool==='volt'){ const li=Math.max(0, Math.min(shown-1, Math.floor(ev.offsetY/Math.max(1,laneH)))); state.caliperV={lead:li, yA:ev.offsetY, yB:null, active:true}; draw(); return; } dragging=true; dragStartX=ev.clientX; dragViewStart=state.viewStart; });
window.addEventListener('mouseup', ()=>{ if(state.caliper.active) state.caliper.active=false; if(state.caliperV.active) state.caliperV.active=false; dragging=false; });
window.addEventListener('mousemove', ev=>{ if(!hasData()) return; const rect=els.canvas.getBoundingClientRect(); const x=ev.clientX-rect.left; const y=ev.clientY-rect.top; if(state.caliper.active){ state.caliper.b=xToTime(x); draw(); return; } if(state.caliperV.active){ state.caliperV.yB=y; draw(); return; } if(!dragging) return; const dx=ev.clientX-dragStartX; const spp=(state.winSecs*state.fs)/Math.max(1,state.width); state.viewStart=clamp(dragViewStart-Math.round(dx*spp),0,maxViewStart()); syncScroll(); draw(); drawOverview(); });
let ovDragging=false; function setViewFromOverviewEvent(e){ const rect=els.overview.getBoundingClientRect(); const x=e.clientX-rect.left; const W=rect.width; const totalSec=state.totalSamples/state.fs; const T0=Math.max(0,state.overview.ovStartSec||0); const Tspan=Math.max(1e-6,state.overview.ovSpanSec||totalSec); const clickSec=T0+(x/Math.max(1,W))*Tspan; const newStart=Math.max(0,Math.round(clickSec*state.fs)); state.viewStart=Math.min(newStart,maxViewStart()); syncScroll(); draw(); }
els.overview.addEventListener('mousedown',e=>{ if(!hasData()) return; ovDragging=true; setViewFromOverviewEvent(e); });
window.addEventListener('mouseup',()=>{ ovDragging=false; });
els.overview.addEventListener('mousemove',e=>{ if(!ovDragging) return; setViewFromOverviewEvent(e); });
els.overview.addEventListener('wheel',ev=>{ if(!hasData()) return; ev.preventDefault(); const rect=els.overview.getBoundingClientRect(); const W=rect.width; const totalSec=state.totalSamples/state.fs; let span=state.overview.ovSpanSec||totalSec; let start=Math.max(0, Math.min(state.overview.ovStartSec||0, totalSec-span)); const x=ev.clientX-rect.left; const cx=x/Math.max(1,W); const tCursor=start+cx*span; const factor=ev.deltaY<0?0.9:1.1; const newSpan=clamp(span*factor, Math.min(5,totalSec), totalSec); const newStart=clamp(tCursor-cx*newSpan,0,totalSec-newSpan); state.overview.ovSpanSec=newSpan; state.overview.ovStartSec=newStart; drawOverview(); }, {passive:false});
els.overview.addEventListener('dblclick',()=>{ if(!hasData()) return; const totalSec=state.totalSamples/state.fs; state.overview.ovStartSec=0; state.overview.ovSpanSec=totalSec; drawOverview(); });
function parseBinary(buf){ const dv=new DataView(buf); const n16=dv.byteLength>>>1; const i16=new Int16Array(n16); for(let i=0;i<n16;i++) i16[i]=dv.getInt16(i<<1,true); state.raw=i16; state.csv=null; state.leadCount=Math.max(1, +els.leads.value|0); state.totalSamples=Math.floor(i16.length/state.leadCount); }
function splitLines(s){ return s.split(/\r?\n/); }
function parseCSV(text){ const rows=splitLines(text).map(line=>line.trim()).filter(Boolean).map(line=>line.split(/[;,\t\s]+/).map(Number)).filter(r=>r.length && r.every(Number.isFinite)); if(!rows.length){ setStatus('CSV parse failed: no numeric rows',true); return; } const L=rows[0].length; const leads=Array.from({length:L},()=>[]); for(const r of rows){ for(let j=0;j<L;j++) leads[j].push(r[j]); } state.csv=leads.map(a=>Float32Array.from(a)); state.raw=null; state.leadCount=L; state.totalSamples=state.csv[0].length; }
function loadSample(){ const fs=state.fs|0; const dur=10; const n=Math.max(1,fs*dur); function synthLead(phase,scale){ const a=new Float32Array(n); const rr=0.8; const qrsW=0.02; for(let i=0;i<n;i++){ const t=i/fs; let v=0.03*Math.sin(2*Math.PI*0.33*t + (phase||0)); const d=t%rr; const near=d < rr-d ? d : rr-d; const qrs=Math.max(0,(qrsW-near))/qrsW; v+=1.0*qrs; v+=0.12*Math.sin(2*Math.PI*(1/rr)*t + (phase||0)*0.6); a[i]=(scale||1)*v; } return a; } state.csv=[synthLead(0,1.0), synthLead(0.15,0.9), synthLead(0.3,0.8)]; state.raw=null; state.leadCount=3; state.totalSamples=n; state.viewStart=0; const totalSec=n/fs; state.overview.ovStartSec=0; state.overview.ovSpanSec=totalSec; setStatus('Sample loaded: 3 leads, '+n+' samples/lead.'); syncScroll(); draw(); startOverviewBuild(); }
els.sample.addEventListener('click', loadSample);
els.file.addEventListener('change', async e=>{ const f=e.target.files&&e.target.files[0]; if(!f) return; try{ setStatus('Loading \"'+f.name+'\" …'); const buf=await f.arrayBuffer(); const name=(f.name||'').toLowerCase(); if(name.endsWith('.csv')||name.endsWith('.txt')) parseCSV(new TextDecoder().decode(new Uint8Array(buf))); else parseBinary(buf); state.fs=+els.fs.value||200; state.uvPerLSB=+els.uv.value||2; state.viewStart=0; const totalSec=state.totalSamples/state.fs; state.overview.ovStartSec=0; state.overview.ovSpanSec=totalSec; setStatus('Loaded: '+state.leadCount+' lead(s), '+state.totalSamples+' samples/lead. Wheel=zoom, drag=pan. Shift=time caliper, Ctrl=volt caliper.'); syncScroll(); draw(); startOverviewBuild(); }catch(err){ console.error(err); setStatus('Error reading file: '+(err&&err.message||err), true); } });
function applyTheme(name){ document.body.classList.toggle('theme-ecg', name==='ecg'); draw(); drawOverview(); }
els.theme.addEventListener('change', ()=>applyTheme(els.theme.value));
els.fs.addEventListener('change', ()=>{ state.fs=+els.fs.value||200; syncScroll(); draw(); drawOverview(); });
els.uv.addEventListener('change', ()=>{ state.uvPerLSB=+els.uv.value||2; draw(); });
els.leads.addEventListener('change', ()=>{ state.leadCount=Math.max(1,+els.leads.value|0); if(state.raw){ state.totalSamples=Math.floor(state.raw.length/state.leadCount); } syncScroll(); draw(); drawOverview(); });
els.win.addEventListener('change', ()=>{ state.winSecs=Math.max(0.2,+els.win.value||10); syncScroll(); draw(); drawOverview(); });
els.vfill.addEventListener('input', ()=>{ state.vfill=(+els.vfill.value||65)/100; els.vfillVal.textContent=Math.round(state.vfill*100); draw(); });
els.autoGain.addEventListener('change', ()=>{ state.autoGain=!!els.autoGain.checked; draw(); });
els.gainMode.addEventListener('change', ()=>{ state.gainMode=els.gainMode.value; draw(); });
els.showHR.addEventListener('change', ()=>{ state.showHR=!!els.showHR.checked; draw(); });
els.hrLock.addEventListener('change', ()=>{ state.hrLockScale=!!els.hrLock.checked; draw(); });
els.hrSmooth.addEventListener('change', ()=>{ state.hrSmooth=Math.max(1,(+els.hrSmooth.value||5)|0); draw(); drawOverview(); });
els.robustHR.addEventListener('change', ()=>{ state.robustHR=!!els.robustHR.checked; draw(); drawOverview(); });
els.hrTol.addEventListener('change', ()=>{ state.hrTol=Math.max(5,Math.min(80,(+els.hrTol.value||30))); draw(); drawOverview(); });
els.showScale.addEventListener('change', ()=>{ state.showScaleBar=!!els.showScale.checked; draw(); });
els.printBtn.addEventListener('click', ()=>window.print());
function init(){
  resize();
  updateWinInput();
  syncScroll();
  setStatus('Ready.');
}
window.addEventListener('load', init);
