import {chromium} from '@playwright/test';
import path from 'node:path';

const baseURL = process.env.SPROUT_TEST_URL || 'http://127.0.0.1:8002';
const browser = await chromium.launch({channel:'msedge',headless:true});
const page = await browser.newPage({baseURL, viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
const errors = [];
let holdProcessing=true;
page.on('pageerror', error => errors.push(error.message));
await page.route('**/api/screenings/RES_*',async route=>{
  if(route.request().method()!=='GET')return route.continue();
  const response=await route.fetch();
  const data=await response.json();
  if(holdProcessing&&data.status==='ready')data.status='parsing';
  await route.fulfill({response,json:data});
});
try {
  await page.goto(baseURL);
  await page.getByRole('button',{name:'Enter demo workspace'}).click();
  await page.getByRole('heading',{name:'A fresh start. A better fit.'}).waitFor();
  await page.getByRole('link',{name:'Resume studio',exact:true}).click();
  await page.locator('#upload-job').selectOption('JOB_004');
  await page.locator('#resume-file').setInputFiles([
    path.resolve('samples/resumes/01_python_developer_text.pdf'),
    path.resolve('samples/resumes/03_data_analyst_text.pdf')
  ]);
  if(await page.locator('.remove-file').count()!==2)throw new Error('Multiple selected resumes not shown.');
  await page.locator('#resume-file').setInputFiles({name:'invalid-test.pdf',mimeType:'application/pdf',buffer:Buffer.from('not a PDF')});
  if(await page.locator('.remove-file').count()!==3)throw new Error('Adding another file replaced the previous selection.');
  await page.getByRole('button',{name:'Extract 3 resumes',exact:true}).click();
  await page.getByRole('heading',{name:'Structuring…',exact:true}).waitFor({timeout:45000});
  await page.screenshot({path:'test-results/processing-active-desktop.png',fullPage:true});
  holdProcessing=false;
  await page.locator('.queue-review').nth(1).waitFor({timeout:45000});
  await page.locator('.queue-error').waitFor();
  if(await page.locator('#download-model-csv').isDisabled())throw new Error('Prepared profiles should allow model CSV export.');
  const draftDownload=page.waitForEvent('download');
  await page.locator('#download-draft-csv').click();
  await (await draftDownload).saveAs('test-results/browser-extraction-draft.csv');
  await page.locator('.queue-item').filter({hasText:'01_python_developer_text.pdf'}).getByRole('button',{name:/Review data/}).click();
  await page.getByRole('heading',{name:'Resume preview',exact:true}).waitFor({timeout:45000});
  if(await page.getByRole('textbox',{name:'CGPA · 10-point scale',exact:true}).inputValue() !== '8.6') throw new Error('Sample CGPA was not extracted.');
  if(await page.locator('.review-form [required]').count())throw new Error('Preview contains required fields.');
  if(await page.locator('.review-form input:not([readonly]), .review-form textarea:not([readonly])').count())throw new Error('Preview must be read-only.');
  await page.screenshot({path:'test-results/checkpoint-resume-review.png',fullPage:true});
  await page.getByRole('button',{name:'Run model',exact:true}).click();
  await page.locator('.model-result').waitFor();
  if(Number((await page.locator('.model-score').first().textContent()).split('/')[0].trim())<=0)throw new Error('Recruitment score must be shown separately.');
  if((await page.locator('.classifier-value').textContent()).trim()==='0.0%')throw new Error('A positive classifier signal was rounded to zero.');
  const profileDownload=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download input CSV',exact:true}).click();
  await (await profileDownload).saveAs('test-results/browser-profile-input.csv');
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.locator('.queue-item').filter({hasText:'03_data_analyst_text.pdf'}).getByRole('button',{name:/Review data/}).click();
  if(await page.getByRole('textbox',{name:'CGPA · 10-point scale',exact:true}).inputValue()!=='7.2')throw new Error('Candidate data leaked between resumes.');
  if(await page.locator('.review-form [required]').count())throw new Error('Preview contains required fields.');
  if(await page.locator('.review-form input:not([readonly]), .review-form textarea:not([readonly])').count())throw new Error('Preview must be read-only.');
  await page.getByRole('button',{name:'Run model',exact:true}).click();
  await page.locator('.model-result').waitFor();
  await page.screenshot({path:'test-results/checkpoint-resume-prediction.png',fullPage:true});
  if(errors.length) throw new Error(errors.join('\n'));
  await page.getByRole('button',{name:'Close dialog'}).click();
  const modelDownload=page.waitForEvent('download');
  await page.locator('#download-model-csv').click();
  await (await modelDownload).saveAs('test-results/browser-ml-input.csv');
  await page.screenshot({path:'test-results/processing-complete-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/multi-upload-mobile.png',fullPage:true});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Multi-upload page overflows on mobile.');
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('button',{name:'Add more resumes'}).click();
  await page.locator('#resume-file').setInputFiles(path.resolve('samples/resumes/04_missing_academics_text.pdf'));
  await page.getByRole('button',{name:'Extract resume',exact:true}).click();
  await page.locator('.queue-item').filter({hasText:'04_missing_academics_text.pdf'}).getByRole('button',{name:/Review data/}).click();
  if(await page.locator('.confirm-none').count())throw new Error('Confirm-none controls were not removed.');
  if(await page.getByRole('textbox',{name:'Backlogs',exact:true}).inputValue()!=='')throw new Error('Missing backlog information was fabricated.');
  if(await page.locator('#save-confirm').count())throw new Error('Confirmation control remains in preview.');
  await page.getByText(/Automatically filled:/).waitFor();
  await page.getByRole('button',{name:'Run model',exact:true}).click();
  await page.locator('.model-result').waitFor();
  await page.screenshot({path:'test-results/incepta-validation.png',fullPage:true});
  await page.getByRole('button',{name:'Close dialog'}).click();
  if(!(await page.locator('#dropzone').isVisible()))await page.getByRole('button',{name:'Add more resumes'}).click();
  await page.locator('#resume-file').setInputFiles(Array.from({length:12},(_,i)=>({name:`selection-${i}.pdf`,mimeType:'application/pdf',buffer:Buffer.from('%PDF-fixture')})));
  if(await page.locator('.remove-file').count()!==12)throw new Error('File count is still capped.');
  console.log('PASS: multi-file upload, failed-file isolation, independent reviews, exact input mapping, real predictions, and mobile layout.');
} finally {
  await browser.close();
}
