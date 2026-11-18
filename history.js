// Compare only dated price observations for the game shown on this page.
(async()=>{
  const section=document.getElementById('historial');
  if(!section || typeof game==='undefined' || !game) return;
  const status=document.getElementById('history-count');
  const current=document.getElementById('history-current');
  const minimum=document.getElementById('history-minimum');
  const start=document.getElementById('history-start');
  const end=document.getElementById('history-end');
  const svg=document.getElementById('history-svg');
  const seriesGroup=document.getElementById('history-series');
  const legend=document.getElementById('history-legend');
  const empty=document.getElementById('history-empty');
  const ns='http://www.w3.org/2000/svg';
  const colors=['#b8ff5c','#6ccff6','#ffbd69','#da91ff','#ff8080','#78e2bd','#f4de79','#91aaff','#f78ec5','#d0d8d0'];
  const dateLabel=value=>new Intl.DateTimeFormat('es-CR',{day:'numeric',month:'short',year:'numeric'}).format(new Date(value));
  const node=(tag,attributes={})=>{const element=document.createElementNS(ns,tag);Object.entries(attributes).forEach(([key,value])=>element.setAttribute(key,String(value)));return element;};
  let entries=[];
  function render(){
    seriesGroup.replaceChildren();legend.replaceChildren();
    const all=entries.flatMap(([,points])=>points);
    if(!all.length){
      status.textContent='Sin capturas';current.textContent='—';minimum.textContent='—';start.textContent='—';end.textContent='—';
      empty.textContent='Todavía no hay observaciones de precios para este juego.';empty.hidden=false;
      svg.setAttribute('aria-label',`Sin historial de precios para ${game.name}`);return;
    }
    const times=all.map(point=>Date.parse(point.at));
    const first=Math.min(...times),last=Math.max(...times);
    const prices=all.map(point=>point.price),low=Math.min(...prices),high=Math.max(...prices);
    const padding=high===low?Math.max(1,high*.08):(high-low)*.16;
    const floor=Math.max(0,low-padding),ceiling=high+padding;
    const xy=point=>({x:first===last?260:18+(Date.parse(point.at)-first)/(last-first)*484,y:175-(point.price-floor)/(ceiling-floor)*150});
    entries.forEach(([store,points],index)=>{
      const color=colors[index%colors.length];
      const positions=points.map(xy);
      const group=node('g',{'data-store':store});
      if(positions.length>1){
        const path=positions.map((position,i)=>`${i?'L':'M'}${position.x.toFixed(2)} ${position.y.toFixed(2)}`).join(' ');
        group.append(node('path',{class:'history-series-line',d:path,stroke:color}));
      }
      positions.forEach((position,i)=>{
        const dot=node('circle',{class:'history-dot',cx:position.x.toFixed(2),cy:position.y.toFixed(2),r:i===positions.length-1?5:3.5,fill:color});
        const title=node('title');title.textContent=`${store} · ${dateLabel(points[i].at)} · ${money(points[i].price,'USD')}`;
        dot.append(title);group.append(dot);
      });
      seriesGroup.append(group);
      const item=document.createElement('span');item.className='history-legend-item';
      const swatch=document.createElement('i');swatch.className='history-legend-swatch';swatch.style.background=color;swatch.setAttribute('aria-hidden','true');
      const label=document.createElement('span');label.textContent=store;
      const value=document.createElement('strong');value.textContent=money(points.at(-1).price,'USD');
      item.append(swatch,label,value);legend.append(item);
    });
    const latestOffers=entries.map(([,points])=>points.at(-1).price);
    current.textContent=money(Math.min(...latestOffers),'USD');minimum.textContent=money(low,'USD');
    status.textContent=`${all.length} ${all.length===1?'captura':'capturas'} · ${entries.length} ${entries.length===1?'tienda':'tiendas'}`;
    start.textContent=dateLabel(new Date(first));end.textContent=dateLabel(new Date(last));
    empty.hidden=entries.some(([,points])=>points.length>1);
    if(!empty.hidden)empty.textContent='Hay una captura por tienda; las líneas aparecerán con nuevas observaciones.';
    svg.setAttribute('aria-label',`Historial de ${game.name}: ${entries.length} tiendas y ${all.length} capturas`);
  }
  try{
    const response=await fetch('data/price-history.json',{cache:'no-cache'});
    if(!response.ok)throw new Error(`History HTTP ${response.status}`);
    const snapshot=await response.json();
    if(snapshot.currency!=='USD'||!snapshot.games)throw new Error('Invalid history');
    entries=Object.entries(snapshot.games[String(game.steamAppId)]||{}).map(([store,points])=>[store,points.filter(point=>Number.isFinite(point.price)&&Number.isFinite(Date.parse(point.at))).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at))]).filter(([,points])=>points.length).sort((a,b)=>a[1].at(-1).price-b[1].at(-1).price||a[0].localeCompare(b[0]));
    document.addEventListener('nexo:currency',render);
    render();
  }catch(error){
    status.textContent='Sin historial';empty.textContent='No se pudo cargar el historial de precios.';empty.hidden=false;
    console.error('NEXO price history:',error);
  }
})();
