/*
 * ChuoSmart Monetag Direct Link fallback.
 *
 * Primary provider formats are loaded in base.html.
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

  var STORAGE_KEY =
    'chuosmart.monetag.directLinkIndex';

  function readIndex() {
    try {
      var value = parseInt(
        window.sessionStorage.getItem(
          STORAGE_KEY
        ),
        10
      );

      return (
        Number.isFinite(value)
        && value >= 0
      )
        ? value
        : 0;
    } catch (error) {
      return 0;
    }
  }

  function writeIndex(value) {
    try {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        String(value)
      );
    } catch (error) {
      /* restricted storage */
    }
  }

  function currentUrl() {
    return DIRECT_LINKS[
      readIndex()
      % DIRECT_LINKS.length
    ];
  }

  function advance() {
    writeIndex(
      (
        readIndex() + 1
      )
      % DIRECT_LINKS.length
    );
  }

  function bind(root) {
    var scope =
      root || document;

    scope
      .querySelectorAll(
        '[data-monetag-direct-link]'
        + ':not([data-monetag-bound])'
      )
      .forEach(
        function (link) {
          link.dataset
            .monetagBound =
              'true';

          link.href =
            currentUrl();

          link.target =
            '_blank';

          link.rel =
            'sponsored '
            + 'noopener '
            + 'noreferrer';

          link.addEventListener(
            'click',
            function () {
              advance();

              window.setTimeout(
                function () {
                  link.href =
                    currentUrl();
                },
                0
              );
            }
          );
        }
      );
  }

  function openDirectLink() {
    var url =
      currentUrl();

    advance();

    return Boolean(
      window.open(
        url,
        '_blank',
        'noopener,noreferrer'
      )
    );
  }

  window.ChuoSmartMonetag = {
    links:
      DIRECT_LINKS.slice(),

    getDirectLink:
      currentUrl,

    next:
      advance,

    bind:
      bind,

    open:
      openDirectLink
  };

  if (
    document.readyState
    === 'loading'
  ) {
    document.addEventListener(
      'DOMContentLoaded',
      function () {
        bind(document);
      }
    );
  } else {
    bind(document);
  }
})();
