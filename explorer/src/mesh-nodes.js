// prepare.py writes the four children of each exterior T6 face consecutively.
function faceAt(triangles, offset) {
  return [
    triangles[offset], triangles[offset+4], triangles[offset+8],
    triangles[offset+9], triangles[offset+10], triangles[offset+11]
  ];
}

export function quadraticNodeRoles(mesh) {
  const roles = new Int8Array(mesh.xyz.length/3).fill(-1);
  for (let offset=0; offset<mesh.tri.length; offset+=12) {
    faceAt(mesh.tri,offset).forEach((point,i)=>{
      const role=i<3?0:1;
      if(roles[point]!==-1 && roles[point]!==role) throw Error('Inconsistent T10 node role');
      roles[point]=role;
    });
  }
  if(roles.includes(-1)) throw Error('Unclassified T10 surface node');
  return roles;
}

export function drawQuadraticFace(mesh, canvas) {
  const xyz = (point)=>Array.from(mesh.xyz.subarray(point*3,point*3+3));
  const difference = (a,b)=>a.map((value,i)=>value-b[i]);
  const dot = (a,b)=>a.reduce((sum,value,i)=>sum+value*b[i],0);
  let face, best=-1;
  for(let offset=0;offset<mesh.tri.length;offset+=12) {
    const nodes=faceAt(mesh.tri,offset);
    const corner=nodes.slice(0,3).map(xyz);
    if(corner.some(point=>point[0]>.65)) continue;
    const u=difference(corner[1],corner[0]), v=difference(corner[2],corner[0]);
    const uu=dot(u,u), vv=dot(v,v), uv=dot(u,v), w=difference(u,v);
    const quality=(uu*vv-uv*uv)/Math.max(uu,vv,dot(w,w))**2;
    if(quality>best) {
      face=nodes.map(xyz);
      best=quality;
    }
  }
  if(!face)return;
  const u=difference(face[1],face[0]), v=difference(face[2],face[0]);
  const axis=u.map(value=>value/Math.hypot(...u));
  const perpendicular=v.map((value,i)=>value-dot(v,axis)*axis[i]);
  const normal=perpendicular.map(value=>value/Math.hypot(...perpendicular));
  const points=face.map(point=>{
    const relative=difference(point,face[0]);
    return [dot(relative,axis),-dot(relative,normal)];
  });
  const lo=points.map(point=>point[0]), hi=points.map(point=>point[1]);
  const x0=Math.min(...lo), x1=Math.max(...lo), y0=Math.min(...hi), y1=Math.max(...hi);
  const {width,height}=canvas;
  const scale=Math.min((width-36)/(x1-x0),(height-26)/(y1-y0));
  const xy=points.map(([x,y])=>[width/2+scale*(x-(x0+x1)/2),height/2+scale*(y-(y0+y1)/2)]);
  const ctx=canvas.getContext('2d');
  ctx.clearRect(0,0,width,height);
  ctx.fillStyle='#182b44';
  ctx.strokeStyle='#a6c1d7';
  ctx.lineWidth=1.5;
  ctx.beginPath();
  xy.slice(0,3).forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));
  ctx.closePath();ctx.fill();ctx.stroke();
  xy.forEach(([x,y],i)=>{
    if(i<3){
      ctx.fillStyle='#f4f7ff';ctx.fillRect(x-4,y-4,8,8);
    } else {
      ctx.fillStyle='#ffb35e';ctx.beginPath();ctx.arc(x,y,5.4,0,2*Math.PI);ctx.fill();
    }
  });
}
