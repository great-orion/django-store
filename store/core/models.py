import os
import uuid
import logging
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models.signals import post_delete
from django.dispatch import receiver
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.text import slugify

# Set up logging for debugging
logger = logging.getLogger(__name__)

User = get_user_model()


def _get_product_image_upload_path(instance, filename):
    """
    Generate a unique upload path for product images.

    Returns:
        str: Path in format 'products/YYYY/MM/category_slug/unique_filename.jpg'
    """
    now = timezone.now()
    basepath = 'products'

    # Generate a unique filename using UUID4
    unique_filename = str(uuid.uuid4())

    # Always use .jpg extension since we convert all images to JPEG
    new_filename = f"{unique_filename}.jpg"

    # Include category in path for better organization
    category_slug = instance.category.slug if instance.category else 'uncategorized'

    # Create path: products/2025/09/electronics/unique_id.jpg
    return os.path.join(
        basepath,
        now.strftime("%Y/%m"),
        category_slug,
        new_filename
    )

class Base(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    deleted_date = models.DateTimeField(default=None, null=True, blank=True)
    deleted = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        abstract = True


class Product(Base):

    # STATUS_ENABLED = 0
    # STATUS_DISABLED = 1
    # STATUS_DELETED = 2
    # STATUS_CHOICES = ((STATUS_ENABLED, 'Enabled'),
    #                   (STATUS_DISABLED, 'Disabled'),
    #                   (STATUS_DELETED, 'Deleted'))

    # Static Attribute
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    price = models.IntegerField(default=0)
    discount = models.FloatField(default=0, help_text="Discount percentage (0.0 to 100.0)")
    enabled = models.BooleanField(default=True)
    description = models.TextField()
    category = models.ForeignKey('Category', on_delete=models.PROTECT, related_name='products')
    image = models.ImageField(upload_to=_get_product_image_upload_path, null=True, blank=True)
    count = models.IntegerField(default=0)
    # status = models.IntegerField(default=STATUS_ENABLED, choices=STATUS_CHOICES)

    # Image processing tracking
    _original_image = None
    _original_image_name = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the model and store original image value.
        This helps us detect when image field changes.
        """
        super().__init__(*args, **kwargs)
        # Store original image value to detect changes
        self._original_image = self.image
        self._original_image_name = self.image.name if self.image else None

    def save(self, *args, **kwargs):
        """
        Override save method to handle image processing, slug generation, and cleanup.
        """
        # Auto-generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name)

        # Check if this is image processing to prevent recursion
        skip_image_processing = kwargs.pop('skip_image_processing', False)

        # Track if we need to delete old image
        old_image_to_delete = None

        # Only process image if it exists and we're not skipping processing
        if self.image and not skip_image_processing:
            # Check if image has actually changed
            if self._image_has_changed():
                try:
                    # Store old image name before processing (for deletion)
                    if self.pk and self._original_image_name:
                        old_image_to_delete = self._original_image_name

                    self._process_image()
                    logger.info(f"Image processed for product {self.name}")

                except Exception as e:
                    logger.error(f"Error processing image for product {self.name}: {e}")

        # Call parent save method
        super().save(*args, **kwargs)

        # Delete old image file AFTER successful save
        if old_image_to_delete:
            self._delete_image_file(old_image_to_delete)

        # Update the original image tracker after successful save
        self._original_image = self.image
        self._original_image_name = self.image.name if self.image else None

    def _image_has_changed(self):
        """
        Check if the image field has been changed.
        """
        # For new instances, always consider it changed if image exists
        if not self.pk:
            return bool(self.image)

        # Handle None cases
        if not self._original_image and not self.image:
            return False  # Both None, no change

        if bool(self._original_image) != bool(self.image):
            return True  # One is None, other isn't

        # Compare file names for reliable detection
        current_name = self.image.name if self.image else None

        # If it's the same name, no change
        if self._original_image_name == current_name:
            return False

        # If current image is an uploaded file (doesn't have a storage name yet), it's new
        if hasattr(self.image, 'temporary_file_path') or not current_name:
            return True

        # Different names = change
        return self._original_image_name != current_name

    def _process_image(self):
        """
        Process the uploaded product image:
        - Resize to optimal dimensions for web display
        - Convert to JPEG format
        - Optimize for web use
        - Maintain aspect ratio with smart cropping if needed
        """
        try:
            img = Image.open(self.image)

            # Define target dimensions
            max_width = 800
            max_height = 800

            # Get current dimensions
            width, height = img.size

            # Calculate scaling to fit within max dimensions while maintaining aspect ratio
            scale_width = max_width / width
            scale_height = max_height / height
            scale = min(scale_width, scale_height)

            # Only resize if image is larger than target
            if scale < 1:
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")

            # Convert to RGB mode (removes alpha channel, ensures JPEG compatibility)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                logger.info(f"Converted image mode from {img.mode} to RGB")

            # Prepare output buffer
            output_buffer = BytesIO()

            # Save as JPEG with good quality for product images
            img.save(output_buffer, format='JPEG', quality=85, optimize=True)
            output_buffer.seek(0)

            # Generate new filename using our upload path function
            new_filename = _get_product_image_upload_path(self, 'product.jpg')

            # Create new InMemoryUploadedFile
            self.image = InMemoryUploadedFile(
                file=output_buffer,
                field_name='image',
                name=os.path.basename(new_filename),  # Just filename
                content_type='image/jpeg',
                size=len(output_buffer.getvalue()),
                charset=None
            )

            # Set the full path for Django's storage system
            self.image.name = new_filename

            # Clean up PIL image
            img.close()

        except Exception as e:
            # Log the specific error for debugging
            logger.error(f"Image processing failed: {e}")
            raise

    def _delete_image_file(self, file_path):
        """
        Safely delete a product image file from storage.
        """
        try:
            # Use Django's default storage to delete the file
            from django.core.files.storage import default_storage

            if default_storage.exists(file_path):
                default_storage.delete(file_path)
                logger.info(f"Deleted old product image file: {file_path}")
            else:
                logger.warning(f"Product image file not found for deletion: {file_path}")

        except Exception as e:
            logger.error(f"Error deleting product image file {file_path}: {e}")


    # we use str in the admin & template
    def __str__(self):
        return f"{self.name}"


@receiver(post_delete, sender=Product)
def cleanup_image_on_product_delete(sender, instance, **kwargs):
    """
    Delete product image file when product is deleted.
    """
    if instance.image:
        try:
            instance.image.delete(save=False)
            logger.info(f"Cleaned up image for deleted product: {instance.name}")
        except Exception as e:
            logger.error(f"Error cleaning up image for deleted product {instance.name}: {e}")


class Category(Base):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    parent = models.ForeignKey('Category', null=True, blank=True, default=None,
                               on_delete= models.PROTECT, related_name='children')

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


class Comment(Base):
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"



class InvoiceItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE)
    count = models.IntegerField()
    price = models.FloatField()
    discount = models.FloatField()
    total = models.FloatField()
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.product.name}, No: {self.count}"

class Invoice(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    number = models.IntegerField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    total = models.FloatField()
    discount = models.FloatField(default=0)
    description = models.TextField(null=True, blank=True)
    address = models.CharField(max_length=255)
    vat = models.FloatField(default=9)

    def __str__(self):
        return f"{self.user} - {self.number}"


class Payment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_DONE = 'done'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = ((STATUS_PENDING, 'Pending'),
                      (STATUS_ERROR, 'Error'),
                      (STATUS_DONE, 'Done'))

    invoice = models.OneToOneField(Invoice, on_delete=models.PROTECT)
    total = models.FloatField()
    ref = models.CharField(max_length=255, null=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=20, default=STATUS_PENDING)
    authority = models.CharField(max_length=255)
    description = models.TextField()
    user_ip = models.CharField(max_length=20, null=True, blank=True)
    # Error handling
    error_code = models.CharField(max_length=50, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.invoice.user.username}: {self.invoice.id}"