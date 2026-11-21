import { createView, palette, diverging, partitions } from './viewer.js';
import { makePlot } from './plot.js';
import { setupDeck, setupFigures } from './deck.js';
import { setupSolverSettings } from './solver-settings.js';

const $ = (id) => document.getElementById(id);
const labels = {
  stress: ['von Mises stress','MPa'], displacement: ['Displacement magnitude','mm'],
  strain: ['Axial strain εₓₓ','mε'], plastic: ['Equivalent plastic strain','mε'],
  elastic: ['Elastic energy density','kJ/m³'], dissipation: ['Plastic dissipation density','kJ/m³'],
  partition: ['MPI partition','rank']
};
const meshName = {fine:'Fine',smoke:'Coarse'};
const slots = ['a','b'];
const state = {runs: [], field:'stress', scale:1, step:29, wire:true, ghost:true,
  chart:'force', curveStep:29, timingMesh:'fine', playing:false, pin:null};
const meshCache = new Map(), frames = new Map(), parts = new Map();
const scenes = [null,null];
let manifest, loaded = [], revision = 0, timer = 0;
let webgl = true;
let startedFields = false;
const getRun = (slot) => state.runs[slot];
const maxStep = () => Math.min(...state.runs.map(r=>r.traces.length-1));
const nfmt = new Intl.NumberFormat('en',{maximumFractionDigits:3});
const fmt = (x) => nfmt.format(x);
const reportError = (err) => { console.error(err); $('fallback').hidden=false; };
const chart = makePlot($('plot'), $('curve-legend'), (step)=>{state.curveStep=step;renderCurves();});

function renderCurves() {
  const filter=$('curve-mode').value;
  const runs=filter==='selected' ? state.runs :
    manifest.runs.filter(run=>filter==='all' || (filter==='coarse' && run.mesh==='smoke') ||
      (filter==='fine' && run.mesh==='fine') || run.id===filter);
  const slider=$('curve-cursor');
  const limit=Math.max(...runs.map(run=>run.traces.at(-1)[0]));
  state.curveStep=Math.min(state.curveStep,limit);
  slider.max=String(limit);
  slider.value=String(state.curveStep);
  $('curve-load').textContent=`${state.curveStep}× gravity`;
  chart({runs,kind:state.chart,step:state.curveStep,reference:manifest.reference,theory:manifest.theory});
}

async function read(path, binary=false) {
  const response = await fetch(new URL(path, document.baseURI));
  if (!response.ok) throw new Error(`Asset ${path} returned ${response.status}`);
  if (!binary) return response.json();
  const buffer = await response.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  // Accept a static file, or a host which has already removed the gzip layer.
  return bytes[0]===31 && bytes[1]===139
    ? new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()
    : buffer;
}

function cached(map, key, create, limit=Infinity) {
  if (map.has(key)) {
    const value=map.get(key);
    map.delete(key); map.set(key,value);
    return value;
  }
  const pending=create().catch(error=>{map.delete(key);throw error;});
  map.set(key,pending);
  while(map.size>limit) map.delete(map.keys().next().value);
  return pending;
}

function meshData(run) {
  return cached(meshCache,run.mesh,async()=>{
    const info=manifest.meshes[run.mesh];
    const buffer=await read(`./data/${run.mesh}.bin.gz`,true);
    const p=info.points*3, t=info.triangles*3, c=info.triangles;
    if(buffer.byteLength!==4*(p+t+c+info.surfaceCells)) throw Error('Incorrect mesh buffer length');
    return {info,xyz:new Float32Array(buffer,0,p),tri:new Uint32Array(buffer,4*p,t),
      cellAt:new Uint32Array(buffer,4*(p+t),c), ids:new Uint32Array(buffer,4*(p+t+c),info.surfaceCells)};
  });
}

function caseFrame(run, step) {
  return cached(frames,`${run.id}/${step}`,async()=>{
    const {points,surfaceCells}=manifest.meshes[run.mesh];
    const len=points*3+surfaceCells*manifest.fields.length;
    const buffer = step===0 ? new ArrayBuffer(len*4)
      : await read(`./data/${run.id}/${String(step).padStart(2,'0')}.bin.gz`,true);
    if(buffer.byteLength!==len*4) throw Error('Incorrect field buffer length');
    return {u:new Float32Array(buffer,0,points*3),
      ...Object.fromEntries(manifest.fields.map((key,i) => [key,
        new Float32Array(buffer,4*(points*3+i*surfaceCells),surfaceCells)]))};
  },12);
}

function partitionData(run) {
  return cached(parts,run.id,async()=>{
    const buffer=await read(`./data/${run.id}/partition.bin.gz`,true);
    if(buffer.byteLength!==2*manifest.meshes[run.mesh].surfaceCells) throw Error('Incorrect partition buffer length');
    return new Uint16Array(buffer);
  });
}

