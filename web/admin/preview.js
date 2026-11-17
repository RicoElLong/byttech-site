// Public-content preview only. The iframe is sandboxed and never runs site scripts.
export function previewHome(html,data,base,reviews){
 const doc=new DOMParser().parseFromString(html,'text/html');
 const text=(selector,value,root=doc)=>{const n=root.querySelector(selector);if(n)n.textContent=value;};
 const section={services:'#services',principles:'#honesty',discounts:'#discounts',why:'#features',tags:'#complaints',steps:'#how',important:'#important',districts:'#districts',cta:'#order'};
 const list={services:['.services-grid','.service-row','h3','.service-price'],hero:['.hero-proof','.hero-proof-card','strong','small'],pricing:['.price-grid','.price-card','h3','.price-val'],principles:['.features','.feature','h3','p'],discounts:['.discounts','.discount-card','h3','p'],why:['.features','.feature','h3','p'],tags:['.pills','.pill'],steps:['.steps','.step','h3','p'],important:['.warnings','.warning',null,'p'],districts:['.districts','.district']};
 text('title',data.global.seoTitle);doc.querySelector('meta[name=description]').content=data.global.seoDescription;
 text('h1',data.hero.title);text('.hero-lead',data.hero.subtitle);text('.hero-badge','Ремонт стиральных машин · '+data.global.city);const hours=doc.querySelector('.header-hours');if(data.global.hours.includes(' по ')){const [first,...rest]=data.global.hours.split(' по ');const strong=doc.createElement('strong');strong.textContent=first;const span=doc.createElement('span');span.textContent='по '+rest.join(' по ');hours.replaceChildren(strong,span);}else hours.textContent=data.global.hours;text('.header-cta',data.global.ctaButton);
 for(const a of doc.querySelectorAll('a[href^="tel:"]')){if(a.textContent.trim())a.textContent=data.global.phone;}
 text('.header-phone span',data.global.phone);
 for(const [key,selector] of Object.entries(section)){const block=doc.querySelector(selector);text('h2',data[key].title,block);if(data[key].subtitle!==undefined)text('.section-head p',data[key].subtitle,block);}
 text('.service-subhead h2',data.pricing.title);text('.service-subhead p',data.pricing.subtitle);
 const discount=doc.querySelector('#discounts');const discountNote=[...discount.querySelectorAll('p')].at(-1);discountNote.textContent=data.discounts.footnote;
 text('#order p',data.cta.text);text('#maxHelp',data.cta.maxInstruction);
 text('#intakeStatus',data.form.disabledNotice);[...doc.querySelectorAll('.quiz-step')].slice(0,3).forEach((n,i)=>text('h3',data.form.steps[i],n));text('.quiz-success h3',data.form.successTitle);text('.quiz-success p',data.form.successText);
 for(const [key,[container,cls,title,body]] of Object.entries(list)){
  const block=key==='hero'?doc.querySelector('.hero'):key==='pricing'?doc.querySelector('#services'):doc.querySelector(section[key]);
  const parent=block.querySelector(container),templates=[...parent.querySelectorAll(cls)];const rows=key==='hero'?data.hero.features:data[key].items;
  parent.replaceChildren();rows.forEach((row,i)=>{const node=templates[Math.min(i,templates.length-1)].cloneNode(true);if(!body)node.textContent=row;else{if(title)text(title,key==='pricing'?row.name:row.title,node);text(body,key==='pricing'?row.price:row.text,node);if(key==='pricing')node.querySelector('.price-val').classList.toggle('free',row.price.trim().toLowerCase()==='бесплатно');if(key==='discounts')text('.pct',row.percent,node);if(key==='important')text('.warning-icon',row.icon,node);if(key==='steps')text('.step-num',String(i+1).padStart(2,'0'),node);}parent.append(node);});
 }
 const notes=doc.querySelector('.price-note ul');notes.replaceChildren(...data.pricing.footnotes.map(s=>{const li=doc.createElement('li');li.textContent=s;return li;}));
 const reviewSlot=doc.querySelector('[data-reviews-slot]');
 if(reviewSlot&&reviews){
  const viewport=doc.createElement('div');
  viewport.className=reviews.length?'reviews-viewport':'reviews-empty';
  if(!reviews.length)viewport.textContent='Отзывы готовятся к публикации';
  for(const review of reviews){
   const card=doc.createElement('article');
   card.className='review-card';
   const quote=doc.createElement('blockquote');
   quote.textContent=review.text;
   const footer=doc.createElement('footer');
   const author=doc.createElement('strong');
   author.textContent=review.name;
   footer.append(author,review.date);
   card.append(quote,footer);
   viewport.append(card);
  }
  reviewSlot.replaceChildren(viewport);
 }
 doc.querySelectorAll('script').forEach(n=>n.remove());
 doc.querySelectorAll('a').forEach(n=>n.removeAttribute('href'));
 doc.querySelectorAll('input,button,textarea,select').forEach(n=>n.disabled=true);
 const baseNode=doc.createElement('base');baseNode.href=base;doc.head.prepend(baseNode);
 return '<!doctype html>'+doc.documentElement.outerHTML;
}
