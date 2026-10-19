/* Event delegation supports share controls repeated in instructor course lists. */
(function () {
  'use strict';
  function announce(widget, text) {
    var status = widget.querySelector('.cs-share__status');
    if (status) {
      status.classList.remove('visually-hidden');
      status.textContent = text;
    }
  }
  function fallbackCopy(text) {
    var field = document.createElement('textarea');
    field.value = text;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.appendChild(field);
    field.select();
    var result = false;
    try { result = document.execCommand('copy'); } catch (error) { result = false; }
    field.remove();
    return result;
  }
  document.addEventListener('DOMContentLoaded', function () {
    if (!navigator.share) return;
    document.querySelectorAll('.cs-share__native').forEach(function (button) { button.hidden = false; });
  });
  document.addEventListener('click', async function (event) {
    var copy = event.target.closest('.cs-share__copy');
    var nativeButton = event.target.closest('.cs-share__native');
    if (!copy && !nativeButton) return;
    var widget = event.target.closest('.cs-share');
    if (!widget) return;
    var url = widget.dataset.shareUrl;
    if (!url) return;
    if (copy) {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(url);
          announce(widget, 'Link copied to clipboard.');
          return;
        }
      } catch (error) { /* Fall back for insecure contexts or denied permission. */ }
      announce(widget, fallbackCopy(url) ? 'Link copied to clipboard.' : 'Could not copy automatically. Please copy the URL from your address bar.');
    } else if (navigator.share) {
      try {
        await navigator.share({ title: widget.dataset.shareTitle || document.title, url: url });
        announce(widget, 'Shared successfully.');
      } catch (error) {
        if (!error || error.name !== 'AbortError') announce(widget, 'Sharing was not available. Try one of the links above.');
      }
    }
  });
}());