function domain() {
  if(state.field==='geometry')return [0,1];
  if(state.field==='partition')return [0,Math.max(...state.runs.map(r=>r.ranks))-1];
  if(state.field==='stress')return [0,250];
  const extents=manifest.runs.map(r=>r.levels[state.field]);
  const absolute=Math.max(...extents.flatMap(pair=>pair.map(Math.abs)));
  const size=10**Math.floor(Math.log10(Math.max(absolute,1e-8)));
  const bound=Math.ceil(absolute/size*2)*size/2;
  return [state.field==='strain' ? -bound : 0,bound];
}

function drawLegend(range) {
  const bar=$('colorbar'), categorical=state.field==='partition';
  const meshOnly=state.field==='geometry';
  bar.hidden=meshOnly;
  $('legend-ticks').hidden=meshOnly;
  if(meshOnly) {
    $('legend-title').textContent='T10 surface mesh';
    return;
  }
  const [title,unit]=labels[state.field];
  $('legend-title').textContent=categorical ? 'MPI rank ownership · zero-based' :
    `${title} [${unit}] · ${state.field==='stress'?'nominal yield at 250 MPa':'shared scale'}`;
  const colors=categorical ? partitions.slice(0,range[1]+1) : (state.field==='strain'?diverging:palette);
  if(categorical) {
    bar.style.background=colors.length===1 ? colors[0] : `linear-gradient(90deg,${colors.map((color,i)=>`${color} ${100*i/colors.length}% ${100*(i+1)/colors.length}%`).join(',')})`;
  } else bar.style.background=`linear-gradient(90deg,${colors.join(',')})`;
  const ticks=categorical ? (range[1]===0?[0]:range[1]<=4?Array.from({length:range[1]+1},(_,i)=>i):[0,4,8,12,range[1]])
    : Array.from({length:5},(_,i)=>range[0]+(range[1]-range[0])*i/4);
  $('legend-ticks').replaceChildren(...[...new Set(ticks)].map(value=>{
    const span=document.createElement('span');span.textContent=fmt(value);return span;
  }));
}

function inspect(slot, cell) {
  if (!loaded[slot] || cell==null) return;
  state.pin={slot,cell,run:loaded[slot].run.id};
  $('inspect-run').value=String(slot);
  $('element').value=loaded[slot].geometry.ids[cell];
  renderScenes();
}
function showPin() {
  const next=state.pin && loaded[state.pin.slot];
  if(!next || next.run.id!==state.pin.run) return;
  const {geometry,frame,part,run}=next, cell=state.pin.cell;
  const display=`${run.solver} · element ${geometry.ids[cell]} · MPI rank ${part[cell]}`;
  if(state.field==='geometry') {
    $('inspect-readout').textContent=display;
    return;
  }
  let value;
  if(state.field==='displacement') {
    const points=new Set();
    geometry.cellAt.forEach((owner,i)=>{
      if(owner===cell) for(let j=0;j<3;j++) points.add(geometry.tri[3*i+j]);
    });
    value=1000*[...points].reduce((sum,i)=>sum+Math.hypot(...frame.u.subarray(3*i,3*i+3)),0)/points.size;
  } else value=state.field==='partition' ? part[cell] : frame[state.field][cell];
  $('inspect-readout').textContent=`${display} · ${labels[state.field][0]} ${fmt(value)} ${labels[state.field][1]}${state.field==='displacement'?' (surface-node mean)':''}`;
}

function renderScenes() {
  const range=domain();
  drawLegend(range);
  loaded.forEach((data,slot)=>{
    if(data.run.id!==getRun(slot).id || data.step!==state.step)return;
    const cell=state.pin?.slot===slot && state.pin.run===data.run.id ? state.pin.cell : null;
    const settings=state.field==='geometry'?{...state,wire:true}:state;
    scenes[slot]?.update(data.geometry,data.frame,data.part,settings,range,cell);
    const viewport=$('view-'+slots[slot]);
    viewport.dataset.run=data.run.id;
    viewport.dataset.load=String(data.step);
    viewport.dataset.field=state.field;
    viewport.dataset.triangles=String(data.geometry.info.triangles);
  });
  showPin();
}

function renderText() {
  const load=state.step*manifest.theory.reference_weight_N/1000;
  $('load').max=String(maxStep());
  $('load').value=String(state.step);
  $('load').setAttribute('aria-valuetext',`${state.step} times gravity, ${load.toFixed(2)} kilonewtons`);
  $('load-readout').textContent=`${state.step}× gravity · ${load.toFixed(2)} kN`;
  slots.forEach((id,slot)=>{
    const run=getRun(slot), tip=run.traces[state.step][1];
    const count=fmt(manifest.meshes[run.mesh].elements);
    $('meta-'+id).textContent=`${count} T10 · ${run.ranks} MPI · Job ${run.job}`;
    $('meta-'+id).title=run.backend;
    $('tip-'+id).textContent=`${tip.toFixed(3)} mm tip ↓`;
  });
}

