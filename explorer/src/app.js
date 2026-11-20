import { createView, palette, diverging, partitions } from './viewer.js';
import { makePlot } from './plot.js';

const $ = (id) => document.getElementById(id);
const labels = {
  stress: ['von Mises stress','MPa'], displacement: ['Displacement magnitude','mm'],
  strain: ['Axial strain εₓₓ','mε'], plastic: ['Equivalent plastic strain','mε'],
  elastic: ['Elastic energy density','kJ/m³'], dissipation: ['Plastic dissipation density','kJ/m³'],
  partition: ['MPI partition','rank']
};
const meshName = {fine:'Fine',smoke:'Smoke'};
const slots = ['a','b'];
const state = {runs: [], field:'stress', scale:1, step:29, wire:false, ghost:true,
  chart:'force', timingMesh:'fine', playing:false, pin:null};
const meshCache = new Map(), frames = new Map(), parts = new Map();
const scenes = [null,null];
let manifest, loaded = [], revision = 0, timer = 0, byId;
let webgl = true;
const getRun = (slot) => state.runs[slot];
const maxStep = () => Math.min(...state.runs.map(r=>r.traces.length-1));
const nfmt = new Intl.NumberFormat('en',{maximumFractionDigits:3});
const fmt = (x) => nfmt.format(x);
const reportError = (err) => { console.error(err); $('fallback').hidden=false; };
const chart = makePlot($('plot'), $('curve-legend'), (step)=>{pause();setStep(step);});

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
  if(state.field==='partition')return [0,Math.max(...state.runs.map(r=>r.ranks))-1];
  if(state.field==='stress')return [0,250];
  const extents=manifest.runs.map(r=>r.levels[state.field]);
  const absolute=Math.max(...extents.flatMap(pair=>pair.map(Math.abs)));
  const size=10**Math.floor(Math.log10(Math.max(absolute,1e-8)));
  const bound=Math.ceil(absolute/size*2)*size/2;
  return [state.field==='strain' ? -bound : 0,bound];
}

function drawLegend(range) {
  const [title,unit]=labels[state.field];
  const bar=$('colorbar'), categorical=state.field==='partition';
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
  let value;
  if(state.field==='displacement') {
    const points=new Set();
    geometry.cellAt.forEach((owner,i)=>{
      if(owner===cell) for(let j=0;j<3;j++) points.add(geometry.tri[3*i+j]);
    });
    value=1000*[...points].reduce((sum,i)=>sum+Math.hypot(...frame.u.subarray(3*i,3*i+3)),0)/points.size;
  } else value=state.field==='partition' ? part[cell] : frame[state.field][cell];
  $('inspect-readout').textContent=`${run.solver} · element ${geometry.ids[cell]} · MPI rank ${part[cell]} · ${labels[state.field][0]} ${fmt(value)} ${labels[state.field][1]}${state.field==='displacement'?' (surface-node mean)':''}`;
}

function renderScenes() {
  const range=domain();
  drawLegend(range);
  loaded.forEach((data,slot)=>{
    if(data.run.id!==getRun(slot).id || data.step!==state.step)return;
    const cell=state.pin?.slot===slot && state.pin.run===data.run.id ? state.pin.cell : null;
    scenes[slot]?.update(data.geometry,data.frame,data.part,state,range,cell);
    const viewport=$('view-'+slots[slot]);
    viewport.dataset.run=data.run.id;
    viewport.dataset.load=String(data.step);
    viewport.dataset.field=state.field;
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
    $('meta-'+id).textContent=`Job ${run.job} · ${run.ranks} MPI · ${run.backend}`;
    $('tip-'+id).textContent=`${tip.toFixed(3)} mm tip ↓`;
  });
  chart({runs:state.runs, kind:state.chart, step:state.step,
    reference:manifest.reference, theory:manifest.theory});
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
  $('timing-note').textContent=`Minimal output first, full output second. ${state.timingMesh==='fine'?'The fine run has 29 increments.':'The smoke run has 30 increments.'} Field time includes extraction, serialization and writes through the page cache.`;
}
function renderGpu() {
  const profiles=[['smoke-elastic','Smoke elastic','cuda-qr','Sparse QR'],
    ['smoke-nonlinear','Smoke nonlinear','cuda-qr','Sparse QR'],['fine-elastic','Fine elastic','cuda-cg','Conjugate gradients']];
  const median=(runs) => runs.map(r=>Number(r.wall_s)).sort((a,b)=>a-b)[1].toFixed(2);
  $('gpu-timings').innerHTML=`<thead><tr><th scope="col">Case</th><th scope="col">CPU MUMPS [s]</th><th scope="col">RTX 5090 [s]</th><th scope="col">CUDA solver</th></tr></thead><tbody>${
    profiles.map(([id,title,backend,algo])=>{
      const group=manifest.gpu.filter(r=>r.profile===id);
      return `<tr><th scope="row">${title}</th><td>${median(group.filter(r=>r.backend==='mumps'))}</td><td>${median(group.filter(r=>r.backend===backend))}</td><td>${algo}</td></tr>`;
    }).join('')}</tbody>`;
}

