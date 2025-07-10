from django.db import models
from django.contrib.auth.models import User
from .universities_colleges_tanzania import universities_data

class Subscription(models.Model):
    LEVEL_CHOICES = [
        ('Free', 'Free'),
        ('Bronze', 'Bronze'),
        ('Silver', 'Silver'),
        ('Gold', 'Gold'),
    ]
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='Free')
    price = models.FloatField()
    benefits = models.TextField()

    @staticmethod
    def populate_default_data():
        if Subscription.objects.count() == 0:
            Subscription.objects.create(
                level='Free',
                price=0.0,
                benefits='Basic access to the platform, limited product listings, basic support'
            )
            Subscription.objects.create(
                level='Bronze',
                price=2000.0,
                benefits='Increased product listings, priority support, access to promotional tools'
            )
            Subscription.objects.create(
                level='Silver',
                price=5000.0,
                benefits='All Bronze benefits, featured product placement, advanced analytics, most popular'
            )
            Subscription.objects.create(
                level='Gold',
                price=10000.0,
                benefits='All Silver benefits, unlimited product listings, dedicated account manager, premium support'
            )

    def __str__(self):
        return self.level

class Customer(models.Model):
    UNIVERSITY_CHOICES = [(uni['name'], uni['name']) for uni in universities_data]
    COLLEGE_CHOICES = [(college, college) for uni in universities_data for college in uni['colleges']]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    is_university_student = models.BooleanField(default=True, help_text="Check if you are a university student")
    university = models.CharField(max_length=200, choices=UNIVERSITY_CHOICES, null=True, blank=True)
    college = models.CharField(max_length=200, choices=COLLEGE_CHOICES, null=True, blank=True)
    block_number = models.CharField(max_length=200, null=True, blank=True)
    room_number = models.CharField(max_length=200, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)  # New field for phone number
    
    def get_default_subscription():
        return Subscription.objects.get(level='Free').id

    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, default=get_default_subscription)

    def __str__(self):
        return str(self.id)


CATEGORY = (
    ('M', 'Mobiles'),
    ('El', 'Electronics'),
    ('B', 'Books'),
    ('C', 'Clothing'),
    ('AC', 'Accessories'),
    ('S', 'Services'),
)


class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    category = models.CharField(choices=CATEGORY, max_length=2)
    description = models.TextField()
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    image = models.ImageField(upload_to='product_images')
    # New field for optimized WebP images
    image_webp = models.ImageField(upload_to='product_images/webp', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        
        # Generate slug from title if slug is not set
        if not self.slug:
            original_slug = slugify(self.title)
            unique_slug = original_slug
            num = 1
            
            # Make sure the slug is unique
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{original_slug}-{num}"
                num += 1
                
            self.slug = unique_slug
        
        # First save to get an ID if this is a new product
        super(Product, self).save(*args, **kwargs)
        
        # Only convert if there's an image and no existing WebP
        if self.image and not self.image_webp:
            try:
                from core.utils.image_optimizer import optimize_image
                # Create WebP version
                optimized = optimize_image(self.image, quality=85, format="WEBP")
                if optimized:
                    self.image_webp.save(
                        f"{self.id}_webp.webp",
                        optimized,
                        save=False
                    )
                    # Save again but don't trigger this method recursively
                    super(Product, self).save(update_fields=['image_webp'])
            except ImportError:
                # If the optimizer module is not available, just continue
                pass
            except Exception as e:
                # Log the error but don't prevent saving
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating WebP image: {e}")

    def __str__(self):
        return self.title


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Cart for {self.user.username}"


STATUS = (
    ('Delivered', 'Delivered'),
    ('Pending', 'Pending'),
    ('Cancelled', 'Cancelled'),
    ('On The Way', 'On The Way'),
    ('Received', 'Received'),
    ('Paid', 'Paid'),
    
)

class OrderPlaced(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    ordered_date = models.DateTimeField(auto_now_add=True)
    price = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=200, choices=STATUS, default='Pending')
    

    def __str__(self):
        return f"{self.quantity} of {self.product.title} placed by {self.user.username}"


class Banners(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='banner_images')

    def __str__(self):
        return self.title


class Blog(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True, null=True)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    thumbnail = models.ImageField(upload_to='blog_thumbnails', blank=True, null=True)
    # New field for optimized WebP thumbnail
    thumbnail_webp = models.ImageField(upload_to='blog_thumbnails/webp', blank=True, null=True)
    is_markdown = models.BooleanField(default=True, help_text="Whether content is written in Markdown format")
    
    def save(self, *args, **kwargs):
        # Generate slug from title if not set
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
            # Ensure slug uniqueness
            original_slug = self.slug
            counter = 1
            while Blog.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # First save to get an ID if this is a new blog post
        super(Blog, self).save(*args, **kwargs)
        
        # Only convert if there's a thumbnail and no existing WebP
        if self.thumbnail and not self.thumbnail_webp:
            try:
                from core.utils.image_optimizer import optimize_image
                # Create WebP version
                optimized = optimize_image(self.thumbnail, quality=85, format="WEBP")
                if optimized:
                    self.thumbnail_webp.save(
                        f"{self.id}_webp.webp",
                        optimized,
                        save=False
                    )
                    # Save again but don't trigger this method recursively
                    super(Blog, self).save(update_fields=['thumbnail_webp'])
            except ImportError:
                # If the optimizer module is not available, just continue
                pass
            except Exception as e:
                # Log the error but don't prevent saving
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating WebP thumbnail: {e}")

    def __str__(self):
        return self.title


class SubscriptionPayment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    payment_proof = models.ImageField(upload_to='payment_proofs/')
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Verified', 'Verified'), ('Rejected', 'Rejected')],
        default='Pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.username} - {self.subscription.level} ({self.status})"

class NewsletterSubscriber(models.Model):
    """Model for newsletter subscribers"""
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=50, default='website', 
                             help_text="Where the subscription originated from")
    is_active = models.BooleanField(default=True)
    date_subscribed = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.email


