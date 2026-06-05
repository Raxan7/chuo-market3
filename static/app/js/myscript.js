// Custom JavaScript for ChuoSmart

// Initialize product carousels
$(document).ready(function(){
    // Product carousel
    $("#product-carousel").owlCarousel({
        loop: true,
        margin: 10,
        responsiveClass: true,
        responsive: {
            0: {
                items: 1,
                nav: false,
                dots: true
            },
            600: {
                items: 3,
                nav: false,
                dots: true
            },
            1000: {
                items: 4,
                nav: false,
                dots: true,
                loop: true
            }
        }
    });

    // Product detail image carousel
    $("#product-detail-carousel").owlCarousel({
        loop: true,
        margin: 10,
        nav: true,
        dots: false,
        responsive: {
            0: {
                items: 1
            }
        }
    });

    // Related products carousel
    $("#related-products").owlCarousel({
        loop: true,
        margin: 10,
        responsiveClass: true,
        responsive: {
            0: {
                items: 1,
                nav: false,
                dots: true
            },
            600: {
                items: 2,
                nav: false,
                dots: true
            },
            1000: {
                items: 4,
                nav: false,
                dots: true,
                loop: true
            }
        }
    });

    // Product quantity buttons
    $('.plus-cart').click(function(){
        var id = $(this).attr("pid").toString();
        var eml = this.parentNode.children[1];
        $.ajax({
            type: "GET",
            url: "/plus-cart/",
            data: {
                pid: id
            },
            success: function(data){
                eml.innerText = data.quantity;
                document.getElementById("amount").innerText = data.amount;
                document.getElementById("totalamount").innerText = data.totalamount;
            },
            error: function() {
                console.error('Failed to increase quantity');
            }
        });
    });

    $('.minus-cart').click(function(){
        var id = $(this).attr("pid").toString();
        var eml = this.parentNode.children[1];
        $.ajax({
            type: "GET",
            url: "/minus-cart/",
            data: {
                pid: id
            },
            success: function(data){
                eml.innerText = data.quantity;
                document.getElementById("amount").innerText = data.amount;
                document.getElementById("totalamount").innerText = data.totalamount;
            },
            error: function() {
                console.error('Failed to decrease quantity');
            }
        });
    });

    $('.remove-cart').click(function(){
        var id = $(this).attr("pid").toString();
        var eml = this;
        $.ajax({
            type: "GET",
            url: "/remove-cart/" + id + "/",
            success: function(){
                document.getElementById("amount").innerText = "0";
                document.getElementById("totalamount").innerText = "0";
                var row = eml.closest('tr') || eml.parentNode.parentNode.parentNode.parentNode;
                if (row && row.parentNode) {
                    row.remove();
                }
                // Reload cart count
                if (typeof updateCartCount === 'function') {
                    updateCartCount();
                    updateMobileCartCount();
                }
            },
            error: function() {
                console.error('Failed to remove item from cart');
            }
        });
    });
});
