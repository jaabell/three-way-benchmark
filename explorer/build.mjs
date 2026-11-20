import { build } from 'esbuild';
import { cp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
process.chdir(root);
const manifest = JSON.parse(await readFile('data/manifest.json','utf8'));
if (manifest.runs.length !== 7 || manifest.timings.length !== 60) throw Error('Incomplete explorer data');
await mkdir('dist',{recursive:true});
await cp('src/assets','dist/assets',{recursive:true});
await cp('data','dist/data',{recursive:true});
await cp('src/index.html','dist/index.html');
await cp('src/style.css','dist/style.css');
await cp('node_modules/three/LICENSE','dist/assets/three-LICENSE.txt');
await build({absWorkingDir:root,entryPoints:['src/app.js'],outfile:'dist/app.js',bundle:true,minify:true,format:'esm',target:'es2022'});
await writeFile('dist/.nojekyll','');
