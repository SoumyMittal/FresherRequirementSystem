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
  await page.getByRole('button', {name:'Show password'}).click();
  if (await page.locator('#password').getAttribute('type') !== 'text') throw new Error('Password visibility did not change');
  await page.getByRole('button', {name:'Hide password'}).click();
  await page.setViewportSize({width:390,height:844});
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Login overflows at mobile width');
  await page.screenshot({path:'test-results/login-mobile.png', fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
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
  await page.getByRole('dialog').getByLabel('HR decision', {exact:true}).selectOption('Reviewed');
  await page.getByRole('button', {name:'Save decision'}).click();
  await page.request.patch('/api/candidates/' + candidateId + '/review', {data:{status:originalCandidate.review}});
  await page.getByRole('button', {name:'Close dialog'}).click();
  await page.getByRole('button', {name:'Run segmentation'}).click();
  await page.getByRole('button', {name:'Run segmentation'}).waitFor();
  await page.screenshot({path:'test-results/talent-desktop.png',fullPage:true});

  await page.getByRole('link', {name:'Open positions'}).click();
  await page.getByRole('heading', {name:'The right opportunity matters.'}).waitFor();
  await page.getByRole('button', {name:'Create position'}).click();
  const title = 'Browser QA Position ' + Date.now();
  await page.getByLabel('Position title').fill(title);
  await page.getByLabel('Required skills').fill('Python, SQL');
  await page.getByLabel('Number of openings').fill('1');
  if (!(await page.locator('#job-capacity').textContent()).includes('capacity: 4')) throw new Error('Default capacity missing');
  const ratio = page.getByLabel('Shortlisting Ratio (candidates per opening)');
  await ratio.fill('0');
  if (await ratio.evaluate(input => input.validity.valid)) throw new Error('Zero ratio was accepted');
  await ratio.fill('2.125');
  if (!(await page.locator('#job-capacity').textContent()).includes('capacity: 3')) throw new Error('Capacity preview was stale');
  await page.getByRole('button', {name:'Save position',exact:true}).click();
  const position = page.locator('.job-card').filter({hasText:title});
  await position.getByText('Shortlist capacity · 3').waitFor();
  await position.getByRole('button',{name:'Edit',exact:true}).click();
  if (await ratio.inputValue() !== '2.125') throw new Error('Ratio was not persisted');
  await page.keyboard.press('Escape');
  if (!await position.getByRole('button',{name:'Edit',exact:true}).evaluate(button => button === document.activeElement)) throw new Error('Dialog did not restore keyboard focus');
  await page.screenshot({path:'test-results/positions-desktop.png',fullPage:true});

  await page.getByRole('link', {name:'Resume studio'}).click();
  await page.getByRole('heading', {name:'Every resume has a story.'}).waitFor();
  await page.locator('#upload-job').selectOption('');
  await page.getByRole('button', {name:'Extract resume'}).click();
  if (!(await page.locator('#toast').textContent()).includes('Choose a position')) throw new Error('Upload validation did not run');
  await page.screenshot({path:'test-results/studio-desktop.png',fullPage:true});

  await page.getByRole('link', {name:'Reports'}).click();
  await page.getByRole('heading', {name:'See the bigger picture.'}).waitFor();
  const exportResponse = await page.request.get('/api/export');
  if (!exportResponse.ok() || !exportResponse.headers()['content-type'].includes('text/csv')) throw new Error('Report CSV export failed');
  await page.evaluate(() => document.querySelector('#toast').className = '');
  await page.screenshot({path:'test-results/reports-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/reports-mobile.png',fullPage:true});
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Page overflows at mobile width');
  await page.getByLabel('Open navigation').click();
  if (await page.locator('#menu').getAttribute('aria-expanded') !== 'true') throw new Error('Drawer did not expose its open state');
  await page.keyboard.press('Escape');
  if (!(await page.locator('#menu').evaluate(element => element === document.activeElement))) throw new Error('Drawer did not restore focus');
  await page.getByLabel('Open navigation').click();
  await page.getByRole('link', {name:'Overview',exact:true}).click();
  await page.getByRole('heading', {name:'A fresh start. A better fit.'}).waitFor();
  await page.screenshot({path:'test-results/overview-mobile.png',fullPage:true});
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Dashboard overflows at mobile width');
  for (const [hash, heading] of [['shortlist', 'HR Shortlist'], ['general-pool', 'General Candidate Pool'], ['data-review', 'Need Data Review']]) {
    await page.evaluate(hash => { location.hash = hash; }, hash);
    await page.getByRole('heading', {name:heading, exact:true}).waitFor();
    await page.locator('#candidate-results .table-footer').waitFor();
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(heading + ' overflows at mobile width');
  }
  for (const width of [768, 1024]) {
    await page.setViewportSize({width, height:900});
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Candidate directory overflows at ' + width);
  }
  if(errors.length) throw new Error(errors.join('\n'));
  console.log('PASS: mocked login, all five views, candidate filtering, model inference, bulk segmentation, HR review, job form, upload validation, and mobile layout.');
} finally {
  await browser.close();
}