function applyRun(slot, runId) {
  pause();
  state.runs[slot] = byId.get(runId);
  state.pin = null;
  $('run-' + slots[slot]).value = runId;
  $('element').value = '';
  $('inspect-readout').textContent = 'Select a surface element in either view.';
  return setStep(state.step);
}
function setField(value) { state.field = value; $('field').value = value; renderScenes(); }
function setScale(value) { state.scale = Number(value); $('scale').value = String(value); renderScenes(); }
function setChart(kind) {
  state.chart = kind;
  for (const b of document.querySelectorAll('[data-chart]')) b.setAttribute('aria-pressed', String(b.dataset.chart === kind));
  renderText();
}
function setTimingMesh(mesh) {
  state.timingMesh = mesh;
  for (const b of document.querySelectorAll('[data-mesh]')) b.setAttribute('aria-pressed', String(b.dataset.mesh === mesh));
  renderTimings();
}

const chapters = [
  { section: 'intro', kicker: 'Esmeralda · Finite-element study', title: 'The I-beam benchmark',
    body: 'Three solvers, one steel cantilever. Watch a 6 m I-beam move from elastic bending into plastic collapse under its own amplified weight — modeled three independent ways on the same cluster.',
    enter() {} },
  { section: 'explore', kicker: 'The model', title: 'One cantilever, two meshes',
    body: '6 m steel I-section, 400×200 mm, 25 mm flanges, 14 mm web, fixed at the root. Small-strain J2 plasticity: E = 210 GPa, ν = 0.30, σy = 250 MPa, ρ = 7,850 kg/m³. Ten-node tetrahedra, four integration points — 7,140 elements (“smoke”) or 69,600 (“fine”).',
    enter() { applyRun(0,'os-fine'); applyRun(1,'fx-fine'); setField('displacement'); setScale(1); setStep(0); scenes[0]?.preset('side'); } },
  { section: 'explore', kicker: 'Solver 1 of 3', title: 'OpenSeesMP 3.8.0 · “Ladruño”',
    body: 'UC Berkeley’s MPI finite-element framework for nonlinear structural and earthquake simulation, using a MUMPS direct solver here. Fine mesh on 16 ranks (job 9580) beside the smoke mesh on 4 ranks (job 9020).',
    enter() { applyRun(0,'os-fine'); applyRun(1,'os-smoke'); setField('stress'); setScale(1); setStep(29); scenes[0]?.preset('orbit'); } },
  { section: 'explore', kicker: 'Solver 2 of 3', title: 'Kratos Multiphysics 10.3.0',
    body: 'CIMNE’s general multi-physics framework, solved here with the Amesos MUMPS direct solver. Fine mesh on 16 ranks (job 9579) beside smoke on 4 ranks (job 9481).',
    enter() { applyRun(0,'kr-fine'); applyRun(1,'kr-smoke'); setField('stress'); setStep(29); } },
  { section: 'explore', kicker: 'Solver 3 of 3', title: 'FEniCSx · DOLFINx 0.11.0',
    body: 'Code-generated finite elements via UFL, solved with PETSc 3.25.6. Fine mesh on 16 CPU ranks (MUMPS, job 9581) beside a single-GPU pilot on the smoke mesh: one RTX 5090 running sparse QR in FP64 (job 9694).',
    enter() { applyRun(0,'fx-fine'); applyRun(1,'fx-gpu'); setField('stress'); setStep(29); } },
  { section: 'explore', kicker: 'Head to head', title: 'Three solvers, one answer',
    body: 'OpenSeesMP and FEniCSx on the fine mesh, tracked against the analytical Euler–Bernoulli limit: 191.98 kN at full plasticity (27.9× gravity). The refined 3D solids keep carrying load to 199.58 kN by 29×.',
    enter() { applyRun(0,'os-fine'); applyRun(1,'fx-fine'); setField('stress'); setStep(29); setChart('force'); } },
  { section: 'performance', kicker: '180 validated CPU runs', title: 'Rank scaling and I/O',
    body: 'Wall time, solve time and field-output time across 4, 8, 16 and 32 MPI ranks, both meshes, three repeats each — plus 18 single-GPU pilots on an RTX 5090.',
    enter() { setTimingMesh('fine'); $('timing-metric').value = 'wall_s'; renderTimings(); } },
  { section: 'machines', kicker: 'Universidad de los Andes · Chile', title: 'The Esmeralda cluster',
    body: 'Two AMD Ryzen 9 5950X nodes — 16 cores / 32 threads, 62.7 GiB RAM, dual-port 25 GbE RoCE — for the CPU sweep; one NVIDIA RTX 5090 (32,607 MiB VRAM) for the GPU pilots. Slurm 24.11.5, Open MPI 5, NVMe-backed NFS.',
    enter() {} },
];
let chapterIndex = 0;

