// The site remains fully usable when animation or IntersectionObserver is unavailable.
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const pageLoader = document.getElementById('page-loader');
if (pageLoader) {
  // Navigation starts immediately; the overlay only covers the page's own initialization.
  let finished = false;
  const finishLoading = () => {
    if (finished) return;
    finished = true;
    requestAnimationFrame(() => {
      pageLoader.classList.add('is-done');
      pageLoader.addEventListener('transitionend', () => pageLoader.remove(), {once:true});
      setTimeout(() => pageLoader.remove(), 700);
    });
  };
  if (document.readyState === 'complete') finishLoading();
  else window.addEventListener('load', finishLoading, {once:true});
  setTimeout(finishLoading, 2500);
}
if (!reduceMotion.matches) {
  document.documentElement.classList.add('motion-ready');
  if ('IntersectionObserver' in window) {
    const sections = document.querySelectorAll('.insight, .metrics, .game-section, .related');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, {threshold: 0.08, rootMargin: '0px 0px 60px 0px'});
    sections.forEach(section => { section.classList.add('reveal'); observer.observe(section); });
  }
}
