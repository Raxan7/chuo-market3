/*
 * ChuoSmart Monetag Direct Link integration.
 *
 * Monetag Direct Link frontend integration.
 * Ads are intentionally enabled only when Django renders this asset through
 * the existing `ads_allowed` policy.
 */
(function () {
  'use strict';

  var DIRECT_LINKS = [
    "https://omg10.com/4/10558191",
    "https://omg10.com/4/10558195",
    "https://omg10.com/4/10558194",
    "https://omg10.com/4/11939936",
    "https://omg10.com/4/10558192",
    "https://omg10.com/4/10558193",
    "https://omg10.com/4/10558189",
    "https://omg10.com/4/10558184",
    "https://omg10.com/4/10558188",
    "https://omg10.com/4/10558187"
  ];

  var STORAGE_KEY = 'chuosmart.monetag.directLinkIndex';

  function readIndex() {
    try {
      var value = parseInt(window.sessionStorage.getItem(STORAGE_KEY), 10);
      return Number.isFinite(value) && value >= 0 ? value : 0;
    } catch (error) {
      return 0;
    }
  }

  function writeIndex(value) {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, String(value));
    } catch (error) {
      // sessionStorage can be unavailable in private/restricted browsing.
    }
  }

  function currentUrl() {
    return DIRECT_LINKS[readIndex() % DIRECT_LINKS.length];
  }

  function advance() {
    writeIndex((readIndex() + 1) % DIRECT_LINKS.length);
  }

  function openDirectLink() {
    var url = currentUrl();
    advance();

    var opened = window.open(
      url,
      '_blank',
      'noopener,noreferrer'
    );

    return Boolean(opened);
  }

  function createStyles() {
    if (document.getElementById('cs-monetag-styles')) return;

    var style = document.createElement('style');
    style.id = 'cs-monetag-styles';
    style.textContent = `
      .cs-monetag-placement {
        width: min(1180px, calc(100% - 32px));
        margin: 24px auto;
        padding: 18px 20px;
        border: 1px solid var(--cs-border, rgba(15,23,42,.12));
        border-radius: 18px;
        background: var(--cs-surface, #fff);
        color: var(--cs-ink, #111827);
        box-shadow: 0 10px 35px rgba(15,23,42,.07);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
      }

      .cs-monetag-copy {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
      }

      .cs-monetag-label {
        flex: 0 0 auto;
        display: inline-flex;
        align-items: center;
        min-height: 28px;
        padding: 5px 10px;
        border-radius: 999px;
        background: rgba(108,77,255,.11);
        color: #6c4dff;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .06em;
        text-transform: uppercase;
      }

      .cs-monetag-copy strong {
        display: block;
        font-size: 15px;
        line-height: 1.3;
      }

      .cs-monetag-copy small {
        display: block;
        margin-top: 2px;
        opacity: .68;
        font-size: 12px;
      }

      .cs-monetag-button {
        flex: 0 0 auto;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 42px;
        padding: 10px 17px;
        border-radius: 12px;
        background: #6c4dff;
        color: #fff !important;
        text-decoration: none !important;
        font-size: 13px;
        font-weight: 750;
        transition:
          transform .18s ease,
          box-shadow .18s ease,
          opacity .18s ease;
      }

      .cs-monetag-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 22px rgba(108,77,255,.24);
      }

      .cs-monetag-button:focus-visible {
        outline: 3px solid rgba(108,77,255,.32);
        outline-offset: 3px;
      }

      @media (max-width: 640px) {
        .cs-monetag-placement {
          width: calc(100% - 24px);
          margin: 18px auto;
          padding: 15px;
          align-items: stretch;
          flex-direction: column;
        }

        .cs-monetag-copy {
          align-items: flex-start;
        }

        .cs-monetag-button {
          width: 100%;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function createPlacement() {
    if (!document.body) return;
    if (document.querySelector('[data-cs-monetag-placement]')) return;

    createStyles();

    var placement = document.createElement('aside');
    placement.className = 'cs-monetag-placement';
    placement.setAttribute('data-cs-monetag-placement', '');
    placement.setAttribute('aria-label', 'Sponsored offer');

    var copy = document.createElement('div');
    copy.className = 'cs-monetag-copy';

    var label = document.createElement('span');
    label.className = 'cs-monetag-label';
    label.textContent = 'Sponsored';

    var text = document.createElement('div');

    var heading = document.createElement('strong');
    heading.textContent = 'Explore a sponsored offer';

    var description = document.createElement('small');
    description.textContent =
      'Sponsored content helps support ChuoSmart.';

    text.appendChild(heading);
    text.appendChild(description);

    copy.appendChild(label);
    copy.appendChild(text);

    var link = document.createElement('a');
    link.className = 'cs-monetag-button';
    link.href = currentUrl();
    link.target = '_blank';
    link.rel = 'sponsored noopener noreferrer';
    link.textContent = 'View offer';

    link.addEventListener('click', function () {
      advance();

      // Prepare the following Monetag zone for another click without
      // interfering with the current navigation.
      window.setTimeout(function () {
        link.href = currentUrl();
      }, 0);
    });

    placement.appendChild(copy);
    placement.appendChild(link);

    var footer = document.querySelector(
      'footer.cs-v2-footer, footer.footer, footer'
    );

    if (footer && footer.parentNode) {
      footer.parentNode.insertBefore(placement, footer);
    } else {
      document.body.appendChild(placement);
    }
  }

  // Public API for future ChuoSmart buttons/cards.
  window.ChuoSmartMonetag = {
    links: DIRECT_LINKS.slice(),
    getDirectLink: currentUrl,
    open: openDirectLink,
    next: advance
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createPlacement);
  } else {
    createPlacement();
  }
})();