function renderChapterShell() {
  const strip = chapters.map((_,i) => `<button type="button" data-chapter="${i}" aria-label="Chapter ${i+1} of ${chapters.length}"></button>`).join('');
  $('chapters').innerHTML = `
    <div class="chapter-strip" role="tablist" aria-label="Presentation chapters">${strip}</div>
    <div class="chapter-card">
      <p class="eyebrow" id="chapterKicker"></p>
      <h2 id="chapterTitle"></h2>
      <p id="chapterBody"></p>
      <div class="chapter-nav">
        <button type="button" id="chapterPrev" class="quiet">‹ Previous</button>
        <button type="button" id="chapterNext" class="quiet">Next ›</button>
        <span id="chapterCount"></span>
      </div>
    </div>`;
  $('chapters').addEventListener('click', (event) => {
    const button = event.target.closest('button[data-chapter]');
    if (button) goChapter(Number(button.dataset.chapter));
  });
  $('chapterPrev').addEventListener('click', () => goChapter(chapterIndex - 1));
  $('chapterNext').addEventListener('click', () => goChapter(chapterIndex + 1));
}

function goChapter(index) {
  chapterIndex = Math.min(chapters.length - 1, Math.max(0, index));
  const chapter = chapters[chapterIndex];
  document.body.dataset.section = chapter.section;
  chapter.enter();
  for (const button of $('chapters').querySelectorAll('[data-chapter]'))
    button.setAttribute('aria-current', String(Number(button.dataset.chapter) === chapterIndex));
  $('chapterKicker').textContent = chapter.kicker;
  $('chapterTitle').textContent = chapter.title;
  $('chapterBody').textContent = chapter.body;
  $('chapterCount').textContent = `${chapterIndex + 1} / ${chapters.length}`;
  $('chapterPrev').disabled = chapterIndex === 0;
  $('chapterNext').disabled = chapterIndex === chapters.length - 1;
  window.scrollTo(0, 0);
}

function initView() {
  try {
    if(!('DecompressionStream' in window))throw new Error('This browser does not support gzip asset streams');
    slots.forEach((id,slot)=>{
      scenes[slot]=createView($('view-'+id),cell=>inspect(slot,cell),
        (cam,target)=>scenes[1-slot]?.sync(cam,target));
    });
  } catch {
    webgl=false;
    $('fallback').hidden=false;
    slots.forEach(id=>{$('status-'+id).textContent='3D unavailable in this browser';});
    for (const id of ['field','scale','wire','ghost','camera-orbit','camera-side','camera-end','inspect-run','element']) $(id).disabled=true;
    $('inspect').querySelector('button').disabled=true;
  }
}

async function main() {
  manifest=await read('./data/manifest.json');
  byId = new Map(manifest.runs.map(run=>[run.id,run]));
  state.runs=[byId.get('os-fine'),byId.get('fx-fine')];
  slots.forEach((id,slot)=>{
    const select=$('run-'+id);
    select.replaceChildren(...manifest.runs.map(run=>new Option(
      `${run.solver} · ${meshName[run.mesh]}${run.id==='fx-gpu'?' · RTX 5090':''}`,run.id)));
    select.value=state.runs[slot].id;
    select.addEventListener('change',()=>applyRun(slot,select.value));
  });
  initView();
  $('field').addEventListener('change',()=>{state.field=$('field').value;renderScenes();});
  $('scale').addEventListener('change',()=>{state.scale=Number($('scale').value);renderScenes();});
  for(const key of ['wire','ghost'])$(key).addEventListener('change',()=>{state[key]=$(key).checked;renderScenes();});
  for(const mode of ['orbit','side','end'])$('camera-'+mode).addEventListener('click',()=>scenes[0]?.preset(mode));
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
  for(const button of document.querySelectorAll('[data-chart]'))button.addEventListener('click',()=>setChart(button.dataset.chart));
  for(const button of document.querySelectorAll('[data-mesh]'))button.addEventListener('click',()=>setTimingMesh(button.dataset.mesh));
  $('timing-metric').addEventListener('change',renderTimings);
  renderChapterShell();
  $('present').addEventListener('click',()=>{
    const active=document.body.classList.toggle('presentation');
    $('present').textContent=active?'Exit presentation':'Presentation view';
    $('present').setAttribute('aria-pressed',String(active));
    $('chapters').hidden=!active;
    if(active)goChapter(0);
    else delete document.body.dataset.section;
  });
  document.addEventListener('keydown',(event)=>{
    if(!document.body.classList.contains('presentation'))return;
    if(document.activeElement?.closest?.('.viewport'))return;
    if(event.key==='ArrowRight'||event.key==='PageDown'){event.preventDefault();goChapter(chapterIndex+1);}
    else if(event.key==='ArrowLeft'||event.key==='PageUp'){event.preventDefault();goChapter(chapterIndex-1);}
  });
  renderTimings();
  renderGpu();
  await refresh();
}
main().catch(error=>{
  slots.forEach(x=>{$('status-'+x).hidden=false;$('status-'+x).textContent='Run list could not be loaded.';});
  reportError(error);
});
