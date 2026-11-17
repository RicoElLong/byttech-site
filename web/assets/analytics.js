(() => {
  const endpoint = new URL('/api/analytics/event', location.origin);
  let visitor;
  try {
    visitor = localStorage.getItem('byttech.analytics.visitor');
    if (!visitor) {
      visitor = crypto.randomUUID();
      localStorage.setItem('byttech.analytics.visitor', visitor);
    }
  } catch {
    return;
  }

  function send(kind, target = '') {
    const body = JSON.stringify({
      id: crypto.randomUUID(), visitor, kind, target, page: location.pathname,
    });
    if (!navigator.sendBeacon?.(endpoint, body)) {
      fetch(endpoint, { method: 'POST', body, keepalive: true }).catch(() => {});
    }
  }

  send('view');
  function recordClick(event) {
    if (!event.isTrusted || (event.type === 'auxclick' && event.button !== 1)) return;
    const link = event.target.closest?.('a[href]');
    if (!link) return;
    const url = new URL(link.href, location.href);
    if (url.protocol === 'tel:') {
      send('phone');
    } else if (url.origin === location.origin && url.hash === '#quiz' && !link.hasAttribute('data-service-problem')) {
      send('master');
    } else if (['https:', 'http:'].includes(url.protocol)) {
      const target = url.origin === location.origin ? url.pathname + url.hash.split('?')[0] : url.hostname;
      send('link', target.slice(0, 240));
    }
  }

  document.addEventListener('click', recordClick, true);
  document.addEventListener('auxclick', recordClick, true);
})();
