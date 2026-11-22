import {createView} from './viewer.js';
import {drawQuadraticFace} from './mesh-nodes.js';

const $ = (id)=>document.getElementById(id);
const sections = [...document.querySelectorAll('#deck section[data-title]')];
const aliases = {explore:'fields',top:'solvers'};

export function setupDeck(onSlide) {
  let active = -1;
  const pick = $('slide-picker');
  const dots = sections.map((section,i)=>{
    const title = section.dataset.title;
    pick.add(new Option(`${i+1}. ${title}`,section.id));
    const b = document.createElement('button');
    b.type='button';
    b.textContent=String(i+1);
    b.title=title;
    b.setAttribute('aria-label',`Slide ${i+1}: ${title}`);
    b.addEventListener('click',()=>go(i));
    $('slide-dots').append(b);
    return b;
  });
  const go = (idx) => {
    if(idx>=0 && idx<sections.length) window.location.hash=sections[idx].id;
  };
  function show() {
    const key = decodeURIComponent(window.location.hash.slice(1));
    const idx = Math.max(0,sections.findIndex(el=>el.id===(aliases[key]??key)));
    if(active===idx)return;
    active=idx;
    const section=sections[idx];
    document.body.dataset.slide=section.id;
    sections.forEach((item,index)=>{item.hidden=index!==idx;});
    dots.forEach((dot,index)=>dot.setAttribute('aria-pressed',String(index===idx)));
    $('prev-slide').disabled=idx===0;
    $('next-slide').disabled=idx===sections.length-1;
    pick.value=section.id;
    onSlide(section.id);
    window.scrollTo(0,0);
  }
  $('prev-slide').addEventListener('click',()=>go(active-1));
  $('next-slide').addEventListener('click',()=>go(active+1));
  pick.addEventListener('change',()=>{window.location.hash=pick.value;});
  window.addEventListener('hashchange',show);
  const toggleClean = () => document.body.classList.toggle('clean');
  $('clean').addEventListener('click',toggleClean);
  $('restore-clean').addEventListener('click',toggleClean);
  window.addEventListener('keydown',event=>{
    if(event.key==='Escape' && document.body.classList.contains('clean')){
      document.body.classList.remove('clean');
      return;
    }
    if(event.defaultPrevented || event.altKey || event.metaKey || event.ctrlKey ||
      event.target.closest('input,select,textarea,.viewport'))return;
    if(event.key.toLowerCase()==='h'){toggleClean();return;}
    if(event.key==='ArrowRight'||event.key==='PageDown'){event.preventDefault();go(active+1);}
    if(event.key==='ArrowLeft'||event.key==='PageUp'){event.preventDefault();go(active-1);}
    if(event.key==='Home'){event.preventDefault();go(0);}
    if(event.key==='End'){event.preventDefault();go(sections.length-1);}
  });
  const full = $('present');
  if(!document.fullscreenEnabled)full.hidden=true;
  full.addEventListener('click',async()=>{
    try {
      if(document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {full.textContent='Fullscreen unavailable';}
  });
  document.addEventListener('fullscreenchange',()=>{
    const enabled=Boolean(document.fullscreenElement);
    full.textContent=enabled?'Exit fullscreen':'Fullscreen';
    full.setAttribute('aria-pressed',String(enabled));
  });
  const pipeline=$('gpu-pipeline');
  function showFlow() {
    pipeline.classList.remove('flow');
    void pipeline.offsetWidth;
    pipeline.classList.add('flow');
  }
  $('gpu-replay').addEventListener('click',showFlow);
  $('gpu').addEventListener('animationend',event=>{
    if(event.target===pipeline.lastElementChild)pipeline.classList.remove('flow');
  });
  show();
}

export function setupFigures(read, meshData, manifest, runs) {
  const states = {
    geometry:{hosts:['geometry-view'],views:[]},
    meshes:{hosts:['mesh-coarse','mesh-fine'],views:[]},
    partitions:{hosts:['part-coarse','part-fine'],views:[]}
  };
  let geometry, meshes, partitionData, pending, animation=0, animatedButton;
  function updateGeometry() {
    const level = Number($('geometry-load').value);
    const mass = manifest.theory.reference_weight_N / 1000;
    $('geometry-force').textContent=`${level}× · ${(level*mass).toFixed(1)} kN`;
    const view=states.geometry.views[0];
    if(!view || !geometry)return;
    view.update(geometry,geometry.rest,null,{field:'geometry',wire:false,ghost:false,scale:0,gravity:level},[0,1],null);
    $('geometry-view').dataset.load=String(level);
  }
  function updateExplosion() {
    const separation = Number($('explode').value);
    states.partitions.views.forEach((view,i)=>{
      view.spread(separation/100);
      $(states.partitions.hosts[i]).dataset.separation=String(separation);
    });
  }
  function clearAnimation() {
    cancelAnimationFrame(animation);
    animation=0;
    animatedButton?.setAttribute('aria-pressed','false');
    animatedButton=null;
  }
  function animate(button,slider,update,ms) {
    if(animatedButton===button){clearAnimation();return;}
    clearAnimation();
    button.setAttribute('aria-pressed','true');
    animatedButton=button;
    const target=Number(slider.max), start=performance.now();
    const motion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    function frame(now) {
      const t=motion?1:Math.min(1,(now-start)/ms);
      const next=String(Math.round(target*t));
      if(slider.value!==next){slider.value=next;update();}
      if(t<1)animation=requestAnimationFrame(frame);
      else clearAnimation();
    }
    slider.value='0'; update();
    animation=requestAnimationFrame(frame);
  }
  $('geometry-load').addEventListener('input',()=>{clearAnimation();updateGeometry();});
  $('geometry-play').addEventListener('click',()=>animate($('geometry-play'),$('geometry-load'),updateGeometry,2000));
  $('geometry-reset').addEventListener('click',()=>states.geometry.views[0]?.preset('orbit'));
  $('explode').addEventListener('input',()=>{clearAnimation();updateExplosion();});
  $('explode-play').addEventListener('click',()=>animate($('explode-play'),$('explode'),updateExplosion,2200));
  $('partition-reset').addEventListener('click',()=>{
    clearAnimation();$('explode').value='0';updateExplosion();states.partitions.views[0]?.preset('spread');
  });
  $('mesh-detail').addEventListener('click',()=>states.meshes.views[0]?.preset('detail'));
  $('mesh-reset').addEventListener('click',()=>states.meshes.views[0]?.preset('orbit'));
  const meshNodes = $('mesh-nodes');
  const showMeshNodes = () => {
    const show = meshNodes.getAttribute('aria-pressed') === 'true';
    $('mesh-node-options').hidden=!show;
    $('mesh-node-key').hidden=!show;
    states.meshes.views.forEach(view=>view.showNodes(show,$('midside-only').checked));
  };
  $('midside-only').addEventListener('change',showMeshNodes);
  meshNodes.addEventListener('click',()=>{
    const show = meshNodes.getAttribute('aria-pressed') !== 'true';
    meshNodes.setAttribute('aria-pressed',String(show));
    meshNodes.textContent = show ? 'Hide surface nodes' : 'Show surface nodes';
    showMeshNodes();
  });

  async function getPartitions() {
    const metadata=await read('./data/partitions.json');
    return Promise.all(['coarse','fine'].map(async key=>{
      const info=metadata[key], buffer=await read(`./data/${key}-partitions.bin.gz`,true);
      const p=3*info.points, n=info.triangles, r=info.ranks*3;
      if(buffer.byteLength!==4*(p+4*n+r))throw Error('Partition buffer size mismatch');
      return {xyz:new Float32Array(buffer,0,p),tri:new Uint32Array(buffer,4*p,3*n),
        ranks:new Uint32Array(buffer,4*(p+3*n),n),centers:new Float32Array(buffer,4*(p+4*n),r)};
    }));
  }
  const rest = (data) => { data.rest??={u:new Float32Array(data.xyz.length)};return data; };
  function unavailable(id) {
    const host=$(id);
    let message=host.querySelector('.notice');
    if(!message){message=document.createElement('p');message.className='notice';host.append(message);}
    message.hidden=false;
    message.textContent='3D unavailable. Open the Result fields slide for the static view.';
  }
  return async function enter(slide) {
    clearAnimation();
    const state=states[slide];
    if(!state || state.views.length)return;
    pending=slide;
    try {
      if(slide==='geometry') geometry??=rest(await meshData(runs.get('os-smoke')));
      if(slide==='meshes') meshes??=(await Promise.all(['os-smoke','os-fine'].map(id=>meshData(runs.get(id))))).map(rest);
      if(slide==='partitions') partitionData??=await getPartitions();
      if(pending!==slide || document.body.dataset.slide!==slide || state.views.length)return;
      state.hosts.forEach((id,i)=>{
        state.views[i]=createView($(id),()=>{},(camera,target)=>state.views[1-i]?.sync(camera,target));
      });
      if(slide==='geometry'){
        updateGeometry();
        $('geometry-status').hidden=true;
      } else if (slide==='meshes'){
        state.views.forEach((view,i)=>{
          view.update(meshes[i],meshes[i].rest,null,{field:'geometry',wire:true,ghost:false,scale:0},[0,1],null);
          const host=$(state.hosts[i]);
          host.dataset.ready='true';
          host.dataset.triangles=String(meshes[i].info.triangles);
        });
        state.views[0].preset('detail');
        drawQuadraticFace(meshes[0],$('mesh-face-detail'));
        showMeshNodes();
      } else {
        state.views.forEach((view,i)=>view.setDomains(partitionData[i]));
        state.views[0].preset('spread');
        updateExplosion();
      }
    } catch (error) {
      if(error.message.indexOf('WebGL')===-1)console.error(error);
      state.hosts.forEach(unavailable);
    }
  };
}
