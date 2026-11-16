// Run against a freshly built, locally served review artifact.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const base = process.env.REVIEW_URL || 'http://127.0.0.1:8010';
(async () => {
  const browser = await chromium.launch({executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', headless: true, args: ['--no-sandbox']});
  try {
    const page = await browser.newPage();
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const routes=['/articles/','/articles/ne-slivaet-vodu/','/articles/ne-otzhimaet/','/articles/techet-snizu/','/articles/kak-vybrat-mastera/','/articles/nedorogoy-remont-bez-doplat/'];
    for (const width of [320,375,768,1024,1440]) {
      await page.setViewportSize({width,height:900});
      for(const route of ['/',...routes]) {
        assert.equal((await page.goto(base+route)).status(),200);
        assert.equal(await page.locator('h1').count(),1);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`${width} ${route}`);
      }
    }
    assert.equal((await page.goto(base+'/articles/missing/')).status(),404);
    await page.goto(base+'/articles/ne-slivaet-vodu/');await page.getByRole('link',{name:'Посмотреть цены',exact:true}).click();assert.equal(new URL(page.url()).hash,'#prices');
    await page.goto(base+'/articles/ne-slivaet-vodu/');await page.getByRole('link',{name:'Вызвать мастера в Самаре',exact:true}).click();assert.equal(new URL(page.url()).hash,'#quiz');
    for(const doc of ['privacy.html','consent.html']) assert.equal((await page.goto(base+'/'+doc)).status(),200);
    await page.setViewportSize({width:375,height:900});await page.goto(base);
    await page.locator('#menuToggle').click();assert(await page.locator('#headerNav').isVisible());
    await page.getByRole('navigation',{name:'Основная навигация'}).getByText('Статьи',{exact:true}).click();assert(page.url().endsWith('/articles/'));
    await page.goto(base);await page.locator('.hero-master').evaluate(x=>x.decode());await page.screenshot({path:'artifacts/mobile.png',fullPage:false});
    await page.locator('[data-field=problem] button').filter({hasText:'Другое / не знаю'}).click();
    await page.locator('#quizNext').click();
    await page.locator('[data-field=brand] button').filter({hasText:'Другая / не знаю'}).click();
    await page.locator('#quizBack').click();
    assert.equal(await page.locator('[data-field=problem] [aria-pressed=true]').innerText(),'Другое / не знаю');
    assert.equal(await page.locator('h3:focus').innerText(),'Что случилось с машиной?');
    await page.locator('#quizNext').click();await page.locator('#quizNext').click();
    assert(await page.locator('#quizNext').isDisabled());
    await page.setViewportSize({width:1440,height:1000});await page.goto(base);await page.locator('.hero-master').evaluate(x=>x.decode());await page.screenshot({path:'artifacts/desktop.png',fullPage:false});
    const nojs=await browser.newContext({javaScriptEnabled:false});const staticPage=await nojs.newPage();
    for(const route of routes){await staticPage.goto(base+route);assert(await staticPage.locator('main').isVisible());}
    await staticPage.goto(base);assert.equal(await staticPage.locator('.services-grid').evaluate(x=>getComputedStyle(x).opacity),'1');await nojs.close();
    // Enable only the synthetic test page; all API responses are intercepted.
    await page.route(base+'/',async route=>{const response=await route.fetch();const html=(await response.text()).replace('data-api="" data-config=""','data-api="https://forms.example.test/api/requests" data-config="https://forms.example.test/api/requests/config"');await route.fulfill({response,body:html});});
    const payloads=[];let fail=true;
    await page.route('https://forms.example.test/**',async route=>{
      if(route.request().method()==='OPTIONS'){await route.fulfill({status:204,headers:{'access-control-allow-origin':'*','access-control-allow-methods':'POST,GET','access-control-allow-headers':'content-type'}});return;}
      if(route.request().url().endsWith('/config')){await route.fulfill({json:{ready:true,consent_version:'pd-2026-11-09-v1'}});return;}
      payloads.push(route.request().postDataJSON());
      if(fail){fail=false;await route.abort();} else await route.fulfill({json:{accepted:true,request_id:42}});
    });
    await page.goto(base);await page.locator('[data-value="Протекает"]').click();assert(await page.locator('#safetyWarning').isVisible());
    await page.locator('#quizNext').click();assert.equal(await page.locator('h3:focus').innerText(),'Какая у вас марка машинки?');
    await page.locator('[data-value="Другая / не знаю"]').click();await page.locator('#quizNext').click();
    await page.locator('#quizName').fill('Тест');await page.locator('#quizPhone').fill('+79990000000');
    assert(await page.locator('#quizNext').isDisabled());await page.locator('#personalDataConsent').check();
    await page.locator('#quizNext').click();await page.locator('#quizError').waitFor({state:'visible'});assert.equal(await page.locator('#quizName').inputValue(),'Тест');
    await page.locator('#quizNext').click();await page.getByText('Заявка отправлена!',{exact:true}).waitFor();
    assert.equal(payloads.length,2);assert.equal(payloads[0].submission_id,payloads[1].submission_id);assert.equal(await page.locator('#sumRequest').innerText(),'№42');
    assert.deepEqual(errors,[]);console.log('Browser checks passed: six routes, 5 widths, menu, no JS, disabled intake, back/next, safety, consent, failed request and idempotent retry.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
