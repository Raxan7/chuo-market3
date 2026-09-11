(function () {
  'use strict';

  var THEME_KEY = 'chuosmart.theme';
  var THEME_CHOICES = ['system', 'light', 'dark', 'midnight'];
  var themeMedia = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function isValidPreference(value) {
    return THEME_CHOICES.indexOf(value) !== -1;
  }

  function getPreference() {
    try {
      var stored = window.localStorage.getItem(THEME_KEY);
      return isValidPreference(stored) ? stored : 'system';
    } catch (e) {
      return 'system';
    }
  }

  function resolveTheme(preference) {
    if (preference === 'system') {
      return themeMedia && themeMedia.matches ? 'dark' : 'light';
    }
    return preference === 'midnight' ? 'midnight' : (preference === 'dark' ? 'dark' : 'light');
  }

  function themeMetaColor(resolved) {
    if (resolved === 'midnight') return '#070d1b';
    if (resolved === 'dark') return '#0f141d';
    return '#ffffff';
  }

  function themeIconClass(preference) {
    if (preference === 'light') return 'fas fa-sun';
    if (preference === 'dark') return 'fas fa-moon';
    if (preference === 'midnight') return 'fas fa-star';
    return 'fas fa-adjust';
  }

  function themeLabel(preference) {
    return preference.charAt(0).toUpperCase() + preference.slice(1);
  }

  function updateThemeControls(preference, resolved) {
    var label = document.querySelector('[data-cs-theme-label]');
    var icon = document.querySelector('[data-cs-theme-icon]');
    var toggle = document.getElementById('csThemeMenuButton');

    if (label) label.textContent = themeLabel(preference);
    if (icon) icon.className = themeIconClass(preference);
    if (toggle) {
      toggle.setAttribute('aria-label', 'Appearance: ' + themeLabel(preference));
      toggle.setAttribute('title', 'Appearance: ' + themeLabel(preference));
    }

    document.querySelectorAll('[data-cs-theme-choice]').forEach(function (option) {
      var active = option.getAttribute('data-cs-theme-choice') === preference;
      option.classList.toggle('active', active);
      option.setAttribute('aria-pressed', active ? 'true' : 'false');
      var check = option.querySelector('.cs-v2-theme-check');
      if (check) check.classList.toggle('invisible', !active);
    });

    var themeColor = document.getElementById('csThemeColor');
    if (themeColor) themeColor.setAttribute('content', themeMetaColor(resolved));
  }

  function applyTheme(preference, persist) {
    preference = isValidPreference(preference) ? preference : 'system';
    var resolved = resolveTheme(preference);
    var root = document.documentElement;

    root.setAttribute('data-cs-theme', resolved);
    root.setAttribute('data-cs-theme-preference', preference);
    root.style.colorScheme = resolved === 'light' ? 'light' : 'dark';

    if (persist !== false) {
      try { window.localStorage.setItem(THEME_KEY, preference); } catch (e) {}
    }

    updateThemeControls(preference, resolved);

    try {
      window.dispatchEvent(new CustomEvent('chuosmart:themechange', {
        detail: { preference: preference, resolvedTheme: resolved }
      }));
    } catch (e) {}
  }

  function bindThemeControls() {
    document.querySelectorAll('[data-cs-theme-choice]').forEach(function (option) {
      option.addEventListener('click', function () {
        applyTheme(option.getAttribute('data-cs-theme-choice'), true);
      });
    });

    if (themeMedia) {
      var onSystemThemeChange = function () {
        if (getPreference() === 'system') applyTheme('system', false);
      };
      if (themeMedia.addEventListener) themeMedia.addEventListener('change', onSystemThemeChange);
      else if (themeMedia.addListener) themeMedia.addListener(onSystemThemeChange);
    }

    window.addEventListener('storage', function (event) {
      if (event.key === THEME_KEY) applyTheme(getPreference(), false);
    });
  }

  window.ChuoSmartTheme = {
    getPreference: getPreference,
    getResolvedTheme: function () { return resolveTheme(getPreference()); },
    setPreference: function (preference) { applyTheme(preference, true); }
  };

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(getPreference(), false);
    bindThemeControls();

    var nav = document.querySelector('.cs-v2-nav');
    if (nav) {
      var syncNav = function () {
        nav.classList.toggle('cs-v2-nav-scrolled', window.scrollY > 12);
      };
      syncNav();
      window.addEventListener('scroll', syncNav, { passive: true });
    }

    // Close the mobile menu after a direct navigation link is selected.
    var collapseEl = document.getElementById('mainNavbar');
    if (collapseEl && window.bootstrap) {
      collapseEl.querySelectorAll('a.nav-link:not(.dropdown-toggle), .cs-v2-nav-cta').forEach(function (link) {
        link.addEventListener('click', function () {
          if (window.innerWidth < 1200 && collapseEl.classList.contains('show')) {
            window.bootstrap.Collapse.getOrCreateInstance(collapseEl).hide();
          }
        });
      });
    }
  });
})();
