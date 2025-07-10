"""
Help Center data module for ChuoSmart
"""

# Common categories for help content
CATEGORIES = [
    {
        'id': 'account',
        'title': 'Account Management',
        'icon': 'fas fa-user-circle'
    },
    {
        'id': 'products',
        'title': 'Products & Shopping',
        'icon': 'fas fa-shopping-bag'
    },
    {
        'id': 'orders',
        'title': 'Orders & Payments',
        'icon': 'fas fa-money-bill-wave'
    },
    {
        'id': 'marketplace',
        'title': 'Selling on Marketplace',
        'icon': 'fas fa-store'
    },
    {
        'id': 'technical',
        'title': 'Technical Support',
        'icon': 'fas fa-cogs'
    }
]

# Frequently Asked Questions grouped by category
FAQS = {
    'account': [
        {
            'question': 'How do I create an account?',
            'answer': 'To create an account, click on the "Registration" link at the top of the page. Fill in your details including username, email, and password. After registration, you\'ll need to complete your profile information.'
        },
        {
            'question': 'How do I reset my password?',
            'answer': 'Click on the "Login" link, then select "Forgot Password". Enter your email address, and we\'ll send you instructions to reset your password.'
        },
        {
            'question': 'Why do I need to provide my phone number?',
            'answer': 'Your phone number is required for selling products on our marketplace. It allows potential buyers to contact you regarding your products. Your number will only be visible to registered users who are interested in your products.'
        },
        {
            'question': 'How do I update my profile information?',
            'answer': 'Log in to your account, then click on your username at the top right corner and select "Profile". From there, you can update your personal information, including your name, university details, and phone number.'
        }
    ],
    'products': [
        {
            'question': 'How do I search for products?',
            'answer': 'You can search for products using the search bar at the top of any page. You can also browse by category by clicking on the category links on the homepage or in the navigation menu.'
        },
        {
            'question': 'How do I view product details?',
            'answer': 'Click on any product to view its full details, including description, price, seller information, and more.'
        },
        {
            'question': 'Are the prices negotiable?',
            'answer': 'Yes, many sellers are open to negotiation. You can contact the seller directly using the provided contact information on the product details page to discuss price.'
        },
        {
            'question': 'How do I contact a seller?',
            'answer': 'On the product details page, you\'ll find the seller\'s contact information. You can reach out to them via phone or message to inquire about the product.'
        }
    ],
    'orders': [
        {
            'question': 'How do I place an order?',
            'answer': 'To place an order, add items to your cart by clicking the "Add to Cart" button on product pages. Then proceed to checkout where you\'ll confirm your order details and payment method.'
        },
        {
            'question': 'What payment methods are accepted?',
            'answer': 'We currently support mobile money payments (M-Pesa, Tigo Pesa, Airtel Money) and cash on delivery for some areas. More payment options will be added in the future.'
        },
        {
            'question': 'How can I track my order?',
            'answer': 'After placing an order, you can track its status by going to "My Account" > "Orders". You\'ll see the current status of each order, from processing to delivery.'
        },
        {
            'question': 'Can I cancel my order?',
            'answer': 'You can cancel orders that are still in the "Pending" status. Go to "My Account" > "Orders", find the order you wish to cancel, and click the "Cancel Order" button if available.'
        }
    ],
    'marketplace': [
        {
            'question': 'How do I sell my product on the marketplace?',
            'answer': 'To sell a product, ensure you\'re logged in and have completed your profile with a valid phone number. Then click on "Add Product" in the navigation menu. Fill in the product details including title, description, price, and image.'
        },
        {
            'question': 'How do I edit or remove my product listing?',
            'answer': 'Go to "My Account" > "My Products" to see all your listings. From there, you can edit or remove any of your product listings.'
        },
        {
            'question': 'Are there any fees for selling on the marketplace?',
            'answer': 'Currently, basic listings on ChuoSmart are free of charge. We may introduce premium listing options in the future with additional benefits.'
        },
        {
            'question': 'How do I get more visibility for my products?',
            'answer': 'Add clear, high-quality images and detailed descriptions. Use relevant keywords in your product title and description. Keep your prices competitive, and respond quickly to inquiries from potential buyers.'
        }
    ],
    'technical': [
        {
            'question': 'The website is not loading properly. What should I do?',
            'answer': 'Try clearing your browser cache and cookies, or try using a different browser. If the problem persists, please contact our technical support team.'
        },
        {
            'question': 'Why can\'t I upload images to my product listing?',
            'answer': 'Make sure your image file is in JPG, PNG, or WebP format and doesn\'t exceed 5MB in size. Also, check your internet connection as slow connections may cause upload failures.'
        },
        {
            'question': 'How do I enable notifications?',
            'answer': 'When prompted by your browser to allow notifications, click "Allow". If you\'ve previously denied notifications, you\'ll need to change this in your browser settings.'
        },
        {
            'question': 'Is my data secure on this platform?',
            'answer': 'Yes, we take data security very seriously. We use encryption for sensitive information and follow industry best practices for data protection. For more details, please read our Privacy Policy.'
        }
    ]
}

# Guides for common tasks
GUIDES = [
    {
        'title': 'How to Complete Your Profile',
        'description': 'A step-by-step guide to setting up your profile information.',
        'icon': 'fas fa-id-card',
        'link': '#profile-guide'
    },
    {
        'title': 'Selling Your First Product',
        'description': 'Learn how to create an effective product listing that sells.',
        'icon': 'fas fa-tag',
        'link': '#selling-guide'
    },
    {
        'title': 'Safe Trading Tips',
        'description': 'Best practices for safe buying and selling in the marketplace.',
        'icon': 'fas fa-shield-alt',
        'link': '#safety-guide'
    },
    {
        'title': 'Using the Blog Platform',
        'description': 'Share your knowledge by creating blog posts on ChuoSmart.',
        'icon': 'fas fa-blog',
        'link': '#blog-guide'
    }
]

# Contact channels
CONTACT_CHANNELS = [
    {
        'title': 'Email Support',
        'description': 'Get help via email at support@chuosmart.com',
        'icon': 'fas fa-envelope',
        'action': 'mailto:support@chuosmart.com'
    },
    {
        'title': 'WhatsApp Support',
        'description': 'Chat with us on WhatsApp for immediate assistance',
        'icon': 'fab fa-whatsapp',
        'action': 'https://wa.me/255712345678'
    },
    {
        'title': 'Call Center',
        'description': 'Call us at +255 712 345 678',
        'icon': 'fas fa-phone-alt',
        'action': 'tel:+255712345678'
    },
    {
        'title': 'Submit Ticket',
        'description': 'Create a support ticket for complex issues',
        'icon': 'fas fa-ticket-alt',
        'action': '/contact/'
    }
]
