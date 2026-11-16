const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.REVIEW_URL||'http://127.0.0.1:8018';
(async()=>{
 const b=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const p=await b.newPage({viewport:{width:1440,height:1000}});const errors=[];p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
  await p.goto(base+'/admin/');await p.getByText('Загружено текущее содержимое сайта.',{exact:true}).waitFor();
  const nav=p.getByRole('navigation',{name:'Разделы редактора'});
  await nav.getByRole('button',{name:'SEO',exact:true}).click();await p.getByLabel('Title главной',{exact:true}).fill('Проверка редактора БытТех');
  await nav.getByRole('button',{name:'Первый экран',exact:true}).click();await p.getByLabel('Заголовок',{exact:true}).first().fill('Проверка первого экрана');
  await p.reload();await nav.getByRole('button',{name:'SEO',exact:true}).click();assert.equal(await p.getByLabel('Title главной',{exact:true}).inputValue(),'Проверка редактора БытТех');
  await p.getByRole('button',{name:'Предпросмотр',exact:true}).click();const frame=p.frameLocator('#preview-frame');await frame.getByRole('heading',{level:1,name:'Проверка первого экрана'}).waitFor();assert.equal(await frame.locator('script').count(),0);await p.getByRole('button',{name:'Закрыть',exact:true}).click();
  await nav.getByRole('button',{name:'Прайс',exact:true}).click();await p.getByLabel('Цена',{exact:true}).first().fill('от 777 ₽');
  await nav.getByRole('button',{name:'Статьи',exact:true}).click();await p.getByRole('button',{name:'Добавить статью',exact:true}).click();assert.equal(await p.getByLabel('URL статьи (латиница и дефисы)',{exact:true}).count(),6);
  const dl=p.waitForEvent('download');await p.getByRole('button',{name:'Скачать изменения',exact:true}).click();const download=await dl;await download.saveAs('/tmp/byttech-editor-browser.json');const exported=JSON.parse(fs.readFileSync('/tmp/byttech-editor-browser.json','utf8'));assert.equal(exported.site.global.seoTitle,'Проверка редактора БытТех');assert.equal(exported.site.pricing.items[0].price,'от 777 ₽');assert.equal(exported.articles.length,6);assert(!('leads'in exported));
  await nav.getByRole('button',{name:'Заявки',exact:true}).click();await p.getByText('Этот редактор не получает и не хранит заявки клиентов.',{exact:false}).waitFor();
  await p.locator('#import-file').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{"leads":[]}')});await p.getByText('Импорт отклонён:',{exact:false}).waitFor();
  await p.locator('#import-file').setInputFiles('/tmp/byttech-editor-browser.json');await nav.getByRole('button',{name:'SEO',exact:true}).click();assert.equal(await p.getByLabel('Title главной',{exact:true}).inputValue(),'Проверка редактора БытТех');
  for(const width of [320,375,1440]){await p.setViewportSize({width,height:900});for(const tab of ['Глобально','Прайс','Статьи','Публикация']){await nav.getByRole('button',{name:tab,exact:true}).click();assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${width}: ${tab}`);}await p.screenshot({path:`artifacts/editor-${width}.png`});}
  assert.deepEqual(errors,[]);console.log('Editor passed: current defaults, edits, persisted draft, sandbox preview, prices, new article, export/import, invalid import rejected, no leads, 320/375/1440 layouts.');
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exit(1)});
