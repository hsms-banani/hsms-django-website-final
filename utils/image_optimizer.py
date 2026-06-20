from io import BytesIO
from PIL import Image
from django.core.files import File
import logging

logger = logging.getLogger(__name__)

def optimize_image(image_field, max_width=1920, max_height=1080, quality=80):
    """
    Optimizes an uploaded image by resizing and compressing it.
    Returns the optimized File object or None if optimization fails or isn't needed.
    """
    if not image_field:
        return None

    try:
        # Open the image using Pillow
        img = Image.open(image_field)
        
        # Determine format. Pillow sometimes loses the format when doing operations.
        img_format = img.format
        if not img_format:
            img_format = 'JPEG'
            
        # Avoid optimizing SVGs, GIFs, or other formats that might lose animation/structure
        if img_format not in ['JPEG', 'PNG', 'WEBP']:
            return None

        # Convert to RGB if it's a JPEG but somehow has an alpha channel or palette
        if img.mode in ("RGBA", "P") and img_format == 'JPEG':
            img = img.convert("RGB")

        # Resize the image using the thumbnail method (maintains aspect ratio)
        # We only resize if the image is larger than the max dimensions
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Save the optimized image to a BytesIO object
        output = BytesIO()
        
        # For PNGs, 'optimize' flag is supported but 'quality' is primarily for JPEGs/WEBP
        if img_format in ['JPEG', 'WEBP']:
            img.save(output, format=img_format, quality=quality, optimize=True)
        else:
            img.save(output, format=img_format, optimize=True)
            
        output.seek(0)
        
        return File(output, name=image_field.name)

    except Exception as e:
        logger.error(f"Error optimizing image {image_field.name}: {e}")
        return None
