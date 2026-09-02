from django.db import models
from core.storage import private_payment_storage
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
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
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('product-detail', kwargs={'slug': self.slug})
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
                from core.image_utils import optimize_image
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
        return self.title or "Unnamed"


class Blog(models.Model):
    UPLOAD_METHOD_CHOICES = [
        ('local', 'Local Storage (Device)'),
        ('cloudinary', 'Cloudinary (Cloud Storage)'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True, null=True)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Image storage options - support both local and Cloudinary
    thumbnail = models.ImageField(upload_to='blog_thumbnails', blank=True, null=True, help_text="Local image storage")
    # New field for Cloudinary-hosted images
    thumbnail_cloudinary = models.CharField(max_length=500, blank=True, null=True, help_text="Cloudinary image URL")
    # New field for optimized WebP thumbnail
    thumbnail_webp = models.ImageField(upload_to='blog_thumbnails/webp', blank=True, null=True)
    
    # Track which upload method was used (local or cloudinary)
    upload_method = models.CharField(
        max_length=20, 
        choices=UPLOAD_METHOD_CHOICES, 
        default='local',
        help_text="Method used to upload the thumbnail image"
    )
    
    is_markdown = models.BooleanField(default=False, help_text="Whether content is written in Markdown format")
    category = models.CharField(max_length=100, blank=True, null=True)
    
    def clean_html_content(self):
        """Clean HTML content from TinyMCE to prevent data attributes from being stored"""
        if not self.content:
            return self.content
            
        import re
        import html
        
        content = self.content
        
        # If content is wrapped in braces (common TinyMCE issue)
        if content.startswith('{') and content.endswith('}') and '<' in content[:100]:
            content = content[1:-1].strip()
        
        # Remove all data-* attributes (safer regex pattern)
        content = re.sub(r'\s+data-[a-zA-Z0-9_-]+=["|\'][^"|\']*["|\']', '', content)
        
        # Remove problematic class attributes that might cause rendering issues
        content = re.sub(r'\s+class=["|\']_[^"|\']*["|\']', '', content)
        content = re.sub(r'\s+class=["|\'][^"|\']*["|\']', '', content)  # Remove all classes
        
        # Remove other problematic attributes
        content = re.sub(r'\s+tabindex=["|\'][^"|\']*["|\']', '', content)
        content = re.sub(r'\s+style=["|\'][^"|\']*["|\']', '', content)  # Remove inline styles
        
        # Handle escaped HTML entities
        content = html.unescape(content)
        
        # If Markdown format, do additional Markdown-specific processing
        if self.is_markdown:
            # No additional processing needed here, will be rendered by the markdown filter
            pass
        else:
            # Process any Markdown-style formatting within HTML content
            # These operations match those in our custom template filter
            
            # Handle **bold** syntax (convert to <strong>)
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            
            # Handle *italic* syntax (convert to <em>)
            # Use negative lookbehind/lookahead to avoid matching inside **text**
            content = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<em>\1</em>', content)
            
            # Handle __bold__ alternate syntax
            content = re.sub(r'__(.*?)__', r'<strong>\1</strong>', content)
            
            # Handle _italic_ alternate syntax
            content = re.sub(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', r'<em>\1</em>', content)
        
        return content
    
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
        
        # Always clean the content regardless of markdown or HTML
        cleaned_content = self.clean_html_content()
        if cleaned_content:
            self.content = cleaned_content
        
        # First save to get an ID if this is a new blog post
        super(Blog, self).save(*args, **kwargs)
        
        # Only convert if there's a thumbnail and no existing WebP
        if self.thumbnail and not self.thumbnail_webp:
            try:
                from core.image_utils import optimize_image
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
    payment_proof = models.ImageField(
        upload_to='payment_proofs/',
        storage=private_payment_storage,
    )
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


class UserNewsletterPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='newsletter_preference')
    newsletter = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} newsletter preference"


def _get_newsletter_preference(user):
    if not getattr(user, 'pk', None):
        return None
    preference, _ = UserNewsletterPreference.objects.get_or_create(user=user)
    return preference


def _get_user_newsletter(self):
    preference = _get_newsletter_preference(self)
    return preference.newsletter if preference else False


def _set_user_newsletter(self, value):
    preference = _get_newsletter_preference(self)
    if preference is None:
        return
    preference.newsletter = bool(value)
    preference.save()


User.add_to_class('newsletter', property(_get_user_newsletter, _set_user_newsletter))


class SentEmail(models.Model):
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=300)
    body = models.TextField(help_text="HTML content of the email")
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_emails')
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('sent', 'Sent'), ('failed', 'Failed')], default='sent')

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Sent Email'
        verbose_name_plural = 'Sent Emails'

    def __str__(self):
        return f"To: {self.recipient_email} - {self.subject}"


class NewsletterSendLog(models.Model):
    """Tracks daily newsletter digest sends to prevent duplicate sends."""
    subscriber_email = models.EmailField()
    sent_date = models.DateField()
    categories = models.CharField(max_length=255, blank=True, help_text="Comma-separated list of categories included")
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('sent', 'Sent'), ('failed', 'Failed')], default='sent')

    class Meta:
        unique_together = ('subscriber_email', 'sent_date')
        verbose_name = 'Newsletter Send Log'
        verbose_name_plural = 'Newsletter Send Logs'

    def __str__(self):
        return f"{self.subscriber_email} - {self.sent_date} ({self.status})"


class NewsletterTestSend(models.Model):
    """Logs admin test/debug newsletter sends."""
    recipient_email = models.EmailField()
    categories = models.CharField(max_length=255, help_text="Comma-separated categories selected")
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='sent')

    class Meta:
        verbose_name = 'Newsletter Test Send'
        verbose_name_plural = 'Newsletter Test Sends'

    def __str__(self):
        return f"Test to {self.recipient_email} - {self.categories} ({self.status})"


class AccountDeletionRequest(models.Model):
    PRODUCT_CHOICES = [
        ('chuosmart', 'ChuoSmart'),
        ('potea_pata', 'Potea Pata'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    product = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    reason = models.TextField(blank=True)
    consent_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_account_deletion_requests'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def clean(self):
        if not self.user and not self.email:
            raise ValidationError('Provide at least an account login or an email address.')
        if not self.consent_confirmed:
            raise ValidationError('You must confirm consent before submitting this request.')

    def mark_reviewed(self, reviewer, status):
        self.reviewed_by = reviewer
        self.status = status
        self.reviewed_at = timezone.now()
        self.save(update_fields=['reviewed_by', 'status', 'reviewed_at'])

    def __str__(self):
        requester = self.user.username if self.user else (self.email or 'Unknown requester')
        return f"{requester} - {self.get_product_display()} ({self.status})"



class NewsletterJob(models.Model):
    """Durable queue for content-announcement emails.

    Jobs are created after the publishing transaction commits and processed by
    ``python manage.py process_newsletter_queue``. This is intentionally
    database-backed so it works on cPanel/shared hosting without Redis/Celery.
    """
    JOB_TYPE_CHOICES = (
        ('blog', 'Blog'),
        ('product', 'Product'),
        ('course', 'Course'),
        ('course_content', 'Course content'),
        ('job', 'Job'),
        ('material', 'Material'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )

    job_type = models.CharField(max_length=30, choices=JOB_TYPE_CHOICES)
    object_id = models.PositiveBigIntegerField()
    related_ids = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    run_after = models.DateTimeField(default=timezone.now)
    last_error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('created_at',)
        constraints = [
            models.UniqueConstraint(fields=('job_type', 'object_id'), name='unique_newsletter_job_per_object'),
        ]

    def __str__(self):
        return f'{self.job_type}:{self.object_id} ({self.status})'

class NewsletterDelivery(models.Model):
    """Per-recipient state makes newsletter job retries idempotent."""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )
    job = models.ForeignKey(NewsletterJob, on_delete=models.CASCADE, related_name='deliveries')
    recipient_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('job', 'recipient_email'), name='unique_newsletter_job_recipient'),
        ]

    def __str__(self):
        return f'{self.job_id}:{self.recipient_email} ({self.status})'

