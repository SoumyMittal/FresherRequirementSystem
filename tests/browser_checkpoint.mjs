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
  if(!(await page.locator('#download-model-csv').isDisabled()))throw new Error('Model CSV must require confirmed profiles.');
  const draftDownload=page.waitForEvent('download');
  await page.locator('#download-draft-csv').click();
  await (await draftDownload).saveAs('test-results/browser-extraction-draft.csv');
  await page.locator('.queue-item').filter({hasText:'01_python_developer_text.pdf'}).getByRole('button',{name:/Review data/}).click();
  await page.getByRole('heading',{name:'A human check makes the difference.'}).waitFor({timeout:45000});
  if(await page.locator('#field-CGPA').inputValue() !== '8.6') throw new Error('Sample CGPA was not extracted.');
  await page.getByRole('button',{name:'Check model inputs'}).click();
  await page.getByText('23 application fields mapped to 34 model inputs.').waitFor();
  await page.screenshot({path:'test-results/checkpoint-resume-review.png',fullPage:true});
  await page.getByRole('button',{name:'Confirm & run model'}).click();
  await page.locator('.model-result').waitFor();
  if(Number((await page.locator('.model-score').first().textContent()).split('/')[0].trim())<=0)throw new Error('Recruitment score must be shown separately.');
  if((await page.locator('.classifier-value').textContent()).trim()==='0.0%')throw new Error('A positive classifier signal was rounded to zero.');
  const profileDownload=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download input CSV',exact:true}).click();
  await (await profileDownload).saveAs('test-results/browser-profile-input.csv');
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.locator('.queue-item').filter({hasText:'03_data_analyst_text.pdf'}).getByRole('button',{name:/Review data/}).click();
  if(await page.locator('#field-CGPA').inputValue()!=='7.2')throw new Error('Candidate data leaked between resumes.');
  await page.getByRole('button',{name:'Check model inputs'}).click();
  await page.getByText('23 application fields mapped to 34 model inputs.').waitFor();
  await page.getByRole('button',{name:'Confirm & run model'}).click();
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
  console.log('PASS: multi-file upload, failed-file isolation, independent reviews, exact input mapping, real predictions, and mobile layout.');
} finally {
  await browser.close();
}
