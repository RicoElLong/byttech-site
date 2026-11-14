const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('web/media/background-film.js', 'utf8');

function fixture({ eligible = true, saveData = false, rejectPlay = false } = {}) {
  const urls = [];
  class Target {
    listeners = new Map();
    addEventListener(name, fn) {
      const listeners = this.listeners.get(name) || [];
      listeners.push(fn); this.listeners.set(name, listeners);
    }
    emit(name) { for (const fn of this.listeners.get(name) || []) fn(); }
  }
  class Element extends Target {
    constructor(tag) {
      super(); this.tag = tag; this.attrs = new Map(); this.children = [];
      this.hidden = false; this.paused = true; this.style = {};
      this.classList = { add() {} };
    }
    setAttribute(key, value) { this.attrs.set(key, value); }
    removeAttribute(key) { this.attrs.delete(key); }
    append(child) { child.parent = this; this.children.push(child); }
    prepend(child) { child.parent = this; this.children.unshift(child); }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this); }
    set src(url) { this.attrs.set('src', url); urls.push([this.tag, url]); }
    set poster(url) { this.attrs.set('poster', url); }
    play() {
      if (rejectPlay) return Promise.reject(new Error('autoplay denied'));
      this.paused = false; this.emit('playing'); return Promise.resolve();
    }
    pause() { if (!this.paused) { this.paused = true; this.emit('pause'); } }
    load() {}
  }
  const policy = new Target(); policy.matches = eligible;
  const connection = new Target(); connection.saveData = saveData;
  const document = new Target();
  document.hidden = false; document.documentElement = new Element('html');
  document.body = new Element('body'); document.createElement = tag => new Element(tag);
  const window = new Target(); window.matchMedia = () => policy;
  class Image {
    set src(url) { urls.push(['image', url]); this.onload?.(); }
  }
  vm.runInNewContext(script, { window, document, navigator: { connection }, Image });
  const video = () => document.body.children.find(x => x.tag === 'div')?.children[0];
  const button = () => document.body.children.find(x => x.tag === 'button');
  return { urls, policy, connection, document, window, video, button };
}

(async () => {
  for (const options of [{ eligible: false }, { saveData: true }]) {
    const f = fixture(options);
    assert.equal(f.urls.length, 0, 'ineligible clients must receive no media URLs');
    assert.equal(f.document.body.children.length, 0);
  }
  const f = fixture();
  assert.equal(f.video().muted, true);
  assert.equal(f.video().loop, true);
  assert.equal(f.video().playsInline, true);
  assert.equal(f.video().paused, false);
  f.document.hidden = true; f.document.emit('visibilitychange');
  assert.equal(f.video().paused, true, 'hidden page pauses playback');
  f.document.hidden = false; f.document.emit('visibilitychange');
  assert.equal(f.video().paused, false);
  f.button().emit('click'); assert.equal(f.video().paused, true);
  f.document.hidden = true; f.document.emit('visibilitychange');
  f.document.hidden = false; f.document.emit('visibilitychange');
  assert.equal(f.video().paused, true, 'manual pause survives tab switching');
  const previous = f.video();
  f.policy.matches = false; f.policy.emit('change');
  assert.equal(f.document.body.children.length, 0);
  assert.equal(previous.attrs.has('src'), false);
  assert.equal(f.document.documentElement.attrs.has('data-film'), false);
  f.policy.matches = true; f.policy.emit('change');
  assert.equal(f.video().paused, true, 'manual pause survives remount');
  assert.equal(f.button().hidden, false, 'a paused background must still be resumable after remount');
  const broken = fixture(); broken.video().emit('error');
  assert.equal(broken.video().hidden, true);
  assert.equal(broken.button().hidden, true);
  assert.match(broken.document.body.children.find(x => x.tag === 'div').style.backgroundImage, /byttech-poster/);
  const denied = fixture({ rejectPlay: true });
  await Promise.resolve(); await Promise.resolve();
  assert.equal(denied.button().hidden, false);
  assert.equal(denied.button().textContent, 'Включить фон');
  assert.equal(denied.video().paused, true);
  console.log('PASS: media policy, visibility, manual pause, resize cleanup, failed media, denied autoplay');
})().catch(error => { console.error(error); process.exitCode = 1; });
