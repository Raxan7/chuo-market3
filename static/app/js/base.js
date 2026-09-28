/* ============================================================
   ChuoSmart Base JavaScript
   Extracted from base.html inline scripts for caching & perf
   ============================================================ */

/* ---- Body Scroll Lock Restore ---- */
function lockBodyScroll() {
  document.body.style.overflow = 'hidden';
  document.documentElement.style.overflow = 'hidden';
}
function restoreBodyScroll() {
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
}

/* ---- Cart Count AJAX ---- */
function updateCartCount() {
  $.ajax({
    url: '/get_cart_count/',
    type: 'GET',
    dataType: 'json',
    success: function(response) {
      $('#cart-count').text(response.cart_count);
    },
    error: function(xhr, status, error) {
      console.error('Error fetching cart count:', error);
    }
  });
}

/* ---- Mobile Cart Count Sync ---- */
function updateMobileCartCount() {
  var cartCount = $('#cart-count').text();
  $('#mobile-cart-count').text(cartCount);
}

/* ---- Document Ready ---- */
$(document).ready(function() {
  updateCartCount();

  // Mobile search toggle
  $('#mobile-search-toggle').click(function(e) {
    e.preventDefault();
    $('#mobile-search-overlay').fadeIn(300);
    setTimeout(function() {
      $('#mobile-search-overlay input').focus();
    }, 350);
  });

  $('#close-search').click(function() {
    $('#mobile-search-overlay').fadeOut(300);
  });

  updateMobileCartCount();

  // Body scroll lock when mobile menu is open
  var mainNavbar = document.getElementById('mainNavbar');
  if (mainNavbar) {
    mainNavbar.addEventListener('show.bs.collapse', function() {
      lockBodyScroll();
    });
    mainNavbar.addEventListener('hide.bs.collapse', function() {
      restoreBodyScroll();
    });
  }

  // Close dropdowns when clicking nav links (collapses the navbar)
  if (typeof bootstrap !== 'undefined') {
    // Close navbar collapse and dropdowns when clicking a regular nav link
    $('.navbar-nav .nav-link:not(.dropdown-toggle)').on('click', function() {
      $('.navbar-collapse').removeClass('show');
      $('.dropdown-menu').removeClass('show');
      $('.dropdown-toggle').attr('aria-expanded', 'false');
      restoreBodyScroll();
    });
    // Click-outside: close any open dropdown
    $(document).on('click', function(e) {
      if (!$(e.target).closest('.dropdown').length) {
        $('.dropdown-menu').removeClass('show');
        $('.dropdown-toggle').attr('aria-expanded', 'false');
      }
    });
    // Close dropdown after navigating to a link inside it
    $('.dropdown-menu .dropdown-item').on('click', function() {
      var $parent = $(this).closest('.dropdown');
      $parent.find('.dropdown-menu').removeClass('show');
      $parent.find('.dropdown-toggle').attr('aria-expanded', 'false');
      $('.navbar-collapse').removeClass('show');
      restoreBodyScroll();
    });
  } else {
    // Fallback: manual toggle when Bootstrap is unavailable
    $('.navbar-toggler').on('click', function() {
      var target = $($(this).attr('data-bs-target'));
      target.toggleClass('show');
      if (target.hasClass('show')) {
        lockBodyScroll();
      } else {
        restoreBodyScroll();
      }
    });
    $(document).on('click', function(e) {
      if (!$(e.target).closest('.navbar').length) {
        $('.navbar-collapse').removeClass('show');
        $('.dropdown-menu').removeClass('show');
        $('.dropdown-toggle').attr('aria-expanded', 'false');
        restoreBodyScroll();
      }
    });
    $('.navbar-nav .nav-link').on('click', function() {
      $('.navbar-collapse').removeClass('show');
      $('.dropdown-menu').removeClass('show');
      $('.dropdown-toggle').attr('aria-expanded', 'false');
      restoreBodyScroll();
    });
  }

  // Mobile nav active state
  (function() {
    var path = window.location.pathname;
    $('.mobile-nav-item').removeClass('active');
    if (path === '/') {
      $('.mobile-nav-item').eq(0).addClass('active');
    } else if (path.indexOf('/marketplace') !== -1 || path.indexOf('/product') !== -1) {
      $('.mobile-nav-item').eq(1).addClass('active');
    } else if (path.indexOf('/blog') !== -1) {
      $('.mobile-nav-item').eq(2).addClass('active');
    } else if (path.indexOf('/jobs') !== -1) {
      $('.mobile-nav-item').eq(3).addClass('active');
    } else if (path.indexOf('/cart') !== -1) {
      $('.mobile-nav-item').eq(4).addClass('active');
    }
  })();
});

/* ---- Auto-dismiss Messages ---- */
document.addEventListener("DOMContentLoaded", function() {
  var messageContainer = document.getElementById("message-container");
  if (messageContainer) {
    setTimeout(function() {
      var alerts = messageContainer.querySelectorAll('.alert');
      alerts.forEach(function(alert) {
        alert.style.transition = 'opacity 0.5s ease';
        alert.style.opacity = '0';
        setTimeout(function() { alert.style.display = 'none'; }, 500);
      });
    }, 5000);
  }
});

