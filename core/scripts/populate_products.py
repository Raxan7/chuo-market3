import os
import django
import requests
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from core.models import Customer  # Import Customer model
from core.models import Product  # Import Product model

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Commerce.settings")  # Update with your project name
django.setup()

# Get the first available user from Customer
customer = Customer.objects.first()
if not customer:
    raise Exception("❌ No customers found! Add a customer first.")

user = customer.user  # Extract associated user

# Define product categories
CATEGORY = {
    'M': 'Mobiles',
    'El': 'Electronics',
    'B': 'Books',
    'C': 'Clothing',
    'AC': 'Accessories',
}

# Sample Products with Image URLs
PRODUCTS = {
    'M': [
        {"title": "iPhone 14", "description": "Latest Apple smartphone", "price": 999, "discount_price": 899, "image": "https://example.com/iphone.jpg"},
        {"title": "Samsung Galaxy S23", "description": "High-performance Android phone", "price": 899, "discount_price": 799, "image": "https://example.com/galaxy.jpg"},
        {"title": "OnePlus 11", "description": "Flagship killer", "price": 699, "discount_price": 649, "image": "https://example.com/oneplus.jpg"},
        {"title": "Google Pixel 7", "description": "Best Android camera phone", "price": 799, "discount_price": 749, "image": "https://example.com/pixel.jpg"},
    ],
    'El': [
        {"title": "Sony Headphones", "description": "Noise-cancelling headphones", "price": 299, "discount_price": 249, "image": "https://example.com/headphones.jpg"},
        {"title": "LG OLED TV", "description": "4K Smart TV", "price": 1299, "discount_price": 1199, "image": "https://example.com/tv.jpg"},
        {"title": "JBL Speaker", "description": "Portable Bluetooth speaker", "price": 149, "discount_price": 129, "image": "https://example.com/speaker.jpg"},
        {"title": "Apple Watch", "description": "Smartwatch with health features", "price": 399, "discount_price": 349, "image": "https://example.com/applewatch.jpg"},
    ],
}

# Function to download and save images
def download_image(image_url, product):
    if not image_url:
        return None

    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            img_temp = NamedTemporaryFile(delete=True)
            img_temp.write(response.content)
            img_temp.flush()
            product.image.save(f"{product.title}.jpg", File(img_temp), save=True)
            print(f"✅ Image saved for {product.title}")
    except Exception as e:
        print(f"⚠️ Failed to download image for {product.title}: {e}")

# Add Products to Database with Images & User
for cat_code, products in PRODUCTS.items():
    for prod in products:
        product = Product.objects.create(
            user=user,  # Assign user from Customer
            title=prod["title"],
            category=cat_code,
            description=prod["description"],
            price=prod["price"],
            discount_price=prod["discount_price"]
        )

        # Download and attach image
        download_image(prod["image"], product)

print(f"✅ Products with images added successfully for user {user.username}!")
