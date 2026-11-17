import { previewHome } from './preview.js';
const KEY='byttech_public_editor_v1';
const status=document.querySelector('#save-status');
const content=document.querySelector('#content');
let defaults,schema,data,active='global',fieldId=0;
const tabs=[['global','Глобально'],['hero','Первый экран'],['form','Форма'],['services','Услуги'],['pricing','Прайс'],['principles','Принципы'],['discounts','Скидки'],['why','Почему я'],['tags','Поломки'],['steps','Шаги'],['important','Важно'],['districts','Районы'],['cta','Призыв к действию'],['seo','SEO'],['articles','Статьи'],['reviews','Отзывы'],['leads','Заявки'],['backup','Публикация']];
const labels={phone:'Телефон для отображения',phoneRaw:'Телефон для ссылки (+7XXXXXXXXXX)',hours:'Часы работы',city:'Город в подписи первого экрана',ctaButton:'Кнопка в шапке',seoTitle:'Title главной',seoDescription:'Description главной',ogTitle:'Open Graph title',ogDescription:'Open Graph description',title:'Заголовок',subtitle:'Описание',text:'Текст',features:'Карточки преимуществ',items:'Элементы',name:'Название работы',price:'Цена',footnotes:'Сноски',footnote:'Условия скидки',percent:'Процент / метка',icon:'Иконка (эмодзи)',disabledNotice:'Сообщение при отключённом приёме',steps:'Заголовки трёх шагов',successTitle:'Заголовок подтверждения',successText:'Текст подтверждения',maxInstruction:'Инструкция связи в MAX',problem:'Тип проблемы для формы',heading:'H1 статьи',slug:'URL статьи (латиница и дефисы)',description:'Description и анонс',body:'Текст статьи (Markdown)'};
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,action,cls='btn'){const b=node('button',text,cls);b.type='button';b.addEventListener('click',action);return b;}
function notice(text,error=false){status.textContent=text;status.classList.toggle('field-error',error);}
function validate(value){
 if(value?.version===1 && !Object.hasOwn(value,'reviews')) value.reviews=structuredClone(defaults.reviews);
 function check(v,s,path){
  if(Array.isArray(s)){if(!Array.isArray(v)||v.length>100)throw Error(`${path}: неверный список`);v.forEach(x=>check(x,s[0],path));return;}
  if(s&&typeof s==='object'){if(!v||Array.isArray(v)||typeof v!=='object'||Object.keys(v).sort().join('|')!==Object.keys(s).sort().join('|'))throw Error(`${path}: неверный состав полей`);for(const k of Object.keys(s))check(v[k],s[k],path+'.'+k);return;}
  if(typeof v!==typeof s||typeof v==='string'&&(v.length>(path.includes('.articles')?100000:20000)||v.includes('\0')))throw Error(`${path}: неверное значение`);
 }
 check(value,schema,'Документ');
 if(value.version!==1)throw Error('Неизвестная версия файла');
 if(!/^\+7[0-9]{10}$/.test(value.site.global.phoneRaw))throw Error('Телефон ссылки должен быть в формате +7XXXXXXXXXX');
 if(!value.site.global.seoTitle.trim()||!value.site.hero.title.trim())throw Error('Заполните title и H1 главной');
 if(value.site.form.steps.length!==3)throw Error('У формы должны остаться три шага');
 if(!value.articles.length)throw Error('Нужна хотя бы одна статья');
 const slugs=new Set();
 for(const a of value.articles){if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(a.slug)||a.slug==='index'||slugs.has(a.slug))throw Error('URL статей должны быть уникальными: латиница, цифры и дефисы');slugs.add(a.slug);if(Object.values(a).some(x=>!x.trim()))throw Error('Заполните все поля статьи');}
 for(const a of value.articles){for(const m of a.body.matchAll(/\]\(([^)]+)\)/g)){const url=m[1];if(url.startsWith('https://')||['/#quiz','/#prices'].includes(url))continue;const match=url.match(/^\/articles\/([a-z0-9-]+)\/$/);if(!match||!slugs.has(match[1]))throw Error('В статьях разрешены HTTPS-ссылки и ссылки на существующие страницы сайта');}}
 if(value.reviews.length>30)throw Error('Можно опубликовать до 30 отзывов.');
 for(const review of value.reviews){
  const {name,text,date,sourceUrl,permission}=review;
  if(!name.trim()||!text.trim()||!date.trim()||!permission)throw Error('Заполните имя, текст и дату отзыва и подтвердите разрешение на публикацию.');
  let url;
  try{url=new URL(sourceUrl);}catch{throw Error('Укажите публичную HTTPS-ссылку на отзыв.');}
  if(url.protocol!=='https:'||url.username||url.password||!sourceUrl.startsWith('https://'))throw Error('Укажите публичную HTTPS-ссылку на отзыв.');
  if(name.length>100||text.length>1200||date.length>40||sourceUrl.length>2048)throw Error('Одно из полей отзыва превышает допустимую длину.');
 }
 return value;
}
function save(){
 try{validate(data);localStorage.setItem(KEY,JSON.stringify(data));notice('Черновик сохранён в этом браузере. Опубликованный сайт не изменён.');}
 catch(e){notice('Не сохранено: '+e.message,true);}
}
function field(label,value,change,long=false){
 const wrap=node('div',undefined,'field');const id='field-'+(++fieldId);const l=node('label',label);l.htmlFor=id;
 const input=document.createElement(long?'textarea':'input');if(!long)input.type='text';input.id=id;input.value=value;input.maxLength=long?100000:20000;if(long)input.rows=4;
 input.addEventListener('input',()=>{change(input.value);save();});wrap.append(l,input);return wrap;
}
function editObject(parent,obj,shape,path=''){
 for(const key of Object.keys(shape)){
  if(path==='global'&&['seoTitle','seoDescription','ogTitle','ogDescription'].includes(key))continue;
  const value=obj[key];const label=labels[key]||key;
  if(Array.isArray(value)){
   const box=node('section',undefined,'panel');box.append(node('h2',label));
   value.forEach((item,i)=>{
    const card=node('div',undefined,'card-item');const actions=node('div',undefined,'card-actions');
    if(!(path==='form'&&key==='steps')){
     actions.append(button('↑',()=>{if(i){[value[i-1],value[i]]=[value[i],value[i-1]];save();render();}}),button('↓',()=>{if(i<value.length-1){[value[i+1],value[i]]=[value[i],value[i+1]];save();render();}}),button('Удалить',()=>{value.splice(i,1);save();render();},'btn btn-danger'));
    }
    card.append(actions);
    if(typeof item==='string')card.append(field(`${label} ${i+1}`,item,v=>value[i]=v));
    else editObject(card,item,shape[key][0],path+'.'+key);
    box.append(card);
   });
   if(!(path==='form'&&key==='steps'))box.append(button('Добавить',()=>{value.push(structuredClone(shape[key][0]));save();render();}));
   parent.append(box);
  } else if(typeof value==='string')parent.append(field(label,value,v=>obj[key]=v,['text','subtitle','description','body','seoDescription','disabledNotice','maxInstruction'].includes(key)));
 }
}
function download(){try{validate(data);const blob=new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const a=node('a');a.href=url;a.download='byttech-content.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice('Файл скачан. Для применения выполните шаги во вкладке «Публикация».');}catch(e){notice(e.message,true);}}
function renderArticles(){
 content.append(node('h2','Статьи'));
 data.articles.forEach((a,i)=>{const box=node('section',undefined,'panel');box.append(node('h2',a.heading),button('Удалить статью',()=>{if(confirm('Удалить статью из черновика? Ссылки на неё нужно будет исправить.')){data.articles.splice(i,1);save();render();}},'btn btn-danger'));editObject(box,a,schema.articles[0]);content.append(box);});
 content.append(button('Добавить статью',()=>{let slug='novaya-statya';let i=1;while(data.articles.some(a=>a.slug===slug))slug='novaya-statya-'+i++;data.articles.push({slug,heading:'Новая статья',title:'Новая статья | БытТех',description:'Описание новой статьи',body:'Текст новой статьи.'});save();render();}));
}
function renderReviews(){
 content.append(node('p','Добавляйте отзывы с разрешения клиента и указывайте ссылку на источник.'));
 data.reviews.forEach((review,index)=>{
  const card=node('section',undefined,'panel');
  card.append(node('h2',review.name||'Новый отзыв'));
  for(const [key,label] of [['name','Имя'],['text','Текст отзыва'],['date','Дата'],['sourceUrl','Ссылка на источник']]){
   card.append(field(label,review[key],value=>{review[key]=value;},key==='text'));
  }
  const permission=node('input');
  permission.type='checkbox';
  permission.checked=review.permission;
  permission.addEventListener('change',()=>{review.permission=permission.checked;save();});
  const label=node('label');
  label.append(permission,' Есть разрешение на публикацию');
  card.append(label,button('Удалить отзыв',()=>{data.reviews.splice(index,1);save();render();},'btn btn-danger'));
  content.append(card);
 });
 if(data.reviews.length<30)content.append(button('Добавить отзыв',()=>{
  data.reviews.push(structuredClone(schema.reviews[0]));render();
 }));
}
function render(){
 fieldId=0;const nav=document.querySelector('#tabs');nav.replaceChildren();for(const [key,label] of tabs){const b=button(label,()=>{active=key;render();},'tab'+(key===active?' active':''));if(key===active)b.setAttribute('aria-current','page');nav.append(b);}
 content.replaceChildren();
 if(active==='reviews'){renderReviews();return;}
 if(active==='articles'){renderArticles();return;}
 if(active==='leads'){content.append(node('h2','Заявки'),node('p','Этот редактор не получает и не хранит заявки клиентов. Их защищённая обработка остаётся на отдельном сервере. GitHub Pages не предоставляет API заявок.'));return;}
 if(active==='backup'){
  content.append(node('h2','Применение изменений'),node('p','Экспорт — резервная копия публичного содержимого, а не публикация. GitHub Pages обновится после применения файла в репозитории и успешного workflow.'));
  const code=node('pre','python3 deploy/apply_content.py byttech-content.json\npython3 -m unittest discover -s tests -v\nSITE_URL=https://ricoellong.github.io/byttech-site python3 deploy/build_pages.py /tmp/byttech-preview --production\n# Проверить результат и git diff, затем commit/push в main');code.style.whiteSpace='pre-wrap';code.style.overflowWrap='anywhere';content.append(code,button('Скачать JSON',download),button('Сбросить черновик к данным сайта',()=>{if(confirm('Сбросить изменения в этом браузере? Сначала можно скачать JSON.')){data=structuredClone(defaults);save();render();}},'btn btn-danger'));return;
 }
 const box=node('div',undefined,'panel');box.append(node('h2',tabs.find(t=>t[0]===active)[1]));
 if(active==='seo')for(const k of ['seoTitle','seoDescription','ogTitle','ogDescription'])box.append(field(labels[k],data.site.global[k],v=>data.site.global[k]=v,k.endsWith('Description')));
 else{if(active==='form')box.append(node('p','Здесь меняются только тексты. Приём данных включается на сервере после проверки реквизитов и документов; чекбоксом в редакторе это обойти нельзя.'));editObject(box,data.site[active],schema.site[active],active);}
 content.append(box);
}
async function preview(){
 try{validate(data);const response=await fetch('../index.html');if(!response.ok)throw Error('Не удалось загрузить главную');const html=previewHome(await response.text(),data.site,new URL('../',location.href).href,data.reviews);document.querySelector('#preview-frame').srcdoc=html;document.querySelector('#preview-dialog').showModal();}catch(e){notice(e.message,true);}
}
async function init(){
 try{
  const response=await fetch('./defaults.json',{cache:'no-store'});if(!response.ok)throw Error('Нет файла содержимого. Откройте панель через собранный сайт.');defaults=await response.json();const schemaResponse=await fetch('./schema.json',{cache:'no-store'});if(!schemaResponse.ok)throw Error('Нет схемы данных редактора');schema=await schemaResponse.json();validate(defaults);data=structuredClone(defaults);
  try{const saved=localStorage.getItem(KEY);if(saved)data=validate(JSON.parse(saved));notice(saved?'Загружен локальный черновик. Он может отличаться от текущего сайта.':'Загружено текущее содержимое сайта.');}catch{notice('Сохранённый черновик повреждён или устарел. Загружено текущее содержимое; исходный черновик не удалён.',true);}
  render();for(const id of ['export','import','preview'])document.getElementById(id).disabled=false;
  document.querySelector('#export').addEventListener('click',download);document.querySelector('#preview').addEventListener('click',preview);
  document.querySelector('#close-preview').addEventListener('click',()=>document.querySelector('#preview-dialog').close());
  document.querySelector('#import').addEventListener('click',()=>document.querySelector('#import-file').click());
  document.querySelector('#import-file').addEventListener('change',async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>2000000)throw Error('Файл больше 2 МБ');const imported=validate(JSON.parse(await file.text()));if(confirm('Заменить черновик содержимым JSON?')){data=structuredClone(imported);save();render();}}catch(error){notice('Импорт отклонён: '+error.message,true);}finally{e.target.value='';}});
 }catch(e){notice(e.message,true);}
}
init();
