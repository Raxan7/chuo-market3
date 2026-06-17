/* ============================================================
   ChuoSmart Base JavaScript
   Extracted from base.html inline scripts for caching & perf
   ============================================================ */

/* ---- AdSense List Ads Initializer ---- */
window.initializeListAds = function(container) {
  if (!container || typeof window.adsbygoogle === 'undefined') {
    return;
  }
  var adSlots = container.querySelectorAll('ins.adsbygoogle:not([data-adsbygoogle-status])');
  adSlots.forEach(function(slot) {
    if (slot.offsetWidth === 0) {
      return;
    }
    try {
      (adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      // Ad providers can reject duplicate initialization; ignore safely.
    }
  });
};

document.addEventListener('DOMContentLoaded', function() {
  window.initializeListAds(document);
});

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

/* ---- Chatbot ---- */
function scrollToBottom() {
  var chatbotBody = $('#chatbot-body');
  chatbotBody.scrollTop(chatbotBody[0].scrollHeight);
  $('#scroll-down').hide();
}

/* ---- Mobile Cart Count Sync ---- */
function updateMobileCartCount() {
  var cartCount = $('#cart-count').text();
  $('#mobile-cart-count').text(cartCount);
}

/* ---- Document Ready ---- */
$(document).ready(function() {
  updateCartCount();

  // Chatbot toggle
  $('#chatbot-header, #chatbot-toggle').click(function() {
    $('#chatbot').toggle();
    setTimeout(scrollToBottom, 100);
  });

  // Chatbot send
  $('#chatbot-send').click(function() {
    var message = $('#chatbot-message').val().trim();
    if (message === '') return;
    $('#chatbot-body').append('<div><strong>You:</strong> ' + $('<span>').text(message).html() + '</div>');
    $('#chatbot-message').val('');
    $.ajax({
      url: window.CHATBOT_API_URL || '/chatbot/chatbot/',
      type: 'POST',
      data: JSON.stringify({ message: message }),
      contentType: 'application/json',
      headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' },
      success: function(response) {
        $('#chatbot-body').append('<div><strong>Bot:</strong> ' + response.reply + '</div>');
        scrollToBottom();
      },
      error: function(xhr, status, error) {
        console.error('Error sending message:', error);
        $('#chatbot-body').append('<div><strong>Bot:</strong> Sorry, something went wrong. Please try again.</div>');
        scrollToBottom();
      }
    });
  });

  // Chatbot Enter key
  $('#chatbot-message').keypress(function(e) {
    if (e.which === 13) {
      $('#chatbot-send').click();
    }
  });

  // Chatbot scroll
  $('#chatbot-body').on('scroll', function() {
    var cb = $(this);
    if (cb.scrollTop() + cb.innerHeight() >= cb[0].scrollHeight) {
      $('#scroll-down').hide();
    } else {
      $('#scroll-down').show();
    }
  });

  $('#scroll-down').click(function() {
    scrollToBottom();
  });

  scrollToBottom();

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

  // Bootstrap nav fallback
  if (typeof bootstrap === 'undefined') {
    $('.navbar-toggler').on('click', function() {
      var target = $($(this).attr('data-bs-target'));
      target.toggleClass('show');
    });
    $(document).on('click', function(e) {
      if (!$(e.target).closest('.navbar').length) {
        $('.navbar-collapse').removeClass('show');
      }
    });
  } else {
    $('.navbar-nav .nav-link').on('click', function() {
      $('.navbar-collapse').removeClass('show');
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
