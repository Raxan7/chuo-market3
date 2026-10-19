const test = require('node:test');
const assert = require('node:assert/strict');
const modulePath = require.resolve('../static/app/js/social-share.js');

function setup(navigator) {
  const listeners = {};
  const status = { textContent: '', classList: { remove() {} } };
  const widget = { dataset: { shareUrl: 'https://chuosmart.com/courses/example/', shareTitle: 'Example Course' }, querySelector: () => status };
  const copyButton = { name: 'copy' };
  const nativeButton = { name: 'native' };
  const target = { closest(selector) {
    if (selector === '.cs-share__copy') return this.copy ? copyButton : null;
    if (selector === '.cs-share__native') return this.native ? nativeButton : null;
    if (selector === '.cs-share') return widget;
    return null;
  } };
  global.document = {
    addEventListener(name, fn) { listeners[name] = fn; },
    querySelectorAll() { return [nativeButton]; },
    createElement() { throw new Error('Clipboard fallback unexpectedly used'); },
  };
  Object.defineProperty(global, 'navigator', { value: navigator, configurable: true });
  delete require.cache[modulePath];
  require(modulePath);
  return { listeners, status, widget, target, nativeButton };
}

test('copy link uses the server-provided public URL, not a dashboard URL', async () => {
  let copied = '';
  const { listeners, status, target } = setup({ clipboard: { async writeText(value) { copied = value; } } });
  target.copy = true;
  await listeners.click({ target });
  assert.equal(copied, 'https://chuosmart.com/courses/example/');
  assert.equal(status.textContent, 'Link copied to clipboard.');
});

test('native sharing appears only when browser supports it', async () => {
  let payload;
  const { listeners, target, nativeButton } = setup({ async share(input) { payload = input; } });
  nativeButton.hidden = true;
  listeners.DOMContentLoaded();
  assert.equal(nativeButton.hidden, false);
  target.native = true;
  await listeners.click({ target });
  assert.deepEqual(payload, { title: 'Example Course', url: 'https://chuosmart.com/courses/example/' });
});

test('unsupported native sharing stays hidden', () => {
  const { listeners, nativeButton } = setup({});
  nativeButton.hidden = true;
  listeners.DOMContentLoaded();
  assert.equal(nativeButton.hidden, true);
});
