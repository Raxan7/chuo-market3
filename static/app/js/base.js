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



function whenAdElementHasWidth(element, minimumWidth, callback) {
  if (
    !element ||
    element.hasAttribute('data-chuosmart-width-wait')
  ) {
    return;
  }

  var isReady = function() {
    return (
      element.isConnected &&
      element.getBoundingClientRect().width >= minimumWidth
    );
  };

  if (isReady()) {
    callback();
    return;
  }

  element.setAttribute('data-chuosmart-width-wait', 'true');

  if ('ResizeObserver' in window) {
    var observer = new ResizeObserver(function() {
      if (!isReady()) {
        return;
      }

      observer.disconnect();
      element.removeAttribute('data-chuosmart-width-wait');
      callback();
    });

    observer.observe(element);
    return;
  }

  var attempts = 0;
  var timer = window.setInterval(function() {
    attempts += 1;

    if (isReady()) {
      window.clearInterval(timer);
      element.removeAttribute('data-chuosmart-width-wait');
      callback();
      return;
    }

    if (attempts >= 40 || !element.isConnected) {
      window.clearInterval(timer);
      element.removeAttribute('data-chuosmart-width-wait');
    }
  }, 250);
}












/* Adcash banner runtime.
   Keep the provider library untouched: aclib.js performs its own anti-fraud /
   browser automation checks. ChuoSmart owns only loading, slot targeting and
   graceful failure handling. */
var ADCASH_LIBRARY_URL = "https://acscdn.com/script/aclib.js";
var adcashLibraryPromise = null;
var adcashSlotSequence = 0;

function adcashRuntimeWarning(message, error) {
  if (window.console && typeof window.console.warn === "function") {
    window.console.warn("[ChuoSmart ads] " + message, error || "");
  }
}

function ensureAdcashLibrary() {
  if (window.aclib && typeof window.aclib.runBanner === "function") {
    return Promise.resolve(window.aclib);
  }

  if (adcashLibraryPromise) {
    return adcashLibraryPromise;
  }

  adcashLibraryPromise = new Promise(function(resolve, reject) {
    var script = document.getElementById("aclib") ||
      document.querySelector('script[data-chuosmart-adcash-library="true"]');
    var timeoutId = null;

    function cleanup() {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
        timeoutId = null;
      }
    }

    function finish() {
      cleanup();
      if (window.aclib && typeof window.aclib.runBanner === "function") {
        resolve(window.aclib);
      } else {
        reject(new Error("Adcash library loaded without runBanner"));
      }
    }

    function fail() {
      cleanup();
      reject(new Error("Adcash library failed to load"));
    }

    if (!script) {
      script = document.createElement("script");
      script.id = "aclib";
      script.type = "text/javascript";
      script.async = true;
      script.src = ADCASH_LIBRARY_URL;
      script.setAttribute("data-chuosmart-adcash-library", "true");
      script.addEventListener("load", finish, { once: true });
      script.addEventListener("error", fail, { once: true });
      document.head.appendChild(script);
    } else {
      if (window.aclib && typeof window.aclib.runBanner === "function") {
        finish();
        return;
      }
      script.addEventListener("load", finish, { once: true });
      script.addEventListener("error", fail, { once: true });
    }

    timeoutId = window.setTimeout(function() {
      reject(new Error("Timed out waiting for Adcash library"));
    }, 12000);
  });

  adcashLibraryPromise.catch(function(error) {
    adcashRuntimeWarning("library unavailable; page continues without ads", error);
    adcashLibraryPromise = null;
  });

  return adcashLibraryPromise;
}

function adcashZoneForSlot(slot) {
  var fixedZone = slot.getAttribute("data-zone");
  if (fixedZone) return String(fixedZone);

  var mobileZone = slot.getAttribute("data-zone-mobile");
  var desktopZone = slot.getAttribute("data-zone-desktop");
  var breakpoint = parseFloat(slot.getAttribute("data-zone-breakpoint") || "767.98");

  if (!mobileZone || !desktopZone || !Number.isFinite(breakpoint)) {
    return null;
  }

  return window.matchMedia("(max-width: " + breakpoint + "px)").matches
    ? String(mobileZone)
    : String(desktopZone);
}

function adcashSlotIsEligible(slot) {
  var minimumWidth = parseInt(slot.getAttribute("data-adcash-min-width") || "0", 10);
  return !minimumWidth || window.innerWidth >= minimumWidth;
}

function revealAdcashSlotParent(slot) {
  var parentId = slot.getAttribute("data-adcash-reveal-parent");
  if (!parentId) return;
  var parent = document.getElementById(parentId);
  if (parent) parent.style.display = "block";
}

function renderAdcashSlot(slot) {
  if (!slot || !slot.isConnected) return;

  var state = slot.getAttribute("data-adcash-state");
  if (state === "loading" || state === "requested" || state === "failed") return;

  if (!adcashSlotIsEligible(slot)) {
    slot.setAttribute("data-adcash-state", "waiting-for-width");
    return;
  }

  var zoneId = adcashZoneForSlot(slot);
  if (!zoneId) {
    slot.setAttribute("data-adcash-state", "failed");
    adcashRuntimeWarning("banner slot has no valid zone id");
    return;
  }

  if (!slot.id) {
    adcashSlotSequence += 1;
    slot.id = "cs-adcash-slot-" + adcashSlotSequence;
  }

  slot.setAttribute("data-adcash-state", "loading");

  ensureAdcashLibrary().then(function(library) {
    if (!slot.isConnected) return;

    try {
      revealAdcashSlotParent(slot);
      library.runBanner({
        zoneId: String(zoneId),
        renderIn: "#" + slot.id
      });
      slot.setAttribute("data-adcash-state", "requested");
    } catch (error) {
      slot.setAttribute("data-adcash-state", "failed");
      adcashRuntimeWarning("runBanner failed for zone " + zoneId, error);
    }
  }).catch(function() {
    if (slot.isConnected) {
      slot.setAttribute("data-adcash-state", "failed");
    }
  });
}

function initAdIframes(root) {
  var scope = root || document;
  var slots = [];

  if (scope.matches && scope.matches("[data-adcash-banner-slot]")) {
    slots.push(scope);
  }

  if (scope.querySelectorAll) {
    Array.prototype.push.apply(
      slots,
      scope.querySelectorAll(
        '[data-adcash-banner-slot][data-adcash-state="pending"], ' +
        '[data-adcash-banner-slot][data-adcash-state="waiting-for-width"]'
      )
    );
  }

  slots.forEach(renderAdcashSlot);
}

/* Keep the public initializer because marketplace/blog infinite-scroll code
   already calls window.initializeListAds(). */
window.initializeListAds = function(listContainer) {
  initAdIframes(listContainer || document);
};

var adcashResizeTimer = null;
window.addEventListener("resize", function() {
  if (adcashResizeTimer !== null) {
    window.clearTimeout(adcashResizeTimer);
  }
  adcashResizeTimer = window.setTimeout(function() {
    initAdIframes(document);
  }, 200);
});

document.addEventListener("DOMContentLoaded", function() {
  initAdIframes(document);
});
