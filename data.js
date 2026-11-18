const liveSnapshot = window.NEXO_LIVE_DATA || null;
const catalogSnapshot = window.NEXO_CATALOG || null;
const catalogGames = catalogSnapshot?.games || [];
const catalogByAppId = new Map(catalogGames.map(game=>[game.steamAppId,game]));
const catalogByName = new Map(catalogGames.map(game=>[game.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,''),game]));
const liveGames = liveSnapshot?.games || [];
const observedOffersKey = 'nexo-observed-offers-v1';
const observedOffersTtl = 30 * 60 * 1000;
const validObservedOffer = offer => offer && typeof offer.store === 'string' && Number.isFinite(offer.price) && offer.price >= 0 && Number.isFinite(offer.regular) && offer.regular >= offer.price && offer.currency === 'USD' && typeof offer.url === 'string' && offer.url.startsWith('https://www.cheapshark.com/redirect?dealID=');
function readObservedOffers(){
  try {
    const saved = JSON.parse(localStorage.getItem(observedOffersKey) || '{}');
    if(!saved || typeof saved !== 'object') return {};
    const now = Date.now();
    return Object.fromEntries(Object.entries(saved).filter(([id,entry]) =>
      /^\d+$/.test(id) && entry && Number.isFinite(entry.time) && now - entry.time >= 0 && now - entry.time < observedOffersTtl &&
      Array.isArray(entry.offers) && entry.offers.length > 0 && entry.offers.every(validObservedOffer)
    ).slice(-100));
  } catch {
    return {};
  }
}
const observedOffers = readObservedOffers();
function withObservedOffers(game,offers){
  if(!Array.isArray(offers) || !offers.length || !offers.every(validObservedOffer)) return game;
  const byStore = new Map((game.offers || []).map(offer => [offer.store,offer]));
  offers.forEach(offer => byStore.set(offer.store,offer));
  const sorted = [...byStore.values()].sort((a,b) => a.price - b.price || a.store.localeCompare(b.store));
  const best = sorted[0];
  return {...game,offers:sorted,store:best.store,price:best.price,regular:best.regular,currency:'USD'};
}
function rememberObservedOffers(steamAppId,offers){
  if(!offers.length) return;
  observedOffers[String(steamAppId)] = {time:Date.now(),offers};
  const recent = Object.entries(observedOffers).sort((a,b) => a[1].time - b[1].time).slice(-100);
  try {localStorage.setItem(observedOffersKey,JSON.stringify(Object.fromEntries(recent)));}
  catch { /* Browsers without storage still show the current page's offers. */ }
  document.dispatchEvent(new CustomEvent('nexo:offers',{detail:{steamAppId,offers}}));
}
const combined = catalogGames.length ? [
  ...liveGames.map(game=>{
    const key=game.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
    const liveAppId=game.steamAppId||Number(game.coverUrl?.match(/\/apps\/(\d+)\//)?.[1]);
    const metadata=catalogByAppId.get(liveAppId)||catalogByName.get(key)||{};
    const byStore = new Map((metadata.offers || []).map(offer => [offer.store,offer]));
    (game.offers || []).forEach(offer => byStore.set(offer.store,offer));
    const offers = [...byStore.values()].sort((a,b) => a.price - b.price || a.store.localeCompare(b.store));
    const best = offers[0];
    return {...metadata,...game,screenshots:metadata.screenshots||[],achievements:metadata.achievements??null,hours:metadata.hours??null,extras:metadata.extras??null,completion:metadata.completion??null,hltbId:metadata.hltbId??null,offers,store:best?.store||game.store,price:best?.price??game.price,regular:best?.regular??game.regular,currency:'USD'};
  }),
  ...catalogGames.filter(game=>!liveGames.some(live=>live.steamAppId===game.steamAppId || Number(live.coverUrl?.match(/\/apps\/(\d+)\//)?.[1])===game.steamAppId || live.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'')===game.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'')))
] : liveGames;
const games = combined.filter(game=>!catalogSnapshot&&!liveSnapshot || game.price!=null && Number(game.price)>0 && game.offers?.some(offer=>offer.url && offer.price!=null)).map(game => {
  return withObservedOffers(game,observedOffers[String(game.steamAppId)]?.offers);
});
const liveFresh = !!liveSnapshot && Date.now()-Date.parse(liveSnapshot.capturedAt) < 48*60*60*1000;
// When a real snapshot exists, Hacienda's dated rates replace the illustrative rates.
const demoRatesFromEUR = {EUR:1, USD:liveSnapshot?.fx?.eur_usd || 1.08, CRC:(liveSnapshot?.fx?.eur_usd || 1.08)*(liveSnapshot?.fx?.usd_crc || 510)};
const supportedCurrencies = ['EUR','USD','CRC'];
let selectedCurrency = supportedCurrencies.includes(localStorage.getItem('nexo-currency')) ? localStorage.getItem('nexo-currency') : 'EUR';
const money = (value, origin='EUR') => {
  if(value==null || !Number.isFinite(Number(value))) return 'Precio no disponible';
  if(Number(value)===0) return 'Gratis';
  const eur = origin==='USD' ? value/demoRatesFromEUR.USD : origin==='CRC' ? value/demoRatesFromEUR.CRC : value;
  return new Intl.NumberFormat(selectedCurrency==='USD'?'en-US':'es-CR',{style:'currency',currency:selectedCurrency,maximumFractionDigits:selectedCurrency==='CRC'?0:2}).format(eur*demoRatesFromEUR[selectedCurrency]);
};
const currencyLabel=document.createElement('label');currencyLabel.className='currency-control';
const currencyCaption=document.createElement('span');currencyCaption.textContent=liveSnapshot?'Moneda':'Moneda demo';currencyCaption.className='currency-caption';currencyLabel.append(currencyCaption);
const currencySelect=document.createElement('select');currencySelect.setAttribute('aria-label','Moneda de visualización');
for(const code of supportedCurrencies){const option=document.createElement('option');option.value=code;option.textContent=code;currencySelect.append(option);}
currencySelect.value=selectedCurrency;currencyLabel.append(currencySelect);
const header=document.querySelector('.site-header');header.insertBefore(currencyLabel,header.querySelector('.header-search, .back-search'));
currencySelect.addEventListener('change',()=>{selectedCurrency=currencySelect.value;localStorage.setItem('nexo-currency',selectedCurrency);document.dispatchEvent(new Event('nexo:currency'));});
const discount = game => game.price!=null && game.regular>0 ? Math.max(0,Math.round((1-game.price/game.regular)*100)) : 0;
// CheapShark hosts the store marks used by its store directory. Keep the text
// fallback for shops outside that directory or when an image fails to load.
const storeLogoIds = {'Steam':0,'GamersGate':1,'GreenManGaming':2,'GOG':6,'Humble Store':10,'Uplay':12,'Fanatical':14,'WinGameStore':20,'GameBillet':22,'Epic Games Store':24,'Gamesplanet':26,'IndieGala':29,'DreamGame':34};
function storeMark(name){
  const mark=document.createElement('span');mark.className='store-mark';mark.setAttribute('aria-label',name);
  const fallback=document.createElement('span');fallback.className='store-mark-fallback';fallback.textContent=name;
  const id=storeLogoIds[name];
  if(id!=null){const logo=document.createElement('img');logo.src=`https://www.cheapshark.com/img/stores/logos/${id}.png`;logo.alt=name;logo.loading='lazy';logo.decoding='async';logo.addEventListener('error',()=>{logo.remove();fallback.hidden=false;});fallback.hidden=true;mark.append(logo);}
  mark.append(fallback);return mark;
}

const cheapSharkEndpoint = 'https://www.cheapshark.com/api/1.0/';
const gameOffersCache = new Map();
const pendingGameOffers = new Map();
let cheapSharkStoresPromise = null;
async function cheapSharkJson(path){
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(),10000);
  try {
    const response = await fetch(cheapSharkEndpoint + path,{signal:controller.signal});
    if(!response.ok) throw new Error('CheapShark returned ' + response.status);
    return await response.json();
  } finally {
    window.clearTimeout(timeout);
  }
}
function cheapSharkStores(){
  if(!cheapSharkStoresPromise){
    cheapSharkStoresPromise = cheapSharkJson('stores').then(rows => {
      if(!Array.isArray(rows)) throw new Error('Invalid store list');
      return new Map(rows.filter(row => row.isActive === 1).map(row => [String(row.storeID),row.storeName]));
    }).catch(error => {cheapSharkStoresPromise = null;throw error;});
  }
  return cheapSharkStoresPromise;
}
async function fetchGameOffers(steamAppId){
  const id = Number(steamAppId);
  if(!Number.isInteger(id) || id <= 0) return [];
  const cached = gameOffersCache.get(id);
  if(cached && Date.now() - cached.time < 30 * 60 * 1000) return cached.offers;
  if(pendingGameOffers.has(id)) return pendingGameOffers.get(id);
  const request = Promise.all([
    cheapSharkStores(),
    cheapSharkJson('deals?steamAppID=' + encodeURIComponent(id) + '&limit=60'),
  ]).then(([stores,rows]) => {
    if(!Array.isArray(rows)) throw new Error('Invalid deal list');
    const byStore = new Map();
    for(const row of rows){
      if(String(row.steamAppID) !== String(id)) continue;
      const store = stores.get(String(row.storeID));
      const price = Number(row.salePrice),regular = Number(row.normalPrice);
      if(!store || !row.dealID || !Number.isFinite(price) || !Number.isFinite(regular) || price < 0 || regular <= 0 || price > regular) continue;
      const offer = {store,price,regular,currency:'USD',url:'https://www.cheapshark.com/redirect?dealID=' + row.dealID,capturedAt:new Date().toISOString()};
      if(!byStore.has(store) || price < byStore.get(store).price) byStore.set(store,offer);
    }
    const offers = [...byStore.values()].sort((a,b) => a.price - b.price || a.store.localeCompare(b.store));
    gameOffersCache.set(id,{time:Date.now(),offers});
    rememberObservedOffers(id,offers);
    return offers;
  }).finally(() => pendingGameOffers.delete(id));
  pendingGameOffers.set(id,request);
  return request;
}
window.NEXO_FETCH_GAME_OFFERS = fetchGameOffers;
