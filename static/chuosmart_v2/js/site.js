(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const nav = document.querySelector('.cs-v2-nav');
    if (nav) {
      const syncNav = function () {
        nav.classList.toggle('cs-v2-nav-scrolled', window.scrollY > 12);
      };
      syncNav();
      window.addEventListener('scroll', syncNav, { passive: true });
    }

    // Close the mobile menu after a direct navigation link is selected.
    const collapseEl = document.getElementById('mainNavbar');
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
