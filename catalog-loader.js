// GitHub Pages serves a JSON projection; SQLite remains the catalog's source of truth.
(async () => {
  try {
    const response = await fetch('data/catalog.json', {cache: 'no-cache'});
    if (!response.ok) throw new Error('Catalog HTTP ' + response.status);
    const catalog = await response.json();
    if (!Array.isArray(catalog.games) || catalog.games.length < 500) {
      throw new Error('Incomplete catalog');
    }
    window.NEXO_CATALOG = catalog;
    for (const placeholder of document.querySelectorAll('[data-after-catalog]')) {
      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = placeholder.getAttribute('data-after-catalog');
        script.onload = resolve;
        script.onerror = () => reject(new Error('Unable to load ' + script.src));
        placeholder.replaceWith(script);
      });
    }
  } catch (error) {
    document.getElementById('page-loader')?.remove();
    const notice = document.createElement('p');
    notice.className = 'catalog-load-error';
    notice.setAttribute('role', 'alert');
    notice.textContent = 'No se pudo cargar el catálogo. Recarga la página para intentarlo de nuevo.';
    document.body.prepend(notice);
    console.error('NEXO catalog:', error);
  }
})();
