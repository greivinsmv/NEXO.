const assert = require('node:assert/strict');
const {chromium} = require('playwright-core');

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_BIN,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });
  try {
    const desktop = await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'no-preference'});
    const errors = [];
    desktop.on('pageerror', error => errors.push(error.message));
    const imageFixture=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lGQAAAAASUVORK5CYII=','base64');
    await desktop.route(/https:\/\/[^/]*steamstatic\.com\//, route => route.fulfill({
      status:200,contentType:'image/png',body:imageFixture
    }));
    await desktop.route(/https:\/\/www\.cheapshark\.com\/img\/stores\/logos\//, route => route.fulfill({status:200,contentType:'image/png',body:imageFixture}));
    await desktop.route(/https:\/\/www\.cheapshark\.com\/api\/1\.0\//, route => {
      const url=new URL(route.request().url());
      const body=url.pathname.endsWith('/stores')
        ? [{storeID:'1',storeName:'Steam',isActive:1},{storeID:'7',storeName:'GOG',isActive:1}]
        : [
          {steamAppID:url.searchParams.get('steamAppID'),storeID:'1',salePrice:'39.99',normalPrice:'39.99',dealID:'test-steam'},
          {steamAppID:url.searchParams.get('steamAppID'),storeID:'7',salePrice:'20.00',normalPrice:'39.99',dealID:'test-gog'}
        ];
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
    });
    await desktop.goto('http://127.0.0.1:8765/index.html', {waitUntil:'domcontentloaded'});
    await desktop.locator('.card').first().waitFor();
    assert.ok(await desktop.locator('.card-rating').count()>0,'catalog cards should show the available user rating');
    assert.equal(await desktop.evaluate(() => window.NEXO_CATALOG.games.length),500,'catalog should load from JSON');
    assert.equal(await desktop.locator('#historial').count(),0,'history should be on game pages only');
    assert.equal(await desktop.locator('.site-header nav a[href="#metricas"]').textContent(),'Así funciona NEXO');
    const gogFilter=desktop.locator('#store-filter-options input[value="GOG"]');
    const storeOptions=await desktop.locator('#store-filter-options input').evaluateAll(inputs => inputs.map(input => ({name:input.value,count:Number(input.closest('label').querySelector('small').textContent)})));
    assert.ok(storeOptions.length>=10,'stores with catalog offers should be filterable');
    for(const store of storeOptions){
      const option=desktop.locator(`#store-filter-options input[value="${store.name}"]`);
      await option.check();
      assert.equal(Number((await desktop.locator('#page-summary').textContent()).match(/de (\d+) juegos/)[1]),store.count,`${store.name} filter count should match its results`);
      await option.uncheck();
    }
    await gogFilter.check();
    assert.ok(Number((await desktop.locator('#page-summary').textContent()).match(/de (\d+) juegos/)[1])>=100,'published GOG catalog should include many games on first visit');
    let foundIsaac=0;
    for(let page=0;page<10;page++){
      foundIsaac=await desktop.locator('.card').filter({hasText:'The Binding of Isaac: Rebirth'}).count();
      if(foundIsaac)break;
      const next=desktop.locator('#catalog-pagination button[aria-label="Página siguiente"]');
      if(await next.isDisabled())break;
      await next.click();
    }
    assert.ok(foundIsaac,'Isaac should appear in GOG without first opening its game page');
    await gogFilter.uncheck();
    await desktop.waitForTimeout(3200);
    assert.equal(await desktop.locator('.orb-ring--outer .orb-game').count(),4);
    assert.equal(await desktop.locator('.orb-ring--inner .orb-game').count(),2);
    const before = await desktop.locator('.orb-ring--outer .orb-game').first().boundingBox();
    await desktop.waitForTimeout(1200);
    const after = await desktop.locator('.orb-ring--outer .orb-game').first().boundingBox();
    assert.ok(Math.hypot(after.x-before.x,after.y-before.y)>2,'outer orbit should move');
    const featuredNode=desktop.locator('.orb-ring--outer .orb-game').first();
    await featuredNode.evaluate(el=>el.dispatchEvent(new PointerEvent('pointerenter',{pointerType:'mouse'})));
    assert.equal(await desktop.locator('.orb-ring--outer').evaluate(el=>getComputedStyle(el).animationPlayState),'paused','hovered orbit should pause');
    assert.equal(await desktop.locator('.orb-ring--inner').evaluate(el=>getComputedStyle(el).animationPlayState),'running','other orbit should keep moving');
    await featuredNode.evaluate(el=>el.click());
    const featuredSlug=await featuredNode.getAttribute('data-slug');
    assert.equal(await desktop.locator('#selected-game-link').evaluate(el=>el.tagName),'A','the entire price card should be a link');
    assert.ok((await desktop.locator('#selected-game-link').getAttribute('href')).includes(featuredSlug),'price panel should link to the selected game');
    assert.equal(await desktop.locator('.glass-game-link').count(),0,'the separate price button should be removed');
    await featuredNode.evaluate(el=>el.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'})));
    assert.equal(await desktop.locator('.orb-ring--outer').evaluate(el=>getComputedStyle(el).animationPlayState),'running','orbit should resume after pointer leaves');
    const logo = await desktop.locator('.card .store-mark img').first().evaluate(img => {
      const rect=img.getBoundingClientRect();return {width:rect.width,height:rect.height};
    });
    assert.ok(Math.abs(logo.width-logo.height)<1,'store logo must be square');
    await desktop.locator('#filter-multi-store').check();
    assert.ok(Number((await desktop.locator('#page-summary').textContent()).match(/de (\d+) juegos/)[1])>0,'multi-store filter should have results');
    await desktop.locator('#filter-multi-store').uncheck();
    assert.ok(await desktop.locator('#filter-genre option').count()>4,'genres should be populated');
    const playStationFilter=desktop.locator('.platform-option[data-platform="PlayStation"]');
    if(await playStationFilter.count()){
      await playStationFilter.click();
      assert.ok((await desktop.locator('#page-summary').textContent()).includes('juegos'),'console release filter should have results');
      assert.ok((await desktop.locator('.card').first().locator('.card-platform').textContent()).includes('PS'),'console release should appear on the card');
      await desktop.locator('.platform-option[data-platform="Todas"]').click();
      assert.ok((await desktop.locator('#catalog-count').textContent()).includes('precios de PC'),'catalog should identify the price platform');
    }
    const beforePrice = Number((await desktop.locator('#page-summary').textContent()).match(/de (\d+) juegos/)[1]);
    await desktop.locator('#filter-max').fill('10');
    const afterPrice = Number((await desktop.locator('#page-summary').textContent()).match(/de (\d+) juegos/)[1]);
    assert.ok(afterPrice>0 && afterPrice<beforePrice,'price filter should narrow results');
    await desktop.locator('#clear-filters').click();
    await desktop.locator('.card .cover').first().evaluate(el=>el.dispatchEvent(new PointerEvent('pointerenter',{pointerType:'mouse'})));
    assert.ok(await desktop.locator('.card').first().evaluate(card=>card.classList.contains('is-previewing')));
    const firstPreview=desktop.locator('.card').first().locator('.card-preview-image.is-visible');
    await firstPreview.waitFor({timeout:10000});
    const firstShot=await firstPreview.getAttribute('src');
    assert.ok(firstShot.includes('steam'));
    const progress=desktop.locator('.card').first().locator('.card-preview-progress-fill');
    const progressAtStart=await progress.evaluate(el=>new DOMMatrixReadOnly(getComputedStyle(el).transform).a);
    await desktop.waitForTimeout(850);
    const progressAfter=await progress.evaluate(el=>new DOMMatrixReadOnly(getComputedStyle(el).transform).a);
    assert.ok(progressAfter>progressAtStart,'preview progress should fill over time');
    await desktop.waitForFunction(first=>[...document.querySelectorAll('.card:first-child .card-preview-image.is-visible')].some(img=>img.getAttribute('src')!==first),firstShot,{timeout:7000});
    assert.ok((await desktop.locator('.preview-description').first().textContent()).length>40);
    assert.ok(await desktop.locator('.card').first().locator('.card-bottom').isVisible(),'price and store remain visible during preview');
    const href = await desktop.locator('.card').first().getAttribute('href');
    await desktop.goto('http://127.0.0.1:8765/'+href,{waitUntil:'domcontentloaded'});
    await desktop.waitForFunction(() => Boolean(document.getElementById('game-title')?.textContent.trim()));
    assert.ok((await desktop.locator('.game-lead').textContent()).length>40,'game description should be visible');
    assert.ok(await desktop.locator('.game-lead').isVisible());
    assert.equal(await desktop.locator('.description-label').textContent(),'Descripción original (inglés)');
    const firstSlide=desktop.locator('.gallery-slide').first();
    await firstSlide.click();
    assert.ok(await desktop.locator('#gallery-lightbox').evaluate(dialog=>dialog.open&&dialog.getAttribute('aria-modal')==='true'));
    const firstLightboxImage=await desktop.locator('#lightbox-image').getAttribute('src');
    await desktop.keyboard.press('ArrowRight');
    assert.notEqual(await desktop.locator('#lightbox-image').getAttribute('src'),firstLightboxImage,'arrow key should change lightbox image');
    await desktop.keyboard.press('Escape');
    assert.equal(await desktop.locator('#gallery-lightbox').evaluate(dialog=>dialog.open),false);
    assert.ok(await firstSlide.evaluate(slide=>slide===document.activeElement),'focus should return to the opened screenshot');
    await desktop.waitForFunction(() => /capturas/.test(document.getElementById('history-count')?.textContent||''));
    assert.ok(await desktop.locator('#history-legend .history-legend-item').count()>=1,'game history should show stores');
    await desktop.locator('#store-list a[href$="test-gog"]').waitFor({timeout:5000});
    assert.ok(await desktop.locator('#store-list .store-row').count()>=2,'opening a game should load offers from other stores');
    assert.equal(await desktop.locator('.game-intro .eyebrow').count(),0);
    assert.equal(await desktop.locator('#related-list a').count(),3);
    assert.ok(await desktop.evaluate(() => {
      const games=window.NEXO_CATALOG.games;
      const slug=new URL(location.href).searchParams.get('game');
      const current=games.find(item=>item.slug===slug);
      return [...document.querySelectorAll('#related-list a')].every(link=>{
        const other=games.find(item=>item.slug===new URL(link.href).searchParams.get('game'));
        return other && other.genres.some(genre=>current.genres.includes(genre));
      });
    }),'related games should share a genre');
    await desktop.goto('http://127.0.0.1:8765/game.html?game=elden-ring',{waitUntil:'domcontentloaded'});
    await desktop.waitForFunction(() => /capturas/.test(document.getElementById('history-count')?.textContent||''));
    assert.ok((await desktop.locator('#launch-platforms').textContent()).startsWith('Lanzado en:'),'release platforms should be identified as release data');
    assert.equal((await desktop.locator('#game-chips').textContent()).includes('Precios de PC'),true,'price platform should be explicit');
    assert.equal((await desktop.locator('.offer-panel .eyebrow').textContent()).includes('PC'),true,'best price must identify its platform');
    const expectedRating=await desktop.evaluate(()=>window.NEXO_CATALOG.games.find(item=>item.steamAppId===1245620)?.steamUserScore);
    assert.equal((await desktop.locator('#hero-steam-rating').textContent()).trim(),expectedRating==null?'Sin datos':`${expectedRating}%`,'Steam user score should match the catalog');
    assert.ok(await desktop.locator('#steam-rating-card').isVisible(),'Steam user rating should be visible beside the title');
    assert.ok(await desktop.locator('#metacritic-rating-card').isVisible(),'Metacritic should be visible beside the title when available');
    assert.ok(await desktop.locator('#store-list .offer-capture-time').count()>0,'store prices should show a capture date');
    assert.equal(await desktop.locator('#history-legend .history-legend-item').count(),9,'Elden Ring should show all nine stores');
    assert.equal(await desktop.locator('.history-series-line').count(),9,'each observed store should have its own line');
    await desktop.goto('http://127.0.0.1:8765/game.html?game=dayz-221100',{waitUntil:'domcontentloaded'});
    await desktop.waitForFunction(() => document.getElementById('main')?.hidden===false);
    const expectedDayzRating=await desktop.evaluate(()=>window.NEXO_CATALOG.games.find(item=>item.steamAppId===221100)?.steamUserScore);
    assert.equal((await desktop.locator('#hero-steam-rating').textContent()).trim(),expectedDayzRating==null?'Sin datos':`${expectedDayzRating}%`);
    const expectedDayzMetacritic=await desktop.evaluate(()=>window.NEXO_CATALOG.games.find(item=>item.steamAppId===221100)?.metacritic);
    assert.equal((await desktop.locator('#hero-metacritic').textContent()).trim(),expectedDayzMetacritic==null?'Sin datos':`${expectedDayzMetacritic}/100`,'missing Metacritic should be explained visibly');
    await desktop.goto('http://127.0.0.1:8765/game.html?game=rust-252490',{waitUntil:'domcontentloaded'});
    await desktop.waitForFunction(() => /capturas/.test(document.getElementById('history-count')?.textContent||''));
    assert.equal(await desktop.locator('#history-legend .history-legend-item').count(),2,'Rust should show both stores');
    const rustLines=await desktop.locator('.history-series-line').evaluateAll(lines=>lines.map(line=>line.parentElement.dataset.store).sort());
    const rustStoresWithTrend=await desktop.evaluate(async()=>{
      const history=await (await fetch('data/price-history.json')).json();
      return Object.entries(history.games['252490']||{}).filter(([,points])=>points.length>1).map(([store])=>store).sort();
    });
    assert.deepEqual(rustLines,rustStoresWithTrend,'only stores with multiple captures should show a trend');
    await desktop.goto('http://127.0.0.1:8765/game.html?game=the-binding-of-isaac-rebirth-250900',{waitUntil:'domcontentloaded'});
    await desktop.locator('#store-list a[href$="test-gog"]').waitFor({timeout:5000});
    assert.ok(await desktop.locator('#store-list .store-row').first().textContent().then(text=>text.includes('Ir a la tienda')));
    await desktop.locator('.site-header .logo').click();
    await desktop.locator('.card').first().waitFor();
    const gogOption=desktop.locator('#store-filter-options input[value="GOG"]');
    await gogOption.check();
    assert.ok(await desktop.locator('.card').filter({hasText:'The Binding of Isaac: Rebirth'}).count(),'a game observed at GOG should appear in the GOG catalog filter');
    assert.ok(Number((await desktop.locator('#page-summary').textContent()).match(/de (\d+) juegos/)[1])>=100,'the published GOG count should remain available');
    assert.deepEqual(errors,[],'desktop should have no JavaScript errors');

    const mobile = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'no-preference'});
    const mobileErrors=[];
    mobile.on('pageerror',error=>mobileErrors.push(error.message));
    await mobile.goto('http://127.0.0.1:8765/index.html',{waitUntil:'domcontentloaded'});
    await mobile.locator('.card').first().waitFor();
    assert.equal(await mobile.locator('#catalog-filters').evaluate(el=>el.open),false);
    assert.ok(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile must not overflow');
    await mobile.locator('#catalog-filters summary').click();
    assert.ok(await mobile.locator('#store-filter-options').evaluate(el=>el.scrollHeight>el.clientHeight),'store list should scroll within filters');
    const all = Number((await mobile.locator('#page-summary').textContent()).match(/de (\d+) juegos/)[1]);
    await mobile.locator('#filter-genre').selectOption('RPG');
    const filtered = Number((await mobile.locator('#page-summary').textContent()).match(/de (\d+) juegos/)[1]);
    assert.ok(filtered>0 && filtered<all,'genre filter should narrow results');
    const cover=mobile.locator('.card .cover').first();
    await cover.dispatchEvent('pointerdown',{pointerType:'touch',clientX:100,clientY:100});
    await mobile.waitForTimeout(650);
    assert.ok(await mobile.locator('.card').first().evaluate(card=>card.classList.contains('is-previewing')),'long press should open preview');
    assert.equal(await mobile.locator('.card-preview-progress').first().evaluate(el=>getComputedStyle(el).display),'none','mobile preview should not animate');
    await cover.dispatchEvent('pointerup',{pointerType:'touch',clientX:100,clientY:100});
    assert.ok(!await mobile.locator('.card').first().evaluate(card=>card.classList.contains('is-previewing')),'release should close preview');
    assert.deepEqual(mobileErrors,[],'mobile should have no JavaScript errors');
    console.log('NEXO UI smoke passed');
  } finally {
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exit(1);});