/* ---- Ad iFrame Auto-loading ----
   Ads are rendered as cards matching the dimensions of sibling
   course/product/blog cards. Each ad is housed in an <iframe> and is
   initialized only after the iframe has a measurable width. This avoids
   AdSense's "No slot size for availableWidth=0" error on grids that start
   hidden behind skeleton loaders, and keeps repeated Adsterra native zones
   isolated from one another. */
function buildAdsterraNativeDocument(scriptSrc, containerId) {
  var safeContainerId = String(containerId || '').replace(/[^a-zA-Z0-9_-]/g, '');
  var allowedPrefix = 'https://pl31147888.profitableratecpmnetwork.com/';
  if (!safeContainerId || !scriptSrc || scriptSrc.indexOf(allowedPrefix) !== 0) {
    return '';
  }

  return '<!DOCTYPE html><html><head>'
    + '<meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<style>html,body{margin:0;padding:0;width:100%;height:100%;background:transparent;overflow:hidden;}'
    + 'body{display:flex;align-items:center;justify-content:center;}'
    + '#' + safeContainerId + '{width:100%;max-width:100%;}</style>'
    + '</head><body>'
    + '<div id="' + safeContainerId + '"></div>'
    + '<script async="async" data-cfasync="false" src="' + scriptSrc + '"><\/script>'
    + '</body></html>';
}

function initializeAdIframe(iframe) {
  if (!iframe || iframe.hasAttribute('data-initialized')) {
    return;
  }

  var adType = iframe.getAttribute('data-ad-type');
  var adSrc = iframe.getAttribute('data-ad-src');

  if (adType === 'adsense') {
    // Build an inline HTML document that loads the AdSense unit only after
    // the outer iframe has a real layout width.
    var client = iframe.getAttribute('data-ad-client');
    var slot = iframe.getAttribute('data-ad-slot');
    var doc = '<!DOCTYPE html><html><head>'
      + '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + client + '" crossorigin="anonymous"><\/script>'
      + '<style>html,body{margin:0;padding:0;width:100%;height:100%;background:transparent;overflow:hidden;}'
      + 'ins.adsbygoogle{display:block!important;width:100%!important;min-width:1px;}</style>'
      + '</head><body>'
      + '<ins class="adsbygoogle" data-ad-client="' + client + '" data-ad-slot="' + slot + '" data-ad-format="auto" data-full-width-responsive="true"></ins>'
      + '<script>(adsbygoogle = window.adsbygoogle || []).push({});<\/script>'
      + '</body></html>';
    iframe.srcdoc = doc;
  } else if (adType === 'adsterra-native') {
    var nativeDoc = buildAdsterraNativeDocument(
      iframe.getAttribute('data-ad-script-src'),
      iframe.getAttribute('data-ad-container-id')
    );
    if (nativeDoc) {
      iframe.srcdoc = nativeDoc;
    }
  } else if (adSrc) {
    // Legacy direct-link iframe support for any older placement still using it.
    iframe.src = adSrc;
  }

  iframe.removeAttribute('data-initialization-pending');
  iframe.setAttribute('data-initialized', 'true');
}

function queueAdIframeInitialization(iframe) {
  if (
    !iframe ||
    iframe.hasAttribute('data-initialized') ||
    iframe.hasAttribute('data-initialization-pending')
  ) {
    return;
  }

  var hasUsableWidth = function() {
    return iframe.getBoundingClientRect().width > 0;
  };

  if (hasUsableWidth()) {
    initializeAdIframe(iframe);
    return;
  }

  iframe.setAttribute('data-initialization-pending', 'true');

  if ('ResizeObserver' in window) {
    var observer = new ResizeObserver(function() {
      if (hasUsableWidth()) {
        observer.disconnect();
        initializeAdIframe(iframe);
      }
    });
    observer.observe(iframe);
    return;
  }

  // Older-browser fallback: retry briefly until the hidden grid is revealed.
  var attempts = 0;
  var timer = window.setInterval(function() {
    attempts += 1;
    if (hasUsableWidth()) {
      window.clearInterval(timer);
      initializeAdIframe(iframe);
    } else if (attempts >= 40) {
      window.clearInterval(timer);
      iframe.removeAttribute('data-initialization-pending');
    }
  }, 250);
}

function initAdIframes(root) {
  var container = root || document;
  var iframes = container.querySelectorAll(
    'iframe.ad-iframe:not([data-initialized]):not([data-initialization-pending])'
  );
  iframes.forEach(queueAdIframeInitialization);
}

window.initializeListAds = function(listContainer) {
  if (listContainer) {
    initAdIframes(listContainer);
  }
};

document.addEventListener("DOMContentLoaded", function() {
  initAdIframes(document);
});
