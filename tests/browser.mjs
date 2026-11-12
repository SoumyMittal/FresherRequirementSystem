import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

const browser = await chromium.launch({channel: 'msedge', headless: true});
const baseURL = process.env.SPROUT_TEST_URL || 'http://127.0.0.1:8000';
const page = await browser.newPage({baseURL, viewport: {width: 1440, height: 1100}, deviceScaleFactor: 1, reducedMotion:'reduce'});
const errors = [];
page.on('pageerror', error => errors.push(error.message));
await mkdir('test-results', {recursive:true});

try {
  await page.goto(baseURL);
  await page.getByRole('heading', {name:'Welcome to Incepta.'}).waitFor();
  await page.screenshot({path:'test-results/login-desktop.png', fullPage:true});
  await page.getByRole('button', {name:'Enter demo workspace'}).click();
  await page.getByRole('heading', {name:'A fresh start. A better fit.'}).waitFor();
  await page.screenshot({path:'test-results/overview-desktop.png', fullPage:true});

  await page.getByRole('link', {name:'Talent pool'}).click();
  await page.getByRole('heading', {name:'Candidate directory'}).waitFor();
  await page.locator('.view-candidate').first().waitFor();
  await page.getByLabel('Search candidates').fill('Python');
  await page.waitForTimeout(600);
  await page.getByLabel('Filter by position').selectOption('JOB_001');
  await page.waitForTimeout(600);
  const candidateId = await page.locator('.view-candidate').first().getAttribute('data-id');
  const originalCandidate = await (await page.request.get('/api/candidates/' + candidateId)).json();
  await page.locator('.view-candidate').first().click();
  await page.getByRole('button', {name:/^Run model(?: again)?$/}).click();
  await page.locator('.model-result').waitFor();
  await page.getByLabel('HR decision').selectOption('Reviewed');
  await page.getByRole('button', {name:'Save decision'}).click();
  await page.request.patch('/api/candidates/' + candidateId + '/review', {data:{status:originalCandidate.review}});
  await page.getByRole('button', {name:'Close dialog'}).click();
  await page.getByRole('button', {name:'Run segmentation'}).click();
  await page.getByRole('button', {name:'Run segmentation'}).waitFor();
  await page.screenshot({path:'test-results/talent-desktop.png',fullPage:true});

  await page.getByRole('link', {name:'Open positions'}).click();
  await page.getByRole('heading', {name:'The right opportunity matters.'}).waitFor();
  await page.getByRole('button', {name:'Create position'}).click();
  await page.getByLabel('Position title').fill('Browser QA Position');
  await page.getByLabel('Required skills').fill('Python, SQL');
  await page.getByRole('button', {name:'Cancel',exact:true}).click();
  await page.screenshot({path:'test-results/positions-desktop.png',fullPage:true});

  await page.getByRole('link', {name:'Resume studio'}).click();
  await page.getByRole('heading', {name:'Every resume has a story.'}).waitFor();
  await page.locator('#upload-job').selectOption('');
  await page.getByRole('button', {name:'Extract resume'}).click();
  if (!(await page.locator('#toast').textContent()).includes('Choose a position')) throw new Error('Upload validation did not run');
  await page.screenshot({path:'test-results/studio-desktop.png',fullPage:true});

  await page.getByRole('link', {name:'Reports'}).click();
  await page.getByRole('heading', {name:'See the bigger picture.'}).waitFor();
  await page.evaluate(() => document.querySelector('#toast').className = '');
  await page.screenshot({path:'test-results/reports-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/reports-mobile.png',fullPage:true});
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Page overflows at mobile width');
  await page.getByLabel('Open navigation').click();
  await page.getByRole('link', {name:'Overview',exact:true}).click();
  await page.getByRole('heading', {name:'A fresh start. A better fit.'}).waitFor();
  await page.screenshot({path:'test-results/overview-mobile.png',fullPage:true});
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Dashboard overflows at mobile width');
  if(errors.length) throw new Error(errors.join('\n'));
  console.log('PASS: mocked login, all five views, candidate filtering, model inference, bulk segmentation, HR review, job form, upload validation, and mobile layout.');
} finally {
  await browser.close();
}