async function refresh() {
  const id=++revision, step=state.step;
  renderText();
  if(!webgl)return;
  let loading;
  try {
    loading=setTimeout(()=>{
      if(id===revision)slots.forEach(x=>{$('status-'+x).hidden=false;$('status-'+x).textContent=`Loading ${step}× gravity…`;});
    },160);
    const prepared=await Promise.all(state.runs.map(async(run)=>{
      const [geometry,frame,part] = await Promise.all([meshData(run),caseFrame(run,step),partitionData(run)]);
      return {run,step,geometry,frame,part};
    }));
    if(id!==revision)return;
    loaded=prepared;
    renderScenes();
    slots.forEach(x=>{$('status-'+x).hidden=true;});
  } catch(err) {
    if(id===revision) {
      pause();
      slots.forEach(x=>{$('status-'+x).hidden=false;$('status-'+x).textContent='Field data could not be loaded.';});
      reportError(err);
    }
  } finally {clearTimeout(loading);}
}

function setStep(step) {
  state.step=Math.min(maxStep(),Math.max(0,Math.round(step)));
  return refresh();
}
function pause() {
  state.playing=false;
  clearTimeout(timer);
  $('play').textContent='Play';
  $('play').setAttribute('aria-pressed','false');
}
async function playStep(step) {
  if(!state.playing)return;
  await setStep(step);
  if(!state.playing)return;
  if(state.step===maxStep()){pause();return;}
  timer=setTimeout(()=>playStep(state.step+1),470);
}

function renderTimings() {
  const selected=$('timing-metric').value;
  const available=manifest.timings.filter(r=>r.mesh===state.timingMesh);
  const rows=[['4','default','Single node'],['8','default','Single node'],['16','default','Single node'],
    ['32','rdma-on','RoCE'],['32','rdma-off','TCP']];
  const solvers=['opensees','kratos','fenicsx'];
  const table=$('timings');
  const t=(r)=> selected==='bytes' ? (Number(r.median_bytes)/1e6).toFixed(2) : Number(r['median_'+selected]).toFixed(2);
  table.innerHTML=`<thead><tr><th scope="col">MPI ranks</th><th scope="col">Interconnect</th><th scope="col">OpenSeesMP</th><th scope="col">Kratos MUMPS</th><th scope="col">FEniCSx</th></tr></thead><tbody>${
    rows.map(([rank,mode,label])=>`<tr><th scope="row">${rank}</th><td>${label}</td>${solvers.map(solver=>{
      const pair=['minimal','full'].map(output=>available.find(r=>r.solver===solver&&r.ranks===rank&&r.transport===mode&&r.output===output));
      return `<td class="time-cell"><span title="Minimal output">${t(pair[0])}</span><span title="Full output">${t(pair[1])}</span></td>`;
    }).join('')}</tr>`).join('')
  }</tbody>`;
  $('timing-note').textContent=`Minimal output first, full output second. ${state.timingMesh==='fine'?'Fine mesh · 29 increments.':'Coarse mesh · 30 increments.'} Field time includes extraction, serialization and writes through the page cache.`;
}
function renderGpu() {
  const profiles=[['smoke-elastic','Coarse elastic','cuda-qr','Sparse QR'],
    ['smoke-nonlinear','Coarse nonlinear','cuda-qr','Sparse QR'],['fine-elastic','Fine elastic','cuda-cg','Conjugate gradients']];
  const median=(runs) => runs.map(r=>Number(r.wall_s)).sort((a,b)=>a-b)[1].toFixed(2);
  $('gpu-timings').innerHTML=`<thead><tr><th scope="col">Case</th><th scope="col">CPU MUMPS [s]</th><th scope="col">RTX 5090 [s]</th><th scope="col">CUDA solver</th></tr></thead><tbody>${
    profiles.map(([id,title,backend,algo])=>{
      const group=manifest.gpu.filter(r=>r.profile===id);
      return `<tr><th scope="row">${title}</th><td>${median(group.filter(r=>r.backend==='mumps'))}</td><td>${median(group.filter(r=>r.backend===backend))}</td><td>${algo}</td></tr>`;
    }).join('')}</tbody>`;
}

