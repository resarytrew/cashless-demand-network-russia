import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const port=8766;
const server=spawn(process.env.PYTHON || 'python',['-m','http.server',String(port),'--bind','127.0.0.1','--directory','site'],{cwd:root,windowsHide:true,stdio:'ignore'});
let browser;
try {
  let ready=false;
  for(let i=0;i<80;i++) {try {const r=await fetch(`http://127.0.0.1:${port}`);if(r.ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}
  if(!ready)throw Error('PDF preview server did not start');
  browser=await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHANNEL} : {})});
  const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  await page.goto(`http://127.0.0.1:${port}`,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.researchReady);
  await page.evaluate(()=>window.prepareResearchPrint());
  await page.emulateMedia({media:'print'});
  await mkdir(path.join(root,'site/assets'),{recursive:true});
  await page.pdf({path:path.join(root,'site/assets/research-brief.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="font:8px Arial;width:100%;text-align:center;color:#627165">География спроса · <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
  await page.emulateMedia({media:'screen'});
  await page.goto(`http://127.0.0.1:${port}`,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.researchReady);await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:path.join(root,'site/assets/social-cover.png')});
  console.log('PDF and social cover exported from the live research page.');
} finally {await browser?.close();server.kill();}
