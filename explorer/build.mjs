import { build } from 'esbuild';
import { cp, mkdir, readdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
process.chdir(root);
const manifest = JSON.parse(await readFile('data/manifest.json','utf8'));
if (manifest.runs.length !== 7 || manifest.timings.length !== 60) throw Error('Incomplete explorer data');
const partitions = JSON.parse(await readFile('data/partitions.json','utf8'));
if (partitions.coarse.ranks !== 4 || partitions.fine.ranks !== 16) throw Error('Incomplete MPI partitions');
const tensors = JSON.parse(await readFile('data/tensor-fields.json','utf8'));
for (const run of manifest.runs) {
  const files = new Set(await readdir(`data/${run.id}`));
  if (tensors.fields.length !== 12 || tensors.frames[run.id] !== run.traces.length-1 ||
      run.traces.slice(1).some(([step])=>!files.has(`tensor-${String(step).padStart(2,'0')}.bin.gz`))) {
    throw Error(`Incomplete tensor fields for ${run.id}`);
  }
}
await mkdir('dist',{recursive:true});
await cp('src/assets','dist/assets',{recursive:true});
await cp('data','dist/data',{recursive:true});
await cp('src/index.html','dist/index.html');
await cp('src/style.css','dist/style.css');
await cp('node_modules/three/LICENSE','dist/assets/three-LICENSE.txt');
await build({absWorkingDir:root,entryPoints:['src/app.js'],outfile:'dist/app.js',bundle:true,minify:true,format:'esm',target:'es2022'});
await writeFile('dist/.nojekyll','');
