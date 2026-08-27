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
   course/product/blog cards. Each ad is housed in an <iframe> that
   auto-loads the ad content (no click required). This function
   initializes iframes either on initial page load or after new
   items are appended via infinite scroll. */
function initAdIframes(root) {
  var container = root || document;
  var iframes = container.querySelectorAll('iframe.ad-iframe:not([data-initialized])');
  iframes.forEach(function(iframe) {
    var adSrc = iframe.getAttribute('data-ad-src');
    if (iframe.getAttribute('data-ad-type') === 'adsense') {
      // Build an inline HTML document that loads the AdSense unit
      var client = iframe.getAttribute('data-ad-client');
      var slot = iframe.getAttribute('data-ad-slot');
      var doc = '<!DOCTYPE html><html><head>'
        + '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + client + '" crossorigin="anonymous"><\/script>'
        + '<style>html,body{margin:0;padding:0;height:100%;background:transparent;overflow:hidden;}' 
        + 'body{display:flex;align-items:center;justify-content:center;}</style>'
        + '</head><body>'
        + '<ins class="adsbygoogle" style="display:block" data-ad-client="' + client + '" data-ad-slot="' + slot + '" data-ad-format="auto" data-full-width-responsive="true"></ins>'
        + '<script>(adsbygoogle = window.adsbygoogle || []).push({});<\/script>'
        + '</body></html>';
      iframe.srcdoc = doc;
    } else if (adSrc) {
      // Adsterra smart link: load the URL directly (auto-loads the ad)
      iframe.src = adSrc;
    }
    iframe.setAttribute('data-initialized', 'true');
  });
}

window.initializeListAds = function(listContainer) {
  if (listContainer) {
    initAdIframes(listContainer);
  }
};

document.addEventListener("DOMContentLoaded", function() {
  initAdIframes(document);
});
