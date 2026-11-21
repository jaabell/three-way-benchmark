import assert from 'node:assert/strict';
import { mkdir, readFile } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import { chromium } from 'playwright-core';

const target = process.env.EXPLORER_URL || 'http://127.0.0.1:8865/dist/';
const args = ['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'];
const bin = process.env.CHROMIUM_PATH || '/usr/bin/chromium';
const browser = await chromium.launch({executablePath:bin,headless:true,args});
const output = new URL('../artifacts/',import.meta.url);
await mkdir(output,{recursive:true});
const manifest=JSON.parse(await readFile(new URL('../data/manifest.json',import.meta.url)));
const errs=[];
function monitor(page){
  page.on('pageerror',e=>errs.push(String(e)));
  page.on('response',r=>{if(r.status()>=400)errs.push(`${r.status()} ${r.url()}`);});
}
try {
  const page=await browser.newPage({viewport:{width:1920,height:1080}});
  monitor(page);
  await page.goto(target,{waitUntil:'networkidle'});
  const go=async (id)=>{
    await page.selectOption('#slide-picker',id);
    await page.waitForSelector(`body[data-slide="${id}"]`);
  };
  const capture=async (name)=>{
    await page.evaluate(()=>document.activeElement.blur());
    await page.keyboard.press('h');
    assert(await page.locator('body').evaluate(el=>el.classList.contains('clean')));
    await page.screenshot({path:new URL(`${name}.png`,output).pathname,animations:'disabled'});
    await page.keyboard.press('Escape');
    assert(!(await page.locator('body').evaluate(el=>el.classList.contains('clean'))));
  };
  await page.waitForSelector('#slide-picker option:nth-child(11)',{state:'attached'});
  assert.match(await page.locator('#solvers').innerText(),/Three solvers/);
  assert.equal(await page.locator('.logo-well img').count(),3);
  await capture('slides-01-solvers');
  await page.click('#next-slide');
  await page.waitForSelector('body[data-slide="machines"]');
  assert.match(await page.locator('#machines').innerText(),/Ryzen 9 5950X/);
  await capture('slides-02-hardware');
  await go('geometry');
  await page.waitForSelector('#geometry-view[data-load="15"]');
  await page.click('#geometry-play');
  await page.waitForSelector('#geometry-view[data-load="30"]');
  assert.match(await page.locator('#geometry-force').innerText(),/206\.5 kN/);
  await capture('slides-03-load');
  await go('meshes');
  await page.waitForSelector('#mesh-fine[data-ready="true"]');
  await page.click('#mesh-detail');
  await capture('slides-04-mesh');
  await go('partitions');
  await page.waitForSelector('#part-fine[data-separation="0"]');
  const assembled=await page.locator('#part-fine canvas').screenshot();
  await page.click('#explode-play');
  await page.waitForSelector('#part-fine[data-separation="100"]');
  assert.notDeepEqual(await page.locator('#part-fine canvas').screenshot(),assembled);
  await capture('slides-05-partitions');
  await page.click('#partition-reset');
  await page.waitForSelector('#part-fine[data-separation="0"]');
  await go('fields');
  await page.waitForSelector('#view-a[data-load="29"][data-run="os-fine"]');
  await page.waitForSelector('#view-b[data-load="29"][data-run="fx-fine"]');
  assert.match(await page.locator('#tip-a').innerText(),/78\.839/);
  assert.match(await page.locator('#load-readout').innerText(),/199\.58/);
  assert.equal(await page.locator('meta[name=robots]').getAttribute('content'),'noindex, nofollow, noarchive');
  await capture('slides-06-fields');

  for(const key of ['displacement','strain','plastic','elastic','dissipation','partition','stress']){
    await page.selectOption('#field',key);
    await page.waitForSelector(`#view-a[data-field="${key}"]`);
    await page.waitForSelector(`#view-b[data-field="${key}"]`);
    assert((await page.locator('#legend-title').innerText()).length>5);
  }
  const info=manifest.meshes.fine;
  const geo=gunzipSync(await readFile(new URL('../data/fine.bin.gz',import.meta.url)));
  const idx=geo.readUInt32LE(4*(info.points*3+info.triangles*4));
  await page.fill('#element',String(idx));
  await page.click('#inspect button');
  assert.match(await page.locator('#inspect-readout').innerText(),new RegExp(`element ${idx} · MPI rank`));

  const before=await page.locator('#view-b canvas').screenshot();
  await page.focus('#view-a');
  await page.keyboard.press('ArrowRight');
  const moved=await page.locator('#view-b canvas').screenshot();
  assert(!before.equals(moved),'keyboard camera adjustment must move both views');
  await page.click('#camera-end');
  await page.click('#camera-orbit');

  for(const run of manifest.runs) {
    await page.selectOption('#run-a',run.id);
    await page.waitForSelector(`#view-a[data-run="${run.id}"]`);
  }
  await page.selectOption('#run-b','fx-smoke');
  await page.waitForSelector('#view-b[data-run="fx-smoke"]');
  assert.equal(await page.locator('#load').getAttribute('max'),'30');
  await page.fill('#load','30');
  await page.waitForSelector('#view-a[data-load="30"]');
  assert.match(await page.locator('#tip-a').innerText(),/127\.528/);
  await page.selectOption('#scale','5');
  await page.check('#wire');
  await page.uncheck('#wire');
  await page.click('#reset-load');
  await page.waitForSelector('#view-a[data-load="0"]');
  assert.match(await page.locator('#tip-a').innerText(),/0\.000/);
  await page.click('#play');
  await page.waitForFunction(()=>Number(document.querySelector('#view-a').dataset.load)>0);
  await page.click('#play');
  assert.equal(await page.locator('#play').getAttribute('aria-pressed'),'false');
  await go('curves');
  assert.equal(await page.locator('#curve-legend .series-key').count(),9);
  await page.selectOption('#curve-mode','fx-gpu');
  assert.equal(await page.locator('#curve-legend .series-key').count(),3);
  await page.selectOption('#curve-mode','all');
  await capture('slides-07-curves');
  await page.click('[data-chart=energy]');
  assert.match(await page.locator('#plot').textContent(),/Energy/);
  await go('performance');
  assert.equal(await page.locator('#timings tbody tr').count(),5);
  assert.match(await page.locator('#timings').innerText(),/111\.45/);
  await capture('slides-08-cpu');
  await page.click('[data-mesh=smoke]');
  assert.match(await page.locator('#timings').innerText(),/12\.53/);
  await page.selectOption('#timing-metric','bytes');
  assert.match(await page.locator('#timings').innerText(),/105\./);
  await go('gpu');
  await page.click('#gpu-replay');
  assert(await page.locator('#gpu-pipeline').evaluate(el=>el.classList.contains('flow')));
  await capture('slides-09-workflow');
  await go('gpu-results');
  assert.match(await page.locator('#gpu-timings').innerText(),/310\.04/);
  await capture('slides-10-gpu');
  await go('conclusions');
  assert.match(await page.locator('#conclusions').innerText(),/191\.98/);
  await capture('slides-11-conclusions');
  assert.equal(new URL(page.url()).hash,'#conclusions');
  await page.goBack();
  await page.waitForSelector('body[data-slide="gpu-results"]');
  await page.close();

  const mobile=await browser.newPage({viewport:{width:390,height:844},isMobile:true,deviceScaleFactor:1,hasTouch:true,reducedMotion:'reduce'});
  monitor(mobile);
  await mobile.goto(new URL('#fields',target).href,{waitUntil:'networkidle'});
  await mobile.waitForSelector('#view-b[data-load="29"]');
  assert(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await mobile.screenshot({path:new URL('mobile.png',output).pathname,fullPage:true});
  await mobile.close();

  const embed=await browser.newPage({viewport:{width:768,height:1024}});
  monitor(embed);
  const wrapper = new URL('iframe-validation.html',target).href;
  await embed.route(wrapper,route=>route.fulfill({contentType:'text/html',body:
    `<!doctype html><title>Embed test</title><iframe title="Beam" src="${new URL('#fields',target).href}" style="width:100%;height:650px"></iframe>`}));
  await embed.goto(wrapper);
  await embed.frameLocator('iframe').locator('#view-a[data-load="29"]').waitFor();
  await embed.close();

  const fallbackBrowser=await chromium.launch({executablePath:bin,headless:true,args:[...args,'--disable-webgl']});
  const fallback=await fallbackBrowser.newPage();
  monitor(fallback);
  await fallback.goto(new URL('#fields',target).href);
  await fallback.locator('#fallback').waitFor();
  await fallback.selectOption('#slide-picker','performance');
  assert.match(await fallback.locator('#timings').innerText(),/111\.45/);
  await fallbackBrowser.close();

  assert.deepEqual(errs,[]);
  console.log('PASS desktop, all seven run selectors and fields, paired keyboard camera, element inspector, timeline, plots, timing tables, presentation, mobile, iframe, WebGL fallback, and no failed HTTP responses');
} finally {
  await browser.close();
}
