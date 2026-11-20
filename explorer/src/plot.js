const ns = 'http://www.w3.org/2000/svg';
const make = (name, attrs={}, label='') => {
  const el = document.createElementNS(ns,name);
  for (const [k,v] of Object.entries(attrs)) el.setAttribute(k,v);
  if (label) el.textContent = label;
  return el;
};
export const curveColors = ['#a64e26','#14757d'];

export function makePlot(svg, legend, onSelect) {
  let geometry, source;
  const text = (x,y,value,props={}) => make('text',{x,y,...props},value);

  function draw(data) {
    source = data;
    const {runs, kind, step, theory, reference} = data;
    const w = Math.max(300, Math.floor(svg.clientWidth));
    const h = Math.max(245, Math.floor(svg.clientHeight));
    svg.setAttribute('viewBox',`0 0 ${w} ${h}`);
    const f = kind==='force', left=61, top=16, right=w-18, bottom=h-49;
    const force = theory.reference_weight_N / 1000;
    const area = f ? [
      Math.ceil(Math.max(...runs.map(c => c.traces.at(-1)[1]),reference.at(-1)[0])/20)*20,
      Math.ceil(Math.max(...runs.map(c => c.traces.at(-1)[0]*force),theory.plastic_force_N/1000)/25)*25
    ] : [30, Math.ceil(Math.max(...runs.flatMap(r=>r.traces.map(t=>t[4])))/2)*2];
    const X = (x) => left + x/area[0]*(right-left);
    const Y = (y) => bottom - y/area[1]*(bottom-top);
    svg.replaceChildren();
    for (let i=0;i<=5;i++) {
      const x=area[0]*i/5, y=area[1]*i/5, gx=X(x), gy=Y(y);
      svg.append(make('line',{x1:gx,x2:gx,y1:top,y2:bottom,stroke:'#e5e5dc'}),
        make('line',{x1:left,x2:right,y1:gy,y2:gy,stroke:'#e5e5dc'}),
        text(gx,bottom+18,Number(x.toFixed(1)).toString(),{'text-anchor':'middle'}),
        text(left-9,gy+4,Number(y.toFixed(1)).toString(),{'text-anchor':'end'}));
    }
    svg.append(make('path',{d:`M ${left} ${top} V ${bottom} H ${right}`,stroke:'#727f77',fill:'none'}),
      text((left+right)/2,h-8,f?'Downward tip displacement [mm]':'Gravity multiplier [×g]',{'text-anchor':'middle',class:'axis-title'}),
      text(16,(top+bottom)/2,f?'Applied weight [kN]':'Energy [kJ]',{'text-anchor':'middle',transform:`rotate(-90 16 ${(top+bottom)/2})`,class:'axis-title'}));
    const specs = [];
    function stroke(points,color,label,dash='',width=2.1) {
      const path=points.map((p,i)=>`${i?'L':'M'}${X(p[0]).toFixed(2)},${Y(p[1]).toFixed(2)}`).join(' ');
      svg.append(make('path',{d:path,stroke:color,'stroke-width':width,'stroke-dasharray':dash,fill:'none','stroke-linejoin':'round'}));
      if(label) specs.push([color,label,dash]);
    }
    if(f) {
      const limit=theory.plastic_force_N/1000;
      stroke([[0,limit],[area[0],limit]],'#6a736d','Plastic limit','5 4',1.1);
      stroke(reference,'#696c81','Euler–Bernoulli','',1.9);
    }
    geometry = [];
    runs.forEach((run,slot)=>{
      const color=curveColors[slot], letter=slot?'B':'A';
      const series=f ? [[1,`${letter} · ${run.solver}`,slot?'4 3':'']] :
        [[4,`${letter} · work`,slot?'5 3':''],[2,`${letter} · elastic`,'1.5 3'],[3,`${letter} · plastic`,'8 3 2 3']];
      for(const [key,label,dash] of series) {
        const points = run.traces.map(t=>f?[t[key],t[0]*force]:[t[0],t[key]]);
        stroke(points,color,label,dash);
        if (key===1||key===4) {
          geometry.push(points.map(([x,y])=>[X(x),Y(y)]));
          const current=points[step];
          if(current) svg.append(make(slot?'rect':'circle',slot
            ? {x:X(current[0])-4,y:Y(current[1])-4,width:8,height:8,fill:color,stroke:'#faf9f3','stroke-width':1}
            : {cx:X(current[0]),cy:Y(current[1]),r:5,fill:color,stroke:'#faf9f3','stroke-width':1.2}));
        }
      }
    });
    legend.replaceChildren(...specs.map(([color,label,dash]) => {
      const key=document.createElement('span');
      key.className='series-key';
      const icon=make('svg',{viewBox:'0 0 20 10','aria-hidden':'true'});
      icon.append(make('line',{x1:0,y1:5,x2:20,y2:5,stroke:color,'stroke-width':2,'stroke-dasharray':dash}));
      key.append(icon,document.createTextNode(label));
      return key;
    }));
  }
  svg.addEventListener('click',(event)=>{
    const box=svg.getBoundingClientRect();
    const x=event.clientX-box.x,y=event.clientY-box.y;
    let distance=Infinity, step=0;
    for(const curve of geometry??[]) curve.forEach(([a,b],i)=>{
      if(i>Math.min(...source.runs.map(r=>r.traces.length-1))) return;
      const d=Math.hypot(x-a,y-b);
      if(d<distance){distance=d;step=i;}
    });
    if(distance<=55) onSelect(step);
  });
  new ResizeObserver(()=>{if(source)draw(source);}).observe(svg);
  return draw;
}
