import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export const palette = ['#27398a', '#107c9b', '#56b887', '#e4ce54', '#f47c36'];
export const diverging = ['#285aa4', '#70a7d4', '#f0eddf', '#e67950', '#a42032'];
export const partitions = ['#37a8b6','#f09c5d','#a792e6','#a5c35f','#f47691','#5bbbe6','#f1cc64','#719d84','#e18acc','#e8a588','#97acc8','#e45f58','#c0d57b','#b2a0f1','#6dd3ad','#f4b03d'];
const fieldColor = (hex) => new THREE.Color(hex);
const colors = palette.map(fieldColor), diverge = diverging.map(fieldColor), ranks = partitions.map(fieldColor);
const ink = new THREE.Color('#133435');

export function createView(host, onPick, onCamera) {
  const r = new THREE.WebGLRenderer({alpha: true, antialias: true});
  r.setPixelRatio(Math.min(devicePixelRatio, 1.8));
  r.outputColorSpace = THREE.SRGBColorSpace;
  r.domElement.setAttribute('aria-hidden', 'true');
  host.prepend(r.domElement);
  const camera = new THREE.OrthographicCamera(-3.8, 3.8, 2.1, -2.1, .02, 80);
  camera.position.set(3.9, 2.6, 7.5);
  const scene = new THREE.Scene();
  const controls = new OrbitControls(camera, r.domElement);
  controls.enableDamping = false;
  controls.minZoom = .42;
  controls.maxZoom = 14;
  controls.zoomSpeed = .8;
  const ray = new THREE.Raycaster();
  scene.add(new THREE.AmbientLight(0xf5fffc, 1.45));
  const sidelight = new THREE.DirectionalLight(0xfff1df, 1.15);
  sidelight.position.set(3, 5, 5);
  scene.add(sidelight);
  const rim = new THREE.DirectionalLight(0xb6d7e6, .45);
  rim.position.set(-5, 1, -4);
  scene.add(rim);
  const grid = new THREE.GridHelper(12, 24, 0x334946, 0x263735);
  grid.position.y = -1.45;
  grid.material.transparent = true;
  grid.material.opacity = .32;
  scene.add(grid);
  const loadDiagram = new THREE.Group();
  const support = new THREE.Mesh(
    new THREE.BoxGeometry(.12,.85,.66),
    new THREE.MeshLambertMaterial({color:0x526582,transparent:true,opacity:.72})
  );
  support.position.x = -3.06;
  loadDiagram.add(support);
  const loadArrows = Array.from({length:9},(_,i)=>{
    const arrow = new THREE.ArrowHelper(new THREE.Vector3(0,-1,0),
      new THREE.Vector3(-2.8+.69*i,.95,0),.68,0xffcd68,.15,.105);
    loadDiagram.add(arrow);
    return arrow;
  });
  loadDiagram.visible = false;
  scene.add(loadDiagram);
  const material = new THREE.MeshLambertMaterial({vertexColors:true, side:THREE.DoubleSide});
  const wireMaterial = new THREE.MeshBasicMaterial({color:0x132321, opacity:.38, transparent:true, wireframe:true});
  const restMaterial = new THREE.LineBasicMaterial({color:0xd9e5d8, opacity:.31, transparent:true});
  const outlineMaterial = new THREE.LineBasicMaterial({color:0xffffff, depthTest:false});
  let mesh, wire, rest, outline, structure, px, py;
  let syncing = false;
  let domains = [];
  const brush = new THREE.Color();
  const render = () => r.render(scene, camera);
  controls.addEventListener('change', () => { render(); if (!syncing) onCamera(camera, controls.target); });
  const observer = new ResizeObserver(() => {
    const {width, height} = host.getBoundingClientRect();
    if (!width || !height) return;
    const aspect = width / height;
    const half = Math.max(1.04, 3.68 / aspect);
    camera.left = -half * aspect; camera.right = half * aspect;
    camera.top = half; camera.bottom = -half;
    camera.updateProjectionMatrix();
    r.setSize(width, height, false);
    render();
  });
  observer.observe(host);

  r.domElement.addEventListener('pointerdown', (e) => { px = e.clientX; py = e.clientY; });
  r.domElement.addEventListener('pointerup', (e) => {
    if (!mesh || Math.hypot(e.clientX - px, e.clientY - py) > 5 || e.button !== 0) return;
    const box = r.domElement.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(2 * (e.clientX-box.left)/box.width-1, 1-2*(e.clientY-box.top)/box.height), camera);
    const hit = ray.intersectObject(mesh, false)[0];
    if (hit) onPick(structure.cellAt[hit.faceIndex]);
  });
  host.addEventListener('keydown', (e) => {
    const angle = .13;
    if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)) return;
    e.preventDefault();
    const offset = camera.position.clone().sub(controls.target);
    const spherical = new THREE.Spherical().setFromVector3(offset);
    if (e.key === 'ArrowLeft') spherical.theta -= angle;
    if (e.key === 'ArrowRight') spherical.theta += angle;
    if (e.key === 'ArrowUp') spherical.phi -= angle;
    if (e.key === 'ArrowDown') spherical.phi += angle;
    camera.position.copy(new THREE.Vector3().setFromSpherical(spherical.makeSafe()).add(controls.target));
    controls.update();
  });

  function configure(data) {
    if (structure === data) return;
    structure = data;
    if (mesh) {
      scene.remove(mesh, wire, rest, outline);
      mesh.geometry.dispose();
      rest.geometry.dispose();
      outline.geometry.dispose();
    }
    const surface = new THREE.BufferGeometry();
    for (const name of ['position','color']) surface.setAttribute(name,
      new THREE.BufferAttribute(new Float32Array(data.tri.length * 3), 3).setUsage(THREE.DynamicDrawUsage));
    mesh = new THREE.Mesh(surface, material);
    wire = new THREE.Mesh(surface, wireMaterial);
    const indexed = new THREE.BufferGeometry();
    const xyz = new Float32Array(data.xyz.length);
    for (let i = 0; i < xyz.length; i += 3) {
      xyz[i] = data.xyz[i]-3; xyz[i+1] = data.xyz[i+2]; xyz[i+2] = -data.xyz[i+1];
    }
    indexed.setAttribute('position', new THREE.BufferAttribute(xyz, 3));
    indexed.setIndex(new THREE.BufferAttribute(data.tri, 1));
    rest = new THREE.LineSegments(new THREE.EdgesGeometry(indexed, 29), restMaterial);
    indexed.dispose();
    outline = new THREE.LineSegments(new THREE.BufferGeometry(), outlineMaterial);
    outline.renderOrder = 10;
    scene.add(mesh, wire, rest, outline);
  }

  function highlight(selected) {
    if (!outline) return;
    outline.geometry.dispose();
    outline.geometry = new THREE.BufferGeometry();
    if (selected == null) return;
    const source = mesh.geometry.getAttribute('position').array;
    const points = [];
    for (let tri=0; tri<structure.cellAt.length; tri++) {
      if (structure.cellAt[tri] !== selected) continue;
      const offset = tri * 9;
      for (const i of [0,1,1,2,2,0]) points.push(...source.subarray(offset+i*3,offset+i*3+3));
    }
    outline.geometry.setAttribute('position', new THREE.Float32BufferAttribute(points,3));
  }

  function update(data, frame, part, state, domain, cell) {
    configure(data);
    const pos = mesh.geometry.getAttribute('position');
    const rgb = mesh.geometry.getAttribute('color');
    const bases = data.xyz, ix = data.tri, u = frame.u;
    const lookup = state.field === 'strain' ? diverge : colors;
    const [lo,hi] = domain;
    for (let k = 0; k < ix.length; k++) {
      const point = ix[k]*3, i = k*3;
      pos.array[i] = bases[point] - 3 + state.scale*u[point];
      pos.array[i+1] = bases[point+2] + state.scale*u[point+2];
      pos.array[i+2] = -(bases[point+1] + state.scale*u[point+1]);
      const c = data.cellAt[Math.floor(k/3)];
      if (state.field === 'partition') brush.copy(ranks[part[c] % ranks.length]);
      else if (state.field === 'geometry') brush.set('#8eb8d5');
      else {
        const v = state.field === 'displacement' ? 1000*Math.hypot(u[point],u[point+1],u[point+2]) : frame[state.field][c];
        const index = Math.max(0, Math.min(lookup.length-1, (v-lo)/(hi-lo)*(lookup.length-1)));
        const lower = Math.floor(index);
        brush.copy(lookup[lower]).lerp(lookup[Math.min(lower+1,lookup.length-1)],index-lower);
      }
      if (c === cell) brush.lerp(ink,.3);
      rgb.setXYZ(k,brush.r,brush.g,brush.b);
    }
    pos.needsUpdate = true;
    rgb.needsUpdate = true;
    mesh.geometry.computeVertexNormals();
    mesh.geometry.computeBoundingSphere();
    wire.visible = state.wire;
    rest.visible = state.ghost;
    loadDiagram.visible = state.gravity != null;
    if (loadDiagram.visible) {
      const fraction = Number(state.gravity)/30;
      for(const arrow of loadArrows) {
        arrow.visible = fraction > 0;
        const length = .12+.56*fraction;
        arrow.position.y = .27+length;
        arrow.setLength(length, Math.min(.15,length*.6), .1);
      }
    }
    highlight(cell);
    render();
  }

  function setDomains(data) {
    const packed = Array.from({length:data.centers.length/3},()=>[]);
    for(let n=0;n<data.ranks.length;n++) for(let j=0;j<3;j++) {
      const offset = 3*data.tri[n*3+j];
      packed[data.ranks[n]].push(data.xyz[offset]-3,data.xyz[offset+2],-data.xyz[offset+1]);
    }
    const order = packed.map((_,i)=>i).sort((a,b)=>data.centers[3*a]-data.centers[3*b]);
    domains = packed.map((vertices,rank)=>{
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
      geometry.computeVertexNormals();
      const model = new THREE.Mesh(geometry,new THREE.MeshLambertMaterial({color:ranks[rank]}));
      scene.add(model);
      const band = order.indexOf(rank) / Math.max(1,order.length-1) - .5;
      const angle = order.indexOf(rank)*2.4;
      return {model,offset:new THREE.Vector3(band*2.65,Math.sin(angle)*.58,Math.cos(angle)*.34)};
    });
    render();
  }

  return {update,setDomains,
    spread(fraction) {
      for(const {model,offset} of domains) model.position.copy(offset).multiplyScalar(fraction);
      render();
    },
    sync(other,target) {
      syncing = true;
      camera.position.copy(other.position);
      camera.zoom = other.zoom;
      camera.updateProjectionMatrix();
      controls.target.copy(target);
      controls.update();
      syncing = false;
      render();
    },
    preset(mode) {
      const positions = {orbit:[3.9,2.6,7.5],side:[0,0,8],end:[8,0,.02],
        detail:[-1.25,1.05,4],spread:[3.9,2.6,7.5]};
      controls.target.set(mode==='end' ? 2.85 : mode==='detail' ? -2.3 : 0,0,0);
      camera.position.set(...positions[mode]);
      camera.zoom = mode==='end' ? 5.5 : mode==='detail' ? 4.4 : mode==='spread' ? .78 : 1;
      camera.updateProjectionMatrix();
      controls.update();
      onCamera(camera, controls.target);
      render();
    }
  };
}