class MarketingSuppression(models.Model):
    """Email addresses that must never receive ChuoSmart marketing campaigns."""
    REASON_CHOICES = (
        ('unsubscribed', 'Unsubscribed'),
        ('bounce', 'Hard bounce'),
        ('complaint', 'Spam complaint'),
        ('manual', 'Manual suppression'),
    )

    email = models.EmailField(unique=True)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='unsubscribed')
    source = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('email',)

    def save(self, *args, **kwargs):
        self.email = (self.email or '').strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.email} ({self.reason})'


class MarketingCampaign(models.Model):
    """Admin-authored, scheduled marketing campaign with durable per-recipient delivery state."""
    AUDIENCE_CHOICES = (
        ('all_opted_in', 'All opted-in contacts'),
        ('registered_users', 'Registered users who opted in'),
        ('website_subscribers', 'Website newsletter subscribers'),
    )
    KIND_CHOICES = (
        ('announcement', 'Announcement'),
        ('product', 'Product'),
        ('service', 'Service'),
        ('course', 'Course'),
        ('career', 'Career / jobs'),
        ('promotion', 'Promotion'),
        ('reengagement', 'Re-engagement'),
    )
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    name = models.CharField(max_length=180, help_text='Internal campaign name.')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='announcement')
    audience = models.CharField(max_length=30, choices=AUDIENCE_CHOICES, default='all_opted_in')
    subject = models.CharField(max_length=255)
    preheader = models.CharField(max_length=255, blank=True, default='')
    headline = models.CharField(max_length=255)
    body = models.TextField(help_text='Main marketing message. Plain text is rendered safely with paragraphs.')
    hero_image_url = models.URLField(blank=True, default='', help_text='Optional HTTPS image URL for the campaign hero.')
    cta_text = models.CharField(max_length=80, blank=True, default='')
    cta_url = models.URLField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_for = models.DateTimeField(blank=True, null=True)
    minimum_gap_hours = models.PositiveSmallIntegerField(
        default=24,
        help_text='Frequency cap. Set 0 only for genuinely urgent campaigns.',
    )
    max_attempts = models.PositiveSmallIntegerField(default=5)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='marketing_campaigns_created'
    )
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    last_test_sent_at = models.DateTimeField(blank=True, null=True)
    prepared_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def clean(self):
        super().clean()
        if self.cta_text and not self.cta_url:
            raise ValidationError({'cta_url': 'CTA URL is required when CTA text is set.'})
        if self.cta_url and not self.cta_text:
            raise ValidationError({'cta_text': 'CTA text is required when a CTA URL is set.'})
        if self.status == 'scheduled' and not self.scheduled_for:
            raise ValidationError({'scheduled_for': 'Choose a send time for a scheduled campaign.'})

    def __str__(self):
        return f'{self.name} ({self.status})'


class MarketingDelivery(models.Model):
    """Durable per-recipient state for a marketing campaign."""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
        ('suppressed', 'Suppressed'),
    )

    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='deliveries')
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='marketing_deliveries'
    )
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=180, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    run_after = models.DateTimeField(default=timezone.now)
    last_error = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('campaign', 'recipient_email'),
                name='unique_marketing_campaign_recipient',
            ),
        ]
        indexes = [
            models.Index(fields=('status', 'run_after'), name='marketing_queue_idx'),
        ]

    def save(self, *args, **kwargs):
        self.recipient_email = (self.recipient_email or '').strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.campaign_id}:{self.recipient_email} ({self.status})'
