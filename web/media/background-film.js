(() => {
  'use strict';
  const policy = window.matchMedia(
    '(min-width: 1024px) and (hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)'
  );
  let instance = null;
  let wantsPlayback = true;
  const eligible = () => policy.matches && !navigator.connection?.saveData;

  function syncPlayback() {
    const current = instance;
    if (!current) return;
    if (document.hidden || !wantsPlayback || current.failed) {
      current.video.pause();
      return;
    }
    const attempt = current.video.play();
    if (attempt?.catch) attempt.catch(() => {
      if (instance !== current) return;
      current.button.hidden = false;
      current.button.textContent = 'Включить фон';
      current.button.setAttribute('aria-pressed', 'false');
    });
  }

  function teardown() {
    if (!instance) return;
    const previous = instance;
    instance = null;
    previous.poster.onload = null;
    previous.poster.onerror = null;
    previous.video.pause();
    previous.video.removeAttribute('src');
    previous.video.removeAttribute('poster');
    previous.video.load();
    previous.film.remove();
    previous.button.remove();
    document.documentElement.removeAttribute('data-film');
  }

  function mount() {
    if (!eligible()) {
      teardown();
      return;
    }
    if (instance) return;
    const film = document.createElement('div');
    film.className = 'site-film';
    film.setAttribute('aria-hidden', 'true');
    const video = document.createElement('video');
    video.muted = true;
    video.defaultMuted = true;
    video.loop = true;
    video.playsInline = true;
    video.preload = 'auto';
    video.tabIndex = -1;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'film-toggle';
    button.textContent = wantsPlayback ? 'Пауза фона' : 'Включить фон';
    button.setAttribute('aria-pressed', 'false');
    button.hidden = wantsPlayback;
    const poster = new Image();
    const current = { film, video, button, poster, failed: false };
    instance = current;
    poster.onload = () => {
      if (instance !== current) return;
      film.style.backgroundImage = 'url("/media/byttech-poster.webp")';
      document.documentElement.setAttribute('data-film', 'poster');
    };
    video.addEventListener('playing', () => {
      if (instance !== current) return;
      film.classList.add('is-playing');
      button.hidden = false;
      button.textContent = 'Пауза фона';
      button.setAttribute('aria-pressed', 'true');
      document.documentElement.setAttribute('data-film', 'ready');
    });
    video.addEventListener('pause', () => {
      if (instance !== current) return;
      button.textContent = 'Включить фон';
      button.setAttribute('aria-pressed', 'false');
    });
    video.addEventListener('error', () => {
      if (instance !== current) return;
      current.failed = true;
      video.pause();
      video.hidden = true;
      button.hidden = true;
      // The already loaded still remains; if it also failed, retain the original site.
    });
    button.addEventListener('click', () => {
      wantsPlayback = video.paused;
      syncPlayback();
    });
    film.append(video);
    document.body.prepend(film);
    document.body.append(button);
    // No media URL is assigned before the desktop/motion/data policy passes.
    poster.src = '/media/byttech-poster.webp';
    video.poster = '/media/byttech-poster.webp';
    video.src = '/media/byttech-loop.mp4';
    syncPlayback();
  }

  policy.addEventListener('change', mount);
  navigator.connection?.addEventListener?.('change', mount);
  document.addEventListener('visibilitychange', syncPlayback);
  window.addEventListener('pagehide', () => instance?.video.pause());
  window.addEventListener('pageshow', syncPlayback);
  mount();
})();
