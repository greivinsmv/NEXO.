const slug = new URLSearchParams(location.search).get('game');
const game = games.find(item => item.slug === slug);
const set = (id,value) => { const element=document.getElementById(id);if(element)element.textContent=value; };
if (!game) {
  document.getElementById('not-found').hidden=false;
  document.title='Juego no encontrado — NEXO';
} else {
  document.getElementById('main').hidden=false;
  document.title=`${game.name} — NEXO`;
  set('crumb-name',game.name);set('game-title',game.name);
  const lead=document.querySelector('.game-lead');lead.textContent=game.description||'';lead.hidden=!game.description;
  document.querySelector('.description-label').hidden=!game.description;
  if(game.description)document.querySelector('meta[name="description"]').content=game.description.slice(0,160);
  const cover=document.getElementById('game-cover');cover.classList.add(`cover-${game.art}`);
  if(game.coverUrl){const image=document.createElement('img');image.className='game-cover-image';image.src=game.coverUrl;image.alt=`Portada de ${game.name}`;image.decoding='async';image.addEventListener('error',()=>{if(game.coverFallbackUrl && image.src!==game.coverFallbackUrl)image.src=game.coverFallbackUrl;else image.remove();});cover.prepend(image);}
  const chips=document.getElementById('game-chips');
  const launchPlatforms=Array.isArray(game.platforms)&&game.platforms.length?game.platforms:[game.platform];
  ['Precios de PC',game.type,game.format].forEach(value=>{const span=document.createElement('span');span.textContent=value;chips.append(span);});
  set('launch-platforms',`Lanzado en: ${launchPlatforms.join(', ')}`);
  const hours=value=>value==null?'Sin datos':`${value} h`;
  const achievements=game.achievements==null?'Sin datos':String(game.achievements);
  set('hero-hours',hours(game.hours));set('hero-achievements',achievements);
  document.getElementById('steam-rating-card').classList.toggle('is-missing',game.steamUserScore==null);
  document.getElementById('metacritic-rating-card').classList.toggle('is-missing',game.metacritic==null);
  set('hero-steam-rating',game.steamUserScore==null?'Sin datos':`${game.steamUserScore}%`);
  set('hero-metacritic',game.metacritic==null?'Sin datos':`${game.metacritic}/100`);
  const durationGrid=document.querySelector('.duration-grid');
  const durations=[['Historia principal',game.hours],['Historia + DLC',game.extras],['Completista',game.completion]];
  const missing=[];
  durations.forEach(([label,value])=>{
    if(value==null){missing.push(label);return;}
    const card=document.createElement('div');const caption=document.createElement('span');const amount=document.createElement('strong');
    caption.textContent=label;amount.textContent=hours(value);card.append(caption,amount);durationGrid.append(card);
  });
  if(missing.length){
    const card=document.createElement('div');card.className='duration-missing';
    if(missing.length===durations.length){
      card.classList.add('duration-empty');
      card.textContent='No hay datos sobre cuánto se tarda en completar este juego.';
    } else {
      const caption=document.createElement('span');const amount=document.createElement('strong');
      caption.textContent=missing.join(' y ');amount.textContent='Sin datos';card.append(caption,amount);
    }
    durationGrid.append(card);
  }
  durationGrid.classList.add(`duration-grid--${durationGrid.children.length}`);
  set('fact-platform',launchPlatforms.join(', '));set('fact-type',game.type);set('fact-format',game.format);set('fact-achievements',achievements);
  set('fact-release',game.releaseDate||'Sin datos');
  if(Array.isArray(game.screenshots) && game.screenshots.length){
    const shots=game.screenshots.slice(0,6);
    const gallery=document.getElementById('game-gallery');gallery.replaceChildren();
    if(!document.getElementById('gallery-controls')||!document.getElementById('gallery-lightbox')){
      shots.forEach((shot,index)=>{const img=document.createElement('img');img.src=shot.url;img.alt=shot.alt||`Captura ${index+1} de ${game.name}`;img.loading='lazy';gallery.append(img);});
    } else {
    const controls=document.getElementById('gallery-controls');controls.hidden=false;
    const galleryPrev=document.getElementById('gallery-prev');
    const galleryNext=document.getElementById('gallery-next');
    const galleryCounter=document.getElementById('gallery-counter');
    const lightbox=document.getElementById('gallery-lightbox');
    const lightboxImage=document.getElementById('lightbox-image');
    const lightboxCounter=document.getElementById('lightbox-counter');
    let carouselIndex=0;
    let lightboxIndex=0;
    const slides=[];
    const visibleSlides=()=>Math.max(1,Math.round(gallery.clientWidth/(slides[0]?.getBoundingClientRect().width||gallery.clientWidth)));
    const maxStart=()=>Math.max(0,slides.length-visibleSlides());
    function updateGalleryControls(){
      galleryPrev.disabled=carouselIndex===0;
      galleryNext.disabled=carouselIndex>=maxStart();
      const end=Math.min(carouselIndex+visibleSlides(),slides.length);
      galleryCounter.textContent=carouselIndex+1===end?`Captura ${end} de ${slides.length}`:`Capturas ${carouselIndex+1}–${end} de ${slides.length}`;
    }
    function moveGallery(index,animated=true){
      carouselIndex=Math.max(0,Math.min(index,maxStart()));
      gallery.scrollTo({left:slides[carouselIndex].offsetLeft-slides[0].offsetLeft,behavior:animated&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches?'smooth':'auto'});
      updateGalleryControls();
    }
    let lightboxOpener=null;
    function showLightbox(index){
      lightboxIndex=(index+shots.length)%shots.length;
      const shot=shots[lightboxIndex];
      lightboxImage.src=shot.fullUrl||shot.url.replace(/\.600x338\.jpg(?=\?|$)/,'.1920x1080.jpg');
      lightboxImage.alt=shot.alt||`Captura ${lightboxIndex+1} de ${game.name}`;
      lightboxCounter.textContent=`${game.name} · Captura ${lightboxIndex+1} de ${shots.length}`;
      if(!lightbox.open){lightboxOpener=document.activeElement;lightbox.showModal();document.body.classList.add('has-lightbox');document.getElementById('lightbox-close').focus();}
    }
    shots.forEach((shot,index)=>{
      const slide=document.createElement('button');slide.type='button';slide.className='gallery-slide';slide.setAttribute('aria-label',`Ampliar captura ${index+1} de ${game.name}`);
      const img=document.createElement('img');img.src=shot.url;img.alt=shot.alt||`Captura ${index+1} de ${game.name}`;img.loading='lazy';img.decoding='async';
      slide.append(img);slide.addEventListener('click',()=>showLightbox(index));gallery.append(slide);slides.push(slide);
    });
    galleryPrev.addEventListener('click',()=>moveGallery(carouselIndex-1));
    galleryNext.addEventListener('click',()=>moveGallery(carouselIndex+1));
    gallery.addEventListener('scroll',()=>{
      const position=gallery.scrollLeft;
      const nearest=slides.reduce((best,slide,index)=>Math.abs(slide.offsetLeft-slides[0].offsetLeft-position)<Math.abs(slides[best].offsetLeft-slides[0].offsetLeft-position)?index:best,0);
      carouselIndex=Math.min(nearest,maxStart());updateGalleryControls();
    },{passive:true});
    window.addEventListener('resize',()=>moveGallery(carouselIndex,false));
    document.getElementById('lightbox-prev').addEventListener('click',()=>showLightbox(lightboxIndex-1));
    document.getElementById('lightbox-next').addEventListener('click',()=>showLightbox(lightboxIndex+1));
    document.getElementById('lightbox-close').addEventListener('click',()=>lightbox.close());
    lightbox.addEventListener('close',()=>{document.body.classList.remove('has-lightbox');if(lightboxOpener?.isConnected)lightboxOpener.focus();});
    lightbox.addEventListener('click',event=>{if(event.target===lightbox)lightbox.close();});
    lightbox.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'){event.preventDefault();showLightbox(lightboxIndex-1);}else if(event.key==='ArrowRight'){event.preventDefault();showLightbox(lightboxIndex+1);}});
    let touchStart=null;
    lightbox.addEventListener('touchstart',event=>{touchStart={x:event.changedTouches[0].clientX,y:event.changedTouches[0].clientY};},{passive:true});
    lightbox.addEventListener('touchend',event=>{if(!touchStart)return;const dx=event.changedTouches[0].clientX-touchStart.x;const dy=event.changedTouches[0].clientY-touchStart.y;if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy))showLightbox(lightboxIndex+(dx<0?1:-1));touchStart=null;},{passive:true});
    updateGalleryControls();
    }
  }
  if(game.featuredAchievements?.length&&document.getElementById('achievement-section')){
    document.getElementById('achievement-section').hidden=false;
    const list=document.getElementById('achievement-list');
    game.featuredAchievements.forEach(item=>{
      const row=document.createElement('div');row.className='achievement-item';
      const icon=document.createElement('img');icon.src=item.icon;icon.alt='';icon.loading='lazy';icon.decoding='async';
      const name=document.createElement('strong');name.textContent=item.name;row.append(icon,name);list.append(row);
    });
  }
  set('best-price',money(game.price,game.currency));set('regular-price',game.regular>game.price?money(game.regular,game.currency):'');set('discount-badge',discount(game)>0?`−${discount(game)}%`:'');
  const storeList=document.getElementById('store-list');
  function renderOfferRows(offers){
    storeList.replaceChildren();
    const cheapest=Math.min(...offers.map(offer=>offer.price));
    const tied=offers.filter(offer=>Math.abs(offer.price-cheapest)<.005);
    const bestStore=document.getElementById('best-store');bestStore.replaceChildren();
    tied.forEach((offer,index)=>{if(index)bestStore.append(document.createTextNode(' · '));const name=document.createElement('span');name.className='store-visible-name';name.textContent=offer.store;bestStore.append(storeMark(offer.store),name);});
    offers.forEach(offer=>{
      const row=document.createElement('a');row.className='store-row';row.href=offer.url;row.target='_blank';row.rel='noopener noreferrer';row.setAttribute('aria-label',`Ir a ${offer.store}: ${money(offer.price,offer.currency)}`);
      const info=document.createElement('span');info.className='store-row-info';const name=document.createElement('span');name.className='store-visible-name';name.textContent=offer.store;info.append(storeMark(offer.store),name);
      if(tied.some(item=>item.store===offer.store)){const best=document.createElement('small');best.className='store-best';best.textContent='Mejor precio';info.append(best);}
      const end=document.createElement('span');end.className='store-row-end';const price=document.createElement('strong');price.textContent=money(offer.price,offer.currency);end.append(price);
      const capturedAt=offer.capturedAt||(offer.store==='Steam'?catalogSnapshot?.capturedAt:hasLiveOffers?liveSnapshot?.capturedAt:null);
      if(capturedAt){const date=new Date(capturedAt);if(!Number.isNaN(date.getTime())){const stamp=document.createElement('time');stamp.className='offer-capture-time';stamp.dateTime=date.toISOString();stamp.textContent=new Intl.DateTimeFormat('es-CR',{day:'numeric',month:'short',year:'numeric'}).format(date);end.append(stamp);}}
      const action=document.createElement('small');action.textContent='Ir a la tienda';end.append(action);
      row.append(info,end);storeList.append(row);
    });
  }
  const hasLiveOffers=liveGames.some(item=>item.slug===game.slug);
  const hasPublishedOffers=game.offers?.some(offer=>offer.capturedAt);
  if(game.offers?.length){
    renderOfferRows(game.offers);
    document.querySelector('.demo-pill').textContent='DATOS DE FUENTES';
    document.querySelector('.offer-panel .eyebrow').textContent=hasPublishedOffers?'MEJOR PRECIO DE PC':hasLiveOffers?(liveFresh?'MEJOR PRECIO DE PC':'ÚLTIMO PRECIO DE PC'):'PRECIO DE REFERENCIA DE PC · EE. UU.';
  } else if(catalogSnapshot){
    document.querySelector('.demo-pill').textContent='DATOS DE FUENTES';
    document.querySelector('.offer-panel .eyebrow').textContent='PRECIO PENDIENTE';
    if(game.steamAppId){const row=document.createElement('a');row.className='store-row';row.href=`https://store.steampowered.com/app/${game.steamAppId}/`;row.target='_blank';row.rel='noopener noreferrer';const value=document.createElement('strong');value.textContent='Consultar ↗';row.append(storeMark('Steam'),value);storeList.append(row);}
  }
  const related=document.getElementById('related-list');
  const baseGenres=new Set(game.genres||[]);
  const weighted=genre=>['Indie','Casual','Early Access'].includes(genre)?0.5:2;
  const recommendations=games.filter(item=>item.slug!==game.slug).map(item=>{
    const shared=(item.genres||[]).filter(genre=>baseGenres.has(genre));
    return {item,score:shared.reduce((total,genre)=>total+weighted(genre),0)+Math.log1p(item.currentPlayers||0)/100};
  }).filter(entry=>!baseGenres.size||entry.score>=0.5).sort((a,b)=>b.score-a.score).slice(0,3);
  recommendations.forEach(({item})=>{
    const link=document.createElement('a');link.href=`game.html?game=${encodeURIComponent(item.slug)}`;link.className='related-card';
    const art=document.createElement('div');art.className=`related-art cover-${item.art}`;art.textContent=item.name;
    if(item.cardImageUrl||item.coverFallbackUrl||item.coverUrl){const image=document.createElement('img');image.src=item.cardImageUrl||item.coverFallbackUrl||item.coverUrl;image.alt='';image.loading='lazy';image.addEventListener('error',()=>{image.remove();art.classList.remove('has-image');art.textContent=item.name;});art.textContent='';art.classList.add('has-image');art.append(image);}
    const info=document.createElement('div');const name=document.createElement('strong');name.textContent=item.name;const value=document.createElement('span');value.textContent=money(item.price,item.currency);info.append(name,value);link.append(art,info);related.append(link);
  });
  if(catalogSnapshot && game.steamAppId){
    storeList.setAttribute('aria-busy','true');
    fetchGameOffers(game.steamAppId).then(offers => {
      if(!offers.length) return;
      Object.assign(game,withObservedOffers(game,offers));
      const best=game.offers[0];
      set('best-price',money(best.price,'USD'));
      set('regular-price',best.regular>best.price?money(best.regular,'USD'):'');
      set('discount-badge',discount(game)>0?`−${discount(game)}%`:'');
      renderOfferRows(game.offers);
      document.querySelector('.offer-panel .eyebrow').textContent='MEJOR PRECIO DE PC';
    }).catch(() => {
      // Keep the published reference price if the live request is unavailable.
    }).finally(() => storeList.setAttribute('aria-busy','false'));
  }
  document.addEventListener('nexo:currency',()=>location.reload());
}
