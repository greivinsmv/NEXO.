const cards = document.getElementById('cards');
const search = document.getElementById('search');
const sort = document.getElementById('sort');
const empty = document.getElementById('empty');
const searchPanel = document.getElementById('search-results');
let pageSizeSelect = document.getElementById('page-size');
let pagination = document.getElementById('catalog-pagination');
let pageSummary = document.getElementById('page-summary');
if(!pageSizeSelect){
  const label=document.createElement('label');label.className='page-size-label';label.textContent='Mostrar ';
  pageSizeSelect=document.createElement('select');pageSizeSelect.id='page-size';pageSizeSelect.setAttribute('aria-label','Juegos por página');
  [10,20,30].forEach(size=>{const option=document.createElement('option');option.value=String(size);option.textContent=String(size);pageSizeSelect.append(option);});
  label.append(pageSizeSelect);document.querySelector('.display-options')?.prepend(label);
}
if(!pagination||!pageSummary){
  const bar=document.createElement('div');bar.className='pagination-bar';
  pageSummary=document.createElement('p');pageSummary.id='page-summary';pageSummary.className='page-summary';pageSummary.setAttribute('aria-live','polite');
  pagination=document.createElement('nav');pagination.id='catalog-pagination';pagination.className='catalog-pagination';pagination.setAttribute('aria-label','Páginas del catálogo');
  bar.append(pageSummary,pagination);document.getElementById('cards').after(bar);
}
const orbGames = document.getElementById('orb-games');
const gridButton=document.getElementById('view-grid');
const listButton=document.getElementById('view-list');
if(document.getElementById('catalog-count'))document.getElementById('catalog-count').textContent=catalogSnapshot?`${games.length} juegos · precios de PC`:'';
const gamePlatforms=game=>Array.isArray(game.platforms)&&game.platforms.length?game.platforms:[game.platform];
const platformShort={PlayStation:'PS','Nintendo Switch':'Switch','Nintendo Switch 2':'Switch 2'};
const platformSummary=game=>gamePlatforms(game).map(name=>platformShort[name]||name).join(' · ');
let catalogView=localStorage.getItem('nexo-catalog-view')==='list'?'list':'grid';
function setCatalogView(view){
  catalogView=view;localStorage.setItem('nexo-catalog-view',view);
  cards.classList.toggle('is-list',view==='list');
  gridButton.setAttribute('aria-pressed',String(view==='grid'));
  listButton.setAttribute('aria-pressed',String(view==='list'));
  if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches && typeof cards.animate==='function')cards.animate([{opacity:.65,transform:'scale(.99)'},{opacity:1,transform:'scale(1)'}],{duration:190,easing:'ease-out'});
}
gridButton.addEventListener('click',()=>setCatalogView('grid'));
listButton.addEventListener('click',()=>setCatalogView('list'));
cards.classList.toggle('is-list',catalogView==='list');
gridButton.setAttribute('aria-pressed',String(catalogView==='grid'));
listButton.setAttribute('aria-pressed',String(catalogView==='list'));
let platform = 'Todas';
let selectedGenre = '';
const selectedStores = new Set();
let multiStoreOnly = false;
let priceMinEur = null;
let priceMaxEur = null;
const filterPanel = document.getElementById('catalog-filters');
const filterMin = document.getElementById('filter-min');
const filterMax = document.getElementById('filter-max');
const filterGenre = document.getElementById('filter-genre');
const priceInEur = game => game.currency === 'USD' ? game.price / demoRatesFromEUR.USD : game.currency === 'CRC' ? game.price / demoRatesFromEUR.CRC : game.price;
function updateFilterCount(){
  if(!filterPanel) return;
  const count = Number(platform !== 'Todas') + Number(!!selectedGenre) + Number(priceMinEur != null) + Number(priceMaxEur != null) + selectedStores.size + Number(multiStoreOnly);
  document.getElementById('active-filter-count').textContent = count + ' ' + (count === 1 ? 'activo' : 'activos');
}
function updatePriceInputs(){
  if(!filterPanel) return;
  document.getElementById('price-filter-currency').textContent = selectedCurrency;
  const decimals = selectedCurrency === 'CRC' ? 0 : 2;
  filterMin.step = filterMax.step = decimals ? '.01' : '1';
  filterMin.value = priceMinEur == null ? '' : (priceMinEur * demoRatesFromEUR[selectedCurrency]).toFixed(decimals);
  filterMax.value = priceMaxEur == null ? '' : (priceMaxEur * demoRatesFromEUR[selectedCurrency]).toFixed(decimals);
}
if(filterPanel){
const genreLabels = {Action:'Acción',Adventure:'Aventura',Strategy:'Estrategia',Simulation:'Simulación',Racing:'Carreras',Sports:'Deportes',Indie:'Indie',Casual:'Casual',RPG:'RPG'};
for(const genre of [...new Set(games.flatMap(game => game.genres || []))].sort((a,b) => a.localeCompare(b,'es'))){
  const option = document.createElement('option'); option.value = genre; option.textContent = genreLabels[genre] || genre; filterGenre.append(option);
}
for(const name of ['Todas', 'PC', 'PlayStation', 'Xbox', 'Nintendo Switch', 'Nintendo Switch 2'].filter(name=>name==='Todas'||games.some(game=>gamePlatforms(game).includes(name)))){
  const button = document.createElement('button'); button.type = 'button'; button.className = 'platform-option'; button.textContent = name; button.dataset.platform = name; button.setAttribute('aria-pressed',String(name === platform));
  button.addEventListener('click',() => {platform = name;currentPage = 1;document.querySelectorAll('.platform-option').forEach(item => item.setAttribute('aria-pressed',String(item === button)));updateFilterCount();updateOffers();});
  document.getElementById('platform-filter-options').append(button);
}
function renderStoreOptions(){
  const container = document.getElementById('store-filter-options');
  const storeCounts = new Map();
  games.forEach(game => new Set((game.offers || []).map(offer => offer.store)).forEach(name => storeCounts.set(name,(storeCounts.get(name) || 0) + 1)));
  container.replaceChildren();
  for(const [name,count] of [...storeCounts].sort((a,b) => b[1] - a[1])){
    const label = document.createElement('label'); label.className = 'store-option'; label.title = name;
    const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.value = name; checkbox.checked = selectedStores.has(name); checkbox.setAttribute('aria-label',name);
    checkbox.addEventListener('change',() => {checkbox.checked ? selectedStores.add(name) : selectedStores.delete(name);currentPage = 1;updateFilterCount();updateOffers();});
    const total = document.createElement('small'); total.textContent = String(count); label.append(checkbox,storeMark(name),total); container.append(label);
  }
}
renderStoreOptions();
document.addEventListener('nexo:offers',event => {
  const game=games.find(item => item.steamAppId === event.detail.steamAppId);
  if(!game || !event.detail.offers.length) return;
  Object.assign(game,withObservedOffers(game,event.detail.offers));
  renderStoreOptions();
  updateOffers();
});
for(const input of [filterMin,filterMax]) input.addEventListener('input',() => {
  const value = input.value === '' ? null : Number(input.value) / demoRatesFromEUR[selectedCurrency];
  if(input === filterMin) priceMinEur = value; else priceMaxEur = value;
  currentPage = 1;updateFilterCount();updateOffers();
});
filterGenre.addEventListener('change',() => {selectedGenre = filterGenre.value;currentPage = 1;updateFilterCount();updateOffers();});
document.getElementById('filter-multi-store').addEventListener('change',event => {multiStoreOnly=event.target.checked;currentPage=1;updateFilterCount();updateOffers();});
document.getElementById('clear-filters').addEventListener('click',() => {
  platform = 'Todas';selectedGenre = '';selectedStores.clear();multiStoreOnly=false;priceMinEur = null;priceMaxEur = null;currentPage = 1;
  document.getElementById('filter-multi-store').checked=false;
  filterGenre.value = '';document.querySelectorAll('.store-option input').forEach(input => input.checked = false);
  document.querySelectorAll('.platform-option').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.platform === 'Todas')));
  updatePriceInputs();updateFilterCount();updateOffers();
});
const compactFilters = window.matchMedia('(max-width: 950px)');
filterPanel.open = !compactFilters.matches;
compactFilters.addEventListener('change',event => {filterPanel.open = !event.matches;});
updatePriceInputs();updateFilterCount();
}else{
  document.querySelectorAll('.filter').forEach(button=>{
    if(!games.some(game=>gamePlatforms(game).includes(button.dataset.platform)) && button.dataset.platform!=='Todas')button.disabled=true;
    button.addEventListener('click',()=>{platform=button.dataset.platform;currentPage=1;document.querySelectorAll('.filter').forEach(other=>{const active=other===button;other.classList.toggle('active',active);other.setAttribute('aria-pressed',String(active));});updateOffers();});
  });
}
const allowedPageSizes=[10,20,30];
const savedPageSize=Number(localStorage.getItem('nexo-page-size'));
let pageSize=allowedPageSizes.includes(savedPageSize)?savedPageSize:20;
let currentPage=1;
pageSizeSelect.value=String(pageSize);
let selectedOrbGame=games[0];
function renderPagination(total){
  const totalPages=Math.ceil(total/pageSize);
  currentPage=Math.max(1,Math.min(currentPage,totalPages||1));
  const first=(currentPage-1)*pageSize+1;
  const last=Math.min(currentPage*pageSize,total);
  pageSummary.textContent=total?`Mostrando ${first}–${last} de ${total} juegos`:'No hay juegos en este filtro';
  pagination.replaceChildren();
  pagination.hidden=totalPages<=1;
  if(totalPages<=1)return;
  const addButton=(label,page,description,disabled=false)=>{
    const button=document.createElement('button');button.type='button';button.textContent=label;button.disabled=disabled;
    button.setAttribute('aria-label',description);
    if(page===currentPage && !disabled && typeof label==='number')button.setAttribute('aria-current','page');
    button.addEventListener('click',()=>{
      if(page===currentPage)return;
      currentPage=page;render();
      if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches && typeof cards.animate==='function')cards.animate([{opacity:.45,transform:'translateY(8px)'},{opacity:1,transform:'translateY(0)'}],{duration:220,easing:'ease-out'});
      document.getElementById('ofertas').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
    });
    pagination.append(button);
  };
  addButton('←',currentPage-1,'Página anterior',currentPage===1);
  const pages=[...new Set([1,currentPage-1,currentPage,currentPage+1,totalPages].filter(page=>page>=1&&page<=totalPages))].sort((a,b)=>a-b);
  pages.forEach((page,index)=>{
    if(index && page-pages[index-1]>1){const gap=document.createElement('span');gap.textContent='…';gap.setAttribute('aria-hidden','true');pagination.append(gap);}
    addButton(page,page,`Página ${page}`);
  });
  addButton('→',currentPage+1,'Página siguiente',currentPage===totalPages);
}
function render(){
  const visible = games.filter(game =>
    (platform === 'Todas' || gamePlatforms(game).includes(platform)) &&
    (!selectedGenre || (game.genres || []).includes(selectedGenre)) &&
    (priceMinEur == null || priceInEur(game) >= priceMinEur - 1e-6) &&
    (priceMaxEur == null || priceInEur(game) <= priceMaxEur + 1e-6) &&
    (!multiStoreOnly || new Set((game.offers||[]).map(offer=>offer.store)).size>1) &&
    (!selectedStores.size || (game.offers || []).some(offer => selectedStores.has(offer.store)))
  );
  visible.sort((a,b) => sort.value === 'name' ? a.name.localeCompare(b.name,'es') : sort.value === 'price' ? a.price-b.price : sort.value === 'discount' ? discount(b)-discount(a) || (b.relevanceScore||0)-(a.relevanceScore||0) : sort.value === 'players' ? (b.currentPlayers||0)-(a.currentPlayers||0) : sort.value === 'owners' ? (b.estimatedOwners||0)-(a.estimatedOwners||0) : sort.value === 'rating' ? (b.steamUserScore??-1)-(a.steamUserScore??-1) || (b.steamReviewCount||0)-(a.steamReviewCount||0) : (b.relevanceScore||0)-(a.relevanceScore||0) || (b.currentPlayers||0)-(a.currentPlayers||0));
  cards.replaceChildren();
  const totalPages=Math.ceil(visible.length/pageSize);
  currentPage=Math.max(1,Math.min(currentPage,totalPages||1));
  visible.slice((currentPage-1)*pageSize,currentPage*pageSize).forEach(game => {
    const button=document.createElement('a'); button.className='card'; button.href=`game.html?game=${encodeURIComponent(game.slug)}`; button.setAttribute('aria-label',`Ver página de ${game.name}`);
    const cover=document.createElement('div'); cover.className=`cover cover-${game.art}`;
    const cardImage=game.cardImageUrl||game.coverFallbackUrl||game.coverUrl;
    if(cardImage){const image=document.createElement('img');image.className='cover-image';image.src=cardImage;image.alt='';image.loading='lazy';image.decoding='async';cover.classList.add('has-image');image.addEventListener('error',()=>{if(game.coverFallbackUrl && image.src!==game.coverFallbackUrl)image.src=game.coverFallbackUrl;else if(game.coverUrl && image.src!==game.coverUrl)image.src=game.coverUrl;else{image.remove();cover.classList.remove('has-image');coverName.textContent=game.name;}});cover.append(image);}
    const coverName=document.createElement('span'); coverName.className='cover-name'; coverName.textContent=cardImage?'':game.name; cover.append(coverName);
    const body=document.createElement('div'); body.className='card-body';
    const top=document.createElement('div'); top.className='card-top';
    const titleBox=document.createElement('div'); const title=document.createElement('p'); title.className='card-title'; title.textContent=game.name; const meta=document.createElement('p'); meta.className='card-platform'; meta.textContent=`Lanzado en: ${platformSummary(game)}`;meta.title=`Plataformas de lanzamiento: ${gamePlatforms(game).join(', ')}`;
    if(game.steamUserScore!=null){const rating=document.createElement('span');rating.className='card-rating';rating.textContent=`Usuarios ${game.steamUserScore}%`;rating.setAttribute('aria-label',`Valoración de usuarios de Steam: ${game.steamUserScore}%`);rating.title='Votos de usuarios de Steam, vía SteamSpy';meta.append(rating);}
    titleBox.append(title,meta);
    const storeCount=new Set((game.offers||[]).map(offer=>offer.store)).size;
    if(storeCount>1){const count=document.createElement('span');count.className='card-store-count';count.textContent=`${storeCount} tiendas`;titleBox.append(count);}
    const badge=document.createElement('span'); badge.className='discount'; badge.textContent=game.price==null?'Sin precio':game.price===0?'Gratis':discount(game)>0?`−${discount(game)}%`:'Precio actual';if(game.price==null)badge.classList.add('is-missing');top.append(titleBox,badge);
    const bottom=document.createElement('div'); bottom.className='card-bottom'; const store=document.createElement('span');store.className='card-store';const storeName=document.createElement('span');storeName.className='store-visible-name';storeName.textContent=`PC · ${game.store}`;store.append(storeMark(game.store),storeName); const price=document.createElement('strong'); price.textContent=money(game.price,game.currency);price.setAttribute('aria-label',`Precio de PC: ${price.textContent}`);bottom.append(store,price);
    body.append(top,bottom); button.append(cover,body); attachCardPreview(button,cover,body,game); cards.append(button);
  });
  empty.hidden=visible.length>0;
  renderPagination(visible.length);
}
function attachCardPreview(card,cover,body,game){
  const shots = (game.screenshots || []).filter(shot => shot.url).slice(0,6);
  if(!shots.length) return;
  const images = [0,1].map(() => {
    const image = document.createElement('img');
    image.className = 'card-preview-image';
    image.alt = '';
    image.decoding = 'async';
    cover.append(image);
    return image;
  });
  const progress = document.createElement('span');
  progress.className = 'card-preview-progress';
  progress.setAttribute('aria-hidden','true');
  progress.hidden = shots.length < 2;
  const progressFill = document.createElement('span');
  progressFill.className = 'card-preview-progress-fill';
  progress.append(progressFill);
  cover.append(progress);
  const copy = document.createElement('div');copy.className = 'preview-description';
  const title = document.createElement('strong');title.textContent = 'Descripción original (inglés)';
  const description = document.createElement('span');description.textContent = game.description || 'Explora las capturas y ofertas de este juego.';
  copy.append(title,description);cover.append(copy);
  let currentLayer = -1,slideIndex = 0,timer = null,pressTimer = null,loadToken = 0;
  let startX = 0,startY = 0,longPressed = false,suppressClick = false,active = false;
  let reducedMotion = false;
  function restartProgress(){
    progressFill.classList.remove('is-running');
    if(reducedMotion || shots.length < 2) return;
    void progressFill.offsetWidth;
    progressFill.classList.add('is-running');
  }
  function showSlide(nextIndex){
    window.clearTimeout(timer);
    const layer = currentLayer === 0 ? 1 : 0;
    const image = images[layer];
    const token = ++loadToken;
    let settled = false;
    function reveal(){
      if(settled || !active || token !== loadToken) return;
      settled = true;
      image.classList.add('is-visible');
      if(currentLayer >= 0) images[currentLayer].classList.remove('is-visible');
      currentLayer = layer;
      slideIndex = nextIndex;
      restartProgress();
      if(!reducedMotion && shots.length > 1){
        timer = window.setTimeout(() => showSlide((slideIndex + 1) % shots.length),5000);
      }
    }
    image.onload = reveal;
    image.onerror = () => {
      if(!active || token !== loadToken) return;
      timer = window.setTimeout(() => showSlide((nextIndex + 1) % shots.length),5000);
    };
    image.src = shots[nextIndex].url;
    if(image.complete && image.naturalWidth > 0) reveal();
  }
  function show(){
    if(active) return;
    active = true;
    reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce), (hover: none)').matches;
    currentLayer = -1;
    card.classList.add('is-previewing');
    showSlide(0);
  }
  function hide(){
    window.clearTimeout(pressTimer);
    window.clearTimeout(timer);
    pressTimer = null;
    timer = null;
    loadToken++;
    active = false;
    longPressed = false;
    progressFill.classList.remove('is-running');
    images.forEach(image => image.classList.remove('is-visible'));
    card.classList.remove('is-previewing');
  }
  card.addEventListener('focus',show);card.addEventListener('blur',hide);
  cover.addEventListener('pointerenter',event => {if(event.pointerType === 'mouse') show();});
  cover.addEventListener('pointerleave',event => {if(event.pointerType === 'mouse') hide();});
  cover.addEventListener('pointerdown',event => {if(event.pointerType === 'mouse') return;startX = event.clientX;startY = event.clientY;pressTimer = window.setTimeout(() => {longPressed = true;show();},550);});
  cover.addEventListener('pointermove',event => {if(pressTimer && Math.hypot(event.clientX-startX,event.clientY-startY)>12){window.clearTimeout(pressTimer);pressTimer = null;}});
  cover.addEventListener('pointerup',() => {window.clearTimeout(pressTimer);pressTimer = null;if(longPressed){suppressClick = true;hide();window.setTimeout(() => {suppressClick = false;},700);}});
  cover.addEventListener('pointercancel',hide);
  cover.addEventListener('contextmenu',event => {if(longPressed) event.preventDefault();});
  card.addEventListener('click',event => {if(suppressClick){event.preventDefault();suppressClick = false;}});
}
function updateOffers(){
  render();
  if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches && typeof cards.animate === 'function')
    cards.animate([{opacity:.45,transform:'scale(.985)',filter:'blur(3px)'},{opacity:1,transform:'scale(1)',filter:'blur(0)'}],{duration:230,easing:'ease-out'});
}
function searchMatches(){
  const term=search.value.trim().toLocaleLowerCase('es');
  return term ? games.filter(game=>[game.name,...gamePlatforms(game),game.store].some(value=>value.toLocaleLowerCase('es').includes(term))) : games.slice(0,5);
}
function updateSearchPanel(){
  const matches=searchMatches().slice(0,12);
  searchPanel.replaceChildren();
  const heading=document.createElement('p');heading.className='search-panel-heading';heading.textContent=catalogSnapshot?`${games.length} juegos`:'Juegos para explorar';searchPanel.append(heading);
  if (!matches.length){const none=document.createElement('p');none.className='search-none';none.textContent='No encontramos juegos con ese nombre.';searchPanel.append(none);}
  matches.forEach(game=>{
    const link=document.createElement('a');link.className='search-result';link.href=`game.html?game=${encodeURIComponent(game.slug)}`;
    const art=document.createElement('span');art.className=`search-art cover-${game.art}`;art.textContent=game.name.slice(0,1);
    if(game.coverUrl){const image=document.createElement('img');image.src=game.coverUrl;image.alt='';image.loading='lazy';image.addEventListener('error',()=>{if(game.coverFallbackUrl && image.src!==game.coverFallbackUrl)image.src=game.coverFallbackUrl;else{image.remove();art.classList.remove('has-image');art.textContent=game.name.slice(0,1);}});art.textContent='';art.classList.add('has-image');art.append(image);}
    const info=document.createElement('span');info.className='search-info';const name=document.createElement('strong');name.textContent=game.name;const meta=document.createElement('small');meta.textContent=platformSummary(game);info.append(name,meta);
    const price=document.createElement('span');price.className='search-price';price.textContent=money(game.price,game.currency);
    link.append(art,info,price);searchPanel.append(link);
  });
  searchPanel.hidden=false;search.setAttribute('aria-expanded','true');
}
function showOrbGame(game,loadFresh=false){
  selectedOrbGame=game;
  orbGames.querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.slug===game.slug)));
  document.getElementById('selected-game-name').textContent=game.name;
  const gameLink=document.getElementById('selected-game-link');
  gameLink.href='game.html?game='+encodeURIComponent(game.slug);
  gameLink.setAttribute('aria-label','Ver ficha de '+game.name);
  const candidates=game.offers?.length ? game.offers : game.price==null ? [] : [{store:game.store,price:game.price,currency:game.currency}];
  const offers=candidates.filter((offer,index)=>candidates.findIndex(other=>other.store===offer.store)===index);
  const rows=document.querySelectorAll('.price-glass .glass-highlight, .price-glass .glass-row');
  rows.forEach((row,index)=>{const offer=offers[index];row.hidden=!offer;if(offer){row.querySelector('strong').textContent=money(offer.price,offer.currency);const label=row.querySelector('span');const name=document.createElement('span');name.className='store-visible-name';name.textContent=offer.store;label.replaceChildren(storeMark(offer.store),name);if(Math.abs(offer.price-offers[0].price)<.005){const best=document.createElement('em');best.textContent='MEJOR PRECIO';label.append(best);}}});
  const panel=document.querySelector('.price-glass');panel.classList.remove('panel-pulse');void panel.offsetWidth;panel.classList.add('panel-pulse');
  if(loadFresh && catalogSnapshot && game.steamAppId){
    fetchGameOffers(game.steamAppId).then(offers => {
      if(!offers.length || selectedOrbGame!==game) return;
      const best=offers[0];
      Object.assign(game,{offers,store:best.store,price:best.price,regular:best.regular,currency:'USD'});
      showOrbGame(game);
    }).catch(() => {
      // Keep the published reference price if the live request is unavailable.
    });
  }
}
function buildOrb(){
  const rings = [{name:'outer',radius:40,angles:[-45,45,135,225]},{name:'inner',radius:13,angles:[0,180]}];
  const featured = [...games].sort((a,b) => (b.relevanceScore || 0) - (a.relevanceScore || 0)).slice(0,6);
  const ringElements = rings.map(ring => {
    const element = document.createElement('div');element.className = 'orb-ring orb-ring--' + ring.name;
    const path = document.createElement('span');path.className = 'orb-ring-path';path.setAttribute('aria-hidden','true');
    element.append(path);orbGames.append(element);return element;
  });
  featured.forEach((game,index) => {
    const ringIndex = index < 4 ? 0 : 1, ring = rings[ringIndex];
    const angle = ring.angles[ringIndex === 0 ? index : index-4] * Math.PI / 180;
    const x = 50 + ring.radius * Math.cos(angle), y = 50 + ring.radius * Math.sin(angle);
    const button = document.createElement('button');button.type = 'button';button.className = 'orb-game orb-node';button.style.left = x + '%';button.style.top = y + '%';button.dataset.slug = game.slug;button.setAttribute('aria-label','Comparar precios de ' + game.name);
    const face = document.createElement('span');face.className = 'orb-game-face';
    const image = document.createElement('img');image.src = game.gameLogoUrl || ('https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/' + game.steamAppId + '/logo.png');image.alt = '';image.loading = 'eager';image.decoding = 'async';
    image.addEventListener('error',() => {if(game.cardImageUrl && image.src !== game.cardImageUrl){image.src = game.cardImageUrl;face.classList.add('is-art');}else{image.remove();face.textContent = game.name.slice(0,2).toUpperCase();}});
    face.append(image);
    const label = document.createElement('span');label.className = 'orb-game-title';label.textContent = game.name;
    button.append(face,label);
    button.addEventListener('pointerenter',event => {if(event.pointerType === 'mouse')ringElements[ringIndex].classList.add('is-paused');});
    button.addEventListener('pointerleave',event => {if(event.pointerType === 'mouse')ringElements[ringIndex].classList.remove('is-paused');});
    button.addEventListener('focus',() => {if(button.matches(':focus-visible'))ringElements[ringIndex].classList.add('is-paused');});
    button.addEventListener('blur',() => ringElements[ringIndex].classList.remove('is-paused'));
    button.addEventListener('click',() => {
      showOrbGame(game,true);
      button.classList.add('is-tapped');
      window.setTimeout(() => button.classList.remove('is-tapped'),650);
    });
    ringElements[ringIndex].append(button);
  });
  if(featured.length) showOrbGame(featured[0]);
}
function closeSearchPanel(){searchPanel.hidden=true;search.setAttribute('aria-expanded','false');}
search.addEventListener('focus',updateSearchPanel);
search.addEventListener('input',updateSearchPanel);
search.addEventListener('keydown',event=>{if(event.key==='Escape'){closeSearchPanel();search.blur();}});
document.addEventListener('click',event=>{if(!document.getElementById('header-search').contains(event.target))closeSearchPanel();});
sort.addEventListener('change',()=>{currentPage=1;updateOffers();});
pageSizeSelect.addEventListener('change',()=>{const size=Number(pageSizeSelect.value);if(!allowedPageSizes.includes(size))return;pageSize=size;currentPage=1;localStorage.setItem('nexo-page-size',String(size));updateOffers();});
document.addEventListener('nexo:currency',()=>{updatePriceInputs();render();if(selectedOrbGame)showOrbGame(selectedOrbGame);if(!searchPanel.hidden)updateSearchPanel();});
document.getElementById('header-search').addEventListener('submit',event=>{event.preventDefault();if(!search.value.trim()){updateSearchPanel();return;}const first=searchMatches()[0];if(first)location.href=`game.html?game=${encodeURIComponent(first.slug)}`;});
render();
buildOrb();
window.addEventListener('pageshow',event => {if(event.persisted) location.reload();});
if(liveSnapshot){
  document.querySelector('.demo-pill').textContent=catalogSnapshot?'DATOS DE FUENTES':'PILOTO CON DATOS';
  const captured=new Intl.DateTimeFormat('es-CR',{dateStyle:'short',timeStyle:'short',timeZone:'America/Costa_Rica'}).format(new Date(liveSnapshot.capturedAt));
  const metricValues=document.querySelectorAll('.metric-list strong');
  metricValues[0].textContent=`${games.length} juegos`;metricValues[1].textContent=String(new Set(games.flatMap(game=>(game.offers||[]).map(offer=>offer.store))).size);metricValues[2].textContent=captured;
  document.querySelector('#metrics-title + p').textContent=catalogSnapshot?'Explora el catálogo y compara precios donde hay varias ofertas disponibles.':'Piloto de comparación de precios.';
}
