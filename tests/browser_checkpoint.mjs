import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import path from 'node:path';

const baseURL = process.env.SPROUT_TEST_URL || 'http://127.0.0.1:8002';
const browser = await chromium.launch({channel:'msedge', headless:true});
const page = await browser.newPage({baseURL, viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
const errors = [];
page.on('pageerror', error => errors.push(error.message));

function pdf(name, lines) {
  const commands = 'BT /F1 12 Tf 50 780 Td 16 TL ' + lines.map((line, index) =>
    (index ? 'T* ' : '') + '(' + line.replace(/[()\\]/g, '\\$&') + ') Tj').join('\n') + ' ET';
  const objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    '<< /Length ' + Buffer.byteLength(commands) + ' >>\nstream\n' + commands + '\nendstream'];
  let data = '%PDF-1.4\n';
  const offsets = objects.map((object, index) => {
    const offset = data.length;
    data += (index + 1) + ' 0 obj\n' + object + '\nendobj\n';
    return offset;
  });
  const xref = data.length;
  data += 'xref\n0 6\n0000000000 65535 f \n' + offsets.map(value => String(value).padStart(10, '0') + ' 00000 n \n').join('');
  data += 'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n' + xref + '\n%%EOF';
  return {name, mimeType:'application/pdf', buffer:Buffer.from(data)};
}

const shortlist = pdf('shortlist.pdf', [
  'Strong Candidate', 'strong@example.test', 'B.Sc Information Technology', 'CGPA: 9.8', 'Class 10 Percentage: 95%',
  'Class 12 Percentage: 95%', 'Backlogs: 0', 'Skills', 'Python, SQL, Git', 'Projects', 'Hospital Management System',
  'Image Classification', 'Bank Management System', 'E-Commerce Website', 'Hand Gesture Recognition', 'Internships',
  'Computer Vision Intern', 'Research Intern', 'Web Development Intern', 'Deep Learning Intern', 'Certifications',
  'TensorFlow Certification', 'Cyber Security Certification', 'Python Certification', 'Achievements', 'Research Paper Presented',
  'Coding Competition Winner', 'Hackathon Finalist'
]);
const invalid = pdf('invalid-grade.pdf', ['Review Candidate', 'review@example.test', 'B.Tech Computer Science',
  'CGPA: 12.5', 'Skills', 'Python, SQL', 'Projects: None']);
const lower = path.resolve('samples/resumes/03_data_analyst_text.pdf');
let holdProcessing = true;
let assessmentState;
await page.route('**/api/batches/BAT_*', async route => {
  if (route.request().method() !== 'GET') return route.continue();
  const response = await route.fetch();
  const data = await response.json();
  if (holdProcessing && data.files?.length) {
    data.extracting = true;
    data.files[0].status = 'ocr';
    data.can_run = false;
  }
  if (assessmentState === 'running' && data.run.id) {
    data.run = {...data.run, summary: undefined, finished_at: undefined, status: 'running', processed: 1, total: 2};
    data.job_running = true;
    data.can_run = false;
  } else if (assessmentState === 'failed' && data.run.summary) {
    data.run = {...data.run, status: 'failed', summary: undefined, error: 'Assessment could not finish. Run the batch again.'};
    data.can_run = true;
  } else if (assessmentState === 'zero' && data.run.summary) {
    data.run.summary = {assessed: 0, shortlisted: 0, non_shortlisted: 0, failed: 0, excluded: 0};
  }
  await route.fulfill({response, json:data});
});

try {
  await page.goto(baseURL);
  await page.getByRole('button',{name:'Enter demo workspace'}).click();
  await page.getByRole('link',{name:'Resume studio',exact:true}).click();
  await page.getByText('Choose a batch to view its progress.', {exact:true}).waitFor();
  await page.locator('#upload-job').selectOption('JOB_004');
  await page.locator('#resume-file').setInputFiles([shortlist, invalid]);
  await page.locator('#resume-file').setInputFiles(lower);
  await page.locator('#resume-file').setInputFiles({name:'broken.pdf',mimeType:'application/pdf',buffer:Buffer.from('not a PDF')});
  assert.equal(await page.locator('.remove-file').count(), 4);
  await page.getByRole('button',{name:'Extract 4 resumes',exact:true}).click();
  await page.getByRole('heading',{name:'Extracting resumes',exact:true}).waitFor();
  const run = page.getByRole('button',{name:'Run Model on All Resumes',exact:true});
  assert(await run.isDisabled());
  holdProcessing = false;
  await page.getByRole('heading',{name:'Extraction complete',exact:true}).waitFor();
  assert(await run.isEnabled());
  assert.equal(await page.locator('.queue-error').count(), 1);
  await page.getByText('2 eligible · 1 pending review', {exact:false}).waitFor();
  await page.reload();
  await page.getByRole('heading',{name:'Extraction complete',exact:true}).waitFor();
  const batchId = await page.locator('#batch-history').inputValue();
  assessmentState = 'running';
  await run.click();
  const dashboard = page.getByRole('region', {name:'Assessment Results'});
  await dashboard.getByText('Processing', {exact:true}).waitFor();
  const progress = dashboard.getByRole('progressbar');
  assert.equal(await progress.getAttribute('value'), '1');
  assert.equal(await progress.getAttribute('max'), '2');
  assert(await run.isDisabled());
  assessmentState = undefined;
  await dashboard.getByText('Completed', {exact:true}).waitFor();
  const batch = await (await page.request.get('/api/batches/' + batchId)).json();
  assert.equal(batch.run.summary.assessed, 2);
  assert.equal(batch.run.summary.shortlisted, 1, JSON.stringify(batch.files));
  assert.equal(batch.run.summary.non_shortlisted, 1);
  assert.deepEqual(await dashboard.locator('.assessment-metrics dt').allTextContents(),
    ['Total Assessed', 'Shortlisted', 'Not Shortlisted']);
  assert.deepEqual(await dashboard.locator('.assessment-metrics dd').allTextContents(),
    ['assessed','shortlisted','non_shortlisted'].map(key => String(batch.run.summary[key])));
  assert.deepEqual(await dashboard.locator('.assessment-secondary dd').allTextContents(),
    [String(batch.run.summary.failed), String(batch.counts.review), (batch.run.threshold * 100).toFixed(1) + '%']);
  assert.equal(await dashboard.locator('time').getAttribute('datetime'), batch.run.finished_at);
  assert.match(await dashboard.locator('.assessment-context').innerText(), /Python Developer/);
  await dashboard.getByText('Job shortlist allocation', {exact:true}).click();
  const allocation = batch.allocation;
  const capacity = allocation.active.job.shortlist_capacity;
  assert.deepEqual(await dashboard.locator('.allocation-facts dd').allTextContents(),
    [allocation.active.job.openings, allocation.active.job.shortlisting_ratio, capacity, allocation.assessed,
      allocation.qualified, allocation.shortlisted, allocation.non_shortlisted, allocation.review].map(String));
  const meter = dashboard.getByRole('meter');
  assert.equal(await meter.getAttribute('value'), String(allocation.shortlisted));
  assert.equal(await meter.getAttribute('max'), String(capacity));
  assert.equal(await dashboard.locator('.capacity-percent').textContent(), Math.round(100 * allocation.shortlisted / capacity) + '%');
  const explanation = dashboard.locator('.ats-allocation .ats-note').first();
  assert((await explanation.innerText()).replace(/\s+/g, ' ').includes(
    `shortlisted from ${allocation.qualified} eligible ${allocation.qualified === 1 ? 'candidate' : 'candidates'}. The configured shortlist capacity is ${capacity}.`));
  assert(!/Batch ID|Assessment Run ID|Active run|(?:RUN|BAT)_[A-Z0-9]+/i.test(await dashboard.innerText()));
  assert(!((await page.locator('#batch-history option:checked').textContent()).includes(batchId.slice(-6))));
  assert(await dashboard.getByRole('button',{name:'HR Shortlist',exact:true}).evaluate(button => button.classList.contains('primary')));
  await dashboard.screenshot({path:'test-results/assessment-results-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  assert(await dashboard.evaluate(panel => panel.scrollWidth <= panel.clientWidth));
  await dashboard.screenshot({path:'test-results/assessment-results-mobile.png'});
  await page.setViewportSize({width:1440,height:1000});
  assessmentState = 'failed';
  await page.reload();
  await dashboard.getByText('Failed',{exact:true}).waitFor();
  await dashboard.getByText('Assessment could not finish. Run the batch again.',{exact:true}).waitFor();
  assert.equal(await dashboard.getByRole('progressbar').count(), 0);
  assert(await run.isEnabled());
  assessmentState = 'zero';
  await page.reload();
  await dashboard.getByText('No candidates were assessed in this batch.',{exact:true}).waitFor();
  assert.deepEqual(await dashboard.locator('.assessment-metrics dd').allTextContents(), ['0', '0', '0']);
  assessmentState = undefined;
  await page.reload();
  await dashboard.getByText('Completed',{exact:true}).waitFor();
  const repeat = await (await page.request.post('/api/batches/' + batchId + '/run')).json();
  assert.equal(repeat.run.id, batch.run.id);
  assert(await run.isDisabled());

  const draft = page.waitForEvent('download');
  await page.getByRole('button',{name:'Download extracted draft'}).click();
  assert.equal((await draft).suggestedFilename(), 'Incepta_Extraction_Draft.csv');
  const model = page.waitForEvent('download');
  await page.getByRole('button',{name:'Download ML input CSV'}).click();
  assert.equal((await model).suggestedFilename(), 'Incepta_Applications.csv');

  await page.getByRole('button',{name:'HR Shortlist',exact:true}).click();
  await page.waitForURL('**/#shortlist');
  await page.getByRole('heading',{name:'HR Shortlist',exact:true}).waitFor();
  await page.getByRole('button',{name:'View Strong Candidate'}).waitFor();
  await page.screenshot({path:'test-results/shortlist-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'View Strong Candidate'}).click();
  await page.getByRole('heading',{name:'Resume application',exact:true}).waitFor();
  const scoreCards = page.locator('.ats-profile .ats-metrics');
  await scoreCards.getByText('Weighted recruitment score',{exact:true}).waitFor();
  await scoreCards.getByText('ML shortlist score',{exact:true}).waitFor();
  const profile = page.getByRole('dialog');
  for (const title of ['Overview','Education','Skills','Projects','Internships','Work Experience','Certifications',
    'Achievements and Publications','Original Resume','Assessment Details']) {
    await profile.getByText(title, {exact:true}).first().waitFor();
  }
  const resumeSection = profile.getByText('Original Resume', {exact:true});
  await resumeSection.focus();
  await page.keyboard.press('Enter');
  await profile.getByTitle('Original uploaded resume').waitFor();
  await profile.getByText('Assessment Details', {exact:true}).click();
  await profile.getByText('Model', {exact:true}).waitFor();
  await profile.evaluate(dialog => { dialog.scrollTop = 0; });
  await profile.screenshot({path:'test-results/candidate-profile-desktop.png'});
  assert(!/Batch ID|Assessment run|Allocation run|Model version \/ hash|(?:RUN|BAT)_[A-Z0-9]+/i.test(await profile.innerText()));
  await page.setViewportSize({width:390,height:844});
  assert(await profile.evaluate(el => el.scrollWidth <= el.clientWidth));
  await page.setViewportSize({width:1440,height:1000});
  await page.getByLabel('Decision',{exact:true}).selectOption('Rejected');
  const confirmation = page.waitForEvent('dialog').then(dialog => dialog.dismiss());
  await page.getByRole('button',{name:'Save decision'}).click();
  await confirmation;
  assert.equal((await (await page.request.get('/api/candidates/' + batch.files[0].application_id)).json()).review, 'Pending HR Review');
  await page.getByLabel('Decision',{exact:true}).selectOption('On Hold');
  await page.getByLabel('Reason (optional)').fill('Interview scheduling');
  await page.getByRole('button',{name:'Save decision'}).click();
  await page.getByText('HR decision saved.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Close dialog'}).click();

  await page.getByRole('button',{name:'Non-shortlisted',exact:true}).click();
  await page.waitForURL('**/#general-pool');
  await page.getByRole('button',{name:'View Kabir Sample'}).waitFor();
  await page.getByRole('button',{name:'Need Data Review',exact:true}).click();
  await page.waitForURL('**/#data-review');
  await page.getByRole('heading',{name:'Need Data Review',exact:true}).waitFor();
  await page.getByRole('button',{name:'View Review Candidate'}).waitFor();
  await page.screenshot({path:'test-results/data-review-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'View Review Candidate'}).click();
  await page.getByText(/Extracted value 12.5/).waitFor();
  await page.getByRole('button',{name:'Correct and revalidate'}).click();
  await page.getByLabel('CGPA',{exact:true}).fill('8.4');
  await page.getByRole('button',{name:'Save and revalidate'}).click();
  await page.getByText('Profile revalidated and ready for the next batch run.').waitFor();
  await page.getByRole('dialog').getByText('Education',{exact:true}).click();
  await page.getByText('Original value 12.5').waitFor();
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.getByRole('link',{name:'Resume studio',exact:true}).click();
  await run.click();
  await dashboard.locator('.ats-metrics').first().locator('dd').first().filter({hasText:/^3$/}).waitFor();

  await page.getByRole('button',{name:'HR Shortlist',exact:true}).click();
  await page.getByRole('button',{name:'View Strong Candidate'}).click();
  assert.equal(await page.getByLabel('Decision',{exact:true}).inputValue(), 'On Hold');
  await page.getByText('Decision history',{exact:true}).click();
  await page.getByText(/Interview scheduling/).waitFor();
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.getByRole('link',{name:'Resume studio',exact:true}).click();
  await page.locator('#upload-job').selectOption('JOB_004');
  await page.locator('#resume-file').setInputFiles(shortlist);
  await page.getByRole('button',{name:'Extract resume',exact:true}).click();
  await page.getByText('Exact duplicate',{exact:true}).waitFor();
  await dashboard.getByText('No candidates are ready for assessment in this batch.',{exact:true}).waitFor();
  assert.deepEqual(await dashboard.locator('.assessment-metrics dd').allTextContents(), ['—', '—', '—']);
  assert(await run.isDisabled());
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/batch-studio-mobile.png',fullPage:true});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  assert.deepEqual(errors, []);
  console.log('PASS: automatic extraction, batch inference, all routing outcomes, corrections, HR decisions, CSV, reload, duplicates, and mobile layout.');
} finally {
  await browser.close();
}
