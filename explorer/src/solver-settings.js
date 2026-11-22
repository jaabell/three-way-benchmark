const $ = (id) => document.getElementById(id);
const cpuOptions = [
  {
    id: 'opensees',
    name: 'OpenSeesMP',
    layout: 'ParallelRCM · distributed assembled coordinate triplets (row, column, value). Rank 0 sums the right-hand side and sends back the solution.',
    solve: 'Newton + LoadControl. Plain constraints. MUMPS sparse multifrontal direct solve.'
  },
  {
    id: 'kratos',
    name: 'Kratos',
    layout: 'In-memory METIS partitioning. Trilinos block builder assembles a row-distributed Epetra sparse CRS matrix.',
    solve: 'Static incremental Newton. Amesos_Mumps. Absolute criterion adjusted for Kratos’s free-DOF residual normalization.'
  },
  {
    id: 'fenicsx',
    name: 'FEniCSx',
    layout: 'PETSc MPIAIJ · row-owned CSR with local and off-rank column blocks. Ghost residual contributions are summed before applying the clamp.',
    solve: 'UFL-consistent tangent and explicit Newton loop. PETSc preonly + LU (MUMPS).'
  }
];

const gpuReference = {
  id:'mumps', name:'CPU MUMPS',
  layout:'One PETSc SeqAIJ matrix and right-hand side on the host.',
  solve:'Same FEniCSx Newton loop as CUDA. PETSc preonly + LU (MUMPS).'
};
const gpuOptions = {
  qr:{id:'cuda-qr',name:'RTX 5090 · sparse QR',
      layout:'Host SeqAIJ → CSR arrays with 32-bit indices and FP64 values → one GPU.',
      solve:'JAX cuSOLVER sparse QR. METIS nested dissection (reorder = 3). Singularity tolerance 10⁻¹².'},
  cg:{id:'cuda-cg',name:'RTX 5090 · CG',
      layout:'Host SeqAIJ → CSR arrays and matrix diagonal → one GPU. FP64 values and 32-bit CSR indices.',
      solve:'Jacobi-preconditioned conjugate gradients. Up to 200,000 iterations with true relative residual accepted below 10⁻⁵.'}
};

function cell(row, value, heading=false) {
  const element = document.createElement(heading?'th':'td');
  if(heading) element.scope='row';
  element.textContent=value;
  row.append(element);
  return element;
}

function memoryCell(row, samples, key, selection, label, missing) {
  const byJob = [...samples].sort((a,b)=>a.job-b.job);
  const chosen = selection==='median' ? byJob :
    [byJob.find(sample=>sample.repeat===Number(selection)) ?? byJob[Number(selection)-1]].filter(Boolean);
  const values = chosen.map(sample=>sample[key]).filter(Number.isFinite).sort((a,b)=>a-b);
  const gib = (kib) => (kib / 1048576).toFixed(2);
  if(!values.length) {
    cell(row,missing);
    return;
  }
  const mid=Math.floor(values.length/2);
  const median=values.length%2 ? values[mid] : (values[mid-1]+values[mid])/2;
  const main=cell(row,`${gib(median)} GiB`);
  main.className='memory-value';
  const info=document.createElement('small');
  const labelText=selection==='median'
    ? `${label} · ${values.length}/${chosen.length} samples`
    : `Job ${chosen[0].job}`;
  info.textContent=labelText;
  main.append(info);
  main.title=chosen.filter(sample=>Number.isFinite(sample[key]))
    .map(sample=>`Job ${sample.job}: ${gib(sample[key])} GiB`).join(' • ');
}

export function setupSolverSettings(read) {
  let data, request, mode='cpu';
  const table=$('settings-table');
  function render() {
    if(!data)return;
    const gpu=mode==='gpu';
    $('settings-cpu').hidden=gpu;
    $('settings-gpu').hidden=!gpu;
    const head=document.createElement('thead');
    const heading=head.insertRow();
    const names=['Solver','SOE and matrix layout','Solve and options',gpu?'Host task RSS':'Peak rank RSS'];
    if(gpu)names.push('GPU VRAM');
    names.forEach(name=>{cell(heading,name,true).scope='col';});
    const body=document.createElement('tbody');
    const mesh=$('settings-mesh').value;
    const [ranks,transport]=$('settings-ranks').value.split(':');
    const host=transport==='default'?'node13':'node12 + node13';
    const output=$('settings-output').value;
    const profile=$('settings-profile').value;
    const repeat=$('settings-repeat').value;
    const fine=profile==='fine-elastic';
    for(const option of gpu ? [gpuReference,gpuOptions[fine?'cg':'qr']] : cpuOptions) {
      const row=body.insertRow();
      cell(row,option.name,true);
      cell(row,option.layout);
      cell(row,option.solve);
      if(gpu) {
        const records=data.gpu.filter(r=>r.case===profile && r.solver===option.id);
        memoryCell(row,records,'hostKiB',repeat,'host task','Unavailable');
        memoryCell(row,records,'deviceKiB',repeat,'device high-water',option.id==='mumps'?'CPU solve':'Unrecorded');
      } else {
        const records=data.cpu.filter(r=>r.mesh===mesh && r.solver===option.id &&
          r.ranks===Number(ranks) && r.transport===transport && r.output===output);
        memoryCell(row,records,'hostKiB',repeat,'peak rank',transport==='default'?'Unavailable':'Launcher only');
      }
    }
    table.replaceChildren(head,body);
    $('settings-case').textContent=gpu
      ? `${fine?'350,343 rows · 26,472,609 stored entries · 2 elastic steps · Minimal output':'39,123 rows · 2,819,799 stored entries · '+(profile==='smoke-elastic'?'2 elastic steps':'30 nonlinear steps')+' · Full output'} · One MPI rank`
      : `${host} · ${mesh==='fine'?'Fine · 29':'Coarse · 30'} gravity increments · Newton residual target 0.1 N · 18 iteration cap · One thread per rank`;
    const usesFullOutput = gpu ? !fine : output==='full';
    $('settings-case').title = usesFullOutput
      ? 'Full output writes displacements and integration-point stresses and strains after each increment.'
      : 'Minimal output records convergence, timings, and tip displacement.';
    $('settings-memory-note').textContent=gpu
      ? 'Slurm peak memory from the solver step. Short runs can miss VRAM sampling.'
      : transport==='default'
        ? 'Slurm MaxRSS is the peak of the largest accounted rank in the solver step. It measures host resident memory, including assembly and the solve.'
        : 'Slurm monitored PRRTE launcher tasks for the two-node cases. Per-solver-rank peak RSS is unavailable for this comparison.';
  }
  for(const button of document.querySelectorAll('[data-settings-mode]')) button.addEventListener('click',()=>{
    mode=button.dataset.settingsMode;
    for(const candidate of document.querySelectorAll('[data-settings-mode]'))
      candidate.setAttribute('aria-pressed',String(candidate===button));
    render();
  });
  for(const id of ['settings-mesh','settings-ranks','settings-output','settings-repeat','settings-profile'])
    $(id).addEventListener('change',render);
  return async () => {
    try {
      request??=read('./assets/solver-memory.json?v=node13').catch(error=>{request=null;throw error;});
      data=await request;
      render();
    } catch {
      $('settings-memory-note').textContent='The solver records could not be loaded.';
    }
  };
}