function initView() {
  try {
    if(!('DecompressionStream' in window))throw new Error('This browser does not support gzip asset streams');
    slots.forEach((id,slot)=>{
      scenes[slot]=createView($('view-'+id),cell=>inspect(slot,cell),
        (cam,target)=>scenes[1-slot]?.sync(cam,target));
    });
    scenes[0].preset('detail');
  } catch {
    webgl=false;
    $('fallback').hidden=false;
    slots.forEach(id=>{$('status-'+id).textContent='3D unavailable in this browser';});
    for (const id of ['field','scale','wire','ghost','camera-orbit','camera-side','camera-end','camera-detail','inspect-run','element']) $(id).disabled=true;
    $('inspect').querySelector('button').disabled=true;
  }
}

async function main() {
  manifest=await read('./data/manifest.json');
  const byId = new Map(manifest.runs.map(run=>[run.id,run]));
  state.runs=[byId.get('os-fine'),byId.get('fx-fine')];
  slots.forEach((id,slot)=>{
    const select=$('run-'+id);
    select.replaceChildren(...manifest.runs.map(run=>new Option(
      `${run.solver} · ${meshName[run.mesh]}${run.id==='fx-gpu'?' · RTX 5090':''}`,run.id)));
    select.value=state.runs[slot].id;
    select.addEventListener('change',()=>{
      pause();state.runs[slot]=byId.get(select.value);state.pin=null;
      $('element').value='';$('inspect-readout').textContent='Select a surface element in either view.';
      setStep(state.step);
    });
  });
  $('field').addEventListener('change',()=>{
    state.field=$('field').value;
    $('wire').disabled=state.field==='geometry';
    $('wire').checked=state.field==='geometry'||state.wire;
    renderScenes();
  });
  $('scale').addEventListener('change',()=>{state.scale=Number($('scale').value);renderScenes();});
  for(const key of ['wire','ghost'])$(key).addEventListener('change',()=>{state[key]=$(key).checked;renderScenes();});
  for(const mode of ['orbit','side','end','detail'])$('camera-'+mode).addEventListener('click',()=>scenes[0]?.preset(mode));
  $('inspect').addEventListener('submit',event=>{
    event.preventDefault();
    const slot=Number($('inspect-run').value);
    if(!loaded[slot] || loaded[slot].run.id!==getRun(slot).id || loaded[slot].step!==state.step)return;
    const id=Number($('element').value);
    const cell=loaded[slot].geometry.ids.indexOf(id);
    if(cell>=0)inspect(slot,cell);
    else $('inspect-readout').textContent='That element ID has no exterior face in this run.';
  });
  $('load').addEventListener('input',()=>{pause();setStep(Number($('load').value));});
  $('reset-load').addEventListener('click',()=>{pause();setStep(0);});
  $('play').addEventListener('click',()=>{
    if(state.playing){pause();return;}
    state.playing=true;
    $('play').textContent='Pause';
    $('play').setAttribute('aria-pressed','true');
    playStep(state.step===maxStep()?0:state.step+1);
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
  for(const button of document.querySelectorAll('[data-chart]'))button.addEventListener('click',()=>{
    state.chart=button.dataset.chart;
    if(state.chart==='energy' && ['all','coarse','fine'].includes($('curve-mode').value)) $('curve-mode').value='selected';
    for(const b of document.querySelectorAll('[data-chart]')) b.setAttribute('aria-pressed',String(b===button));
    renderCurves();
  });
  for(const button of document.querySelectorAll('[data-mesh]'))button.addEventListener('click',()=>{
    state.timingMesh=button.dataset.mesh;
    for(const b of document.querySelectorAll('[data-mesh]')) b.setAttribute('aria-pressed',String(b===button));
    renderTimings();
  });
  $('timing-metric').addEventListener('change',renderTimings);
  for(const run of manifest.runs) $('curve-mode').add(new Option(
    `${run.solver} · ${meshName[run.mesh]}${run.id==='fx-gpu'?' · RTX 5090':''}`,run.id));
  $('curve-mode').addEventListener('change',()=>{
    if(['all','coarse','fine'].includes($('curve-mode').value) && state.chart==='energy') {
      document.querySelector('[data-chart=force]').click();
      return;
    }
    renderCurves();
  });
  $('curve-cursor').addEventListener('input',()=>{state.curveStep=Number($('curve-cursor').value);renderCurves();});
  renderTimings();
  renderGpu();
  const figures = setupFigures(read,meshData,manifest,byId);
  const solverSettings = setupSolverSettings(read);
  setupDeck(slide=>{
    pause();
    revision++;
    figures(slide);
    if(slide==='fields') {
      if(!startedFields){initView();startedFields=true;}
      refresh();
    }
    if(slide==='curves') renderCurves();
    if(slide==='solver-options') solverSettings();
  });
}
main().catch(error=>{
  slots.forEach(x=>{$('status-'+x).hidden=false;$('status-'+x).textContent='Run list could not be loaded.';});
  reportError(error);
});
