import os
import uuid
import logging
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_delete
from django.dispatch import receiver

# Set up logging for debugging
logger = logging.getLogger(__name__)


def _get_avatar_upload_path(instance, filename):
    """
    Generate a unique upload path for user avatars.

    Args:
        instance: The User model instance
        filename: Original filename (we'll ignore this and generate our own)

    Returns:
        str: Path in format 'avatars/YYYY/MM/unique_filename.jpg'
    """
    now = timezone.now()
    basepath = 'avatars'

    # Generate a unique filename using UUID4
    unique_filename = str(uuid.uuid4())

    # Always use .jpg extension since we convert all images to JPEG
    new_filename = f"{unique_filename}.jpg"

    # Create path: avatars/2025/09/unique_id.jpg
    return os.path.join(basepath, now.strftime("%Y/%m"), new_filename)


class User(AbstractUser):
    email = models.EmailField("email address", blank=False, unique=True)
    phone = models.CharField("Phone Number", max_length=15)
    address = models.TextField("Address", blank=True, null=True)
    avatar = models.ImageField(upload_to=_get_avatar_upload_path, blank=True, null=True)

    # Track original avatar for change detection and cleanup
    _original_avatar = None
    _original_avatar_name = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the model and store original avatar value.
        This helps us detect when avatar field changes.
        """
        super().__init__(*args, **kwargs)
        # Store original avatar value to detect changes
        self._original_avatar = self.avatar
        self._original_avatar_name = self.avatar.name if self.avatar else None

    def save(self, *args, **kwargs):
        """
        Override save method to handle avatar processing and cleanup.
        """
        # Check if this is avatar processing to prevent recursion
        skip_avatar_processing = kwargs.pop('skip_avatar_processing', False)

        # Track if we need to delete old avatar
        old_avatar_to_delete = None

        # Only process avatar if it exists and we're not skipping processing
        if self.avatar and not skip_avatar_processing:
            # Check if avatar has actually changed
            if self._avatar_has_changed():
                try:
                    # Store old avatar name before processing (for deletion)
                    if self.pk and self._original_avatar_name:
                        old_avatar_to_delete = self._original_avatar_name

                    self._process_avatar()
                    logger.info(f"Avatar processed for user {self.username}")

                except Exception as e:
                    logger.error(f"Error processing avatar for user {self.username}: {e}")


        super().save(*args, **kwargs)

        # Delete old avatar file AFTER successful save
        if old_avatar_to_delete:
            self._delete_avatar_file(old_avatar_to_delete)

        # Update the original avatar tracker after successful save
        self._original_avatar = self.avatar
        self._original_avatar_name = self.avatar.name if self.avatar else None

    def _avatar_has_changed(self):
        """
        Check if the avatar field has been changed.

        Returns:
            bool: True if avatar has changed, False otherwise
        """
        # For new instances, always consider it changed if avatar exists
        if not self.pk:
            return bool(self.avatar)

        # Handle None cases
        if not self._original_avatar and not self.avatar:
            return False  # Both None, no change

        if bool(self._original_avatar) != bool(self.avatar):
            return True  # One is None, other isn't

        # Compare file names for reliable detection
        current_name = self.avatar.name if self.avatar else None

        # If it's the same name, no change
        if self._original_avatar_name == current_name:
            return False

        # If current avatar is an uploaded file (doesn't have a storage name yet), it's new
        if hasattr(self.avatar, 'temporary_file_path') or not current_name:
            return True

        # Different names = change
        return self._original_avatar_name != current_name

    def _process_avatar(self):
        """
        Process the uploaded avatar image:
        - Crop to center square
        - Resize to 512x512
        - Convert to JPEG format
        - Optimize quality
        """
        try:
            img = Image.open(self.avatar)

            # Define target size
            target_size = (512, 512)

            # Get current dimensions
            width, height = img.size

            # Calculate center crop coordinates for square aspect ratio
            min_dimension = min(width, height)
            left = (width - min_dimension) // 2
            top = (height - min_dimension) // 2
            right = left + min_dimension
            bottom = top + min_dimension

            # Crop to center square
            img = img.crop((left, top, right, bottom))

            # Resize to target size using high-quality resampling
            img = img.resize(target_size, Image.Resampling.LANCZOS)

            # Convert to RGB mode (removes alpha channel, ensures JPEG compatibility)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Prepare output buffer
            output_buffer = BytesIO()

            # Save as JPEG with good quality
            img.save(output_buffer, format='JPEG', quality=90, optimize=True)
            output_buffer.seek(0)

            # Generate new filename using our upload path function
            new_filename = _get_avatar_upload_path(self, 'avatar.jpg')

            # Create new InMemoryUploadedFile
            self.avatar = InMemoryUploadedFile(
                file=output_buffer,
                field_name='avatar',
                name=os.path.basename(new_filename),  # Just filename
                content_type='image/jpeg',
                size=len(output_buffer.getvalue()),
                charset=None
            )

            # Set the full path for Django's storage system
            self.avatar.name = new_filename

            # Clean up PIL image
            img.close()

        except Exception as e:
            # Log the specific error for debugging
            logger.error(f"Avatar processing failed: {e}")


    def _delete_avatar_file(self, file_path):
        """
        Safely delete an avatar file from storage.

        Args:
            file_path: Path to the file to delete
        """
        try:
            # Django's default storage to delete the file
            from django.core.files.storage import default_storage

            if default_storage.exists(file_path):
                default_storage.delete(file_path)
                logger.info(f"Deleted old avatar file: {file_path}")
            else:
                logger.warning(f"Avatar file not found for deletion: {file_path}")

        except Exception as e:
            logger.error(f"Error deleting avatar file {file_path}: {e}")

    def delete_avatar(self):
        """
        Public method to delete the current avatar.
        """
        if self.avatar:
            old_name = self.avatar.name
            self.avatar.delete(save=False)
            self.avatar = None
            self.save()
            logger.info(f"User {self.username} deleted their avatar: {old_name}")

    def __str__(self):
        return f"{self.username}"


@receiver(post_delete, sender=User)
def cleanup_avatar_on_user_delete(sender, instance, **kwargs):
    """
    Delete avatar file when user is deleted.
    """
    if instance.avatar:
        try:
            instance.avatar.delete(save=False)
            logger.info(f"Cleaned up avatar for deleted user: {instance.username}")
        except Exception as e:
            logger.error(f"Error cleaning up avatar for deleted user {instance.username}: {e}")