"""
BRIA RMBG-1.4 background removal processor.
"""

import logging

from PIL import Image
from transformers import pipeline

logger = logging.getLogger(__name__)


class BRIAProcessor:
    """BRIA RMBG-1.4 background removal processor."""

    def __init__(self, device: str = "cpu"):
        """
        Initialize BRIA RMBG-1.4 model for background removal.

        Args:
            device: Device to run on ('cpu', 'cuda', 'mps')
        """
        self.device = device
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the BRIA model."""
        try:
            logger.info(f"Initializing BRIA RMBG-1.4 model on {self.device}")
            self.model = pipeline(
                "image-segmentation",
                model="briaai/RMBG-1.4",
                trust_remote_code=True,
                device=self.device,
            )
            logger.info("✓ BRIA RMBG-1.4 model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BRIA model: {e}")
            raise

    def remove_background(self, image: Image.Image) -> Image.Image:
        """
        Remove background from an image using BRIA RMBG-1.4.

        Args:
            image: Input PIL Image

        Returns:
            PIL Image with transparent background
        """
        if self.model is None:
            raise RuntimeError("BRIA model not initialized")
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")
            result = self.model(image, return_mask=True)
            mask = result
            if not isinstance(mask, Image.Image):
                if hasattr(mask, "cpu"):
                    mask = mask.cpu()
                mask = Image.fromarray((mask * 255).astype("uint8"))
            if mask.mode != "L":
                mask = mask.convert("L")
            no_bg_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
            no_bg_image.paste(image, mask=mask)
            return no_bg_image
        except Exception as e:
            logger.error(f"BRIA background removal failed: {e}")
            raise

    def remove_background_bytes(self, image_bytes: bytes) -> bytes:
        """
        Remove background from image bytes using BRIA RMBG-1.4.

        Args:
            image_bytes: Input image as bytes

        Returns:
            PNG bytes with transparent background
        """
        try:
            import io

            image = Image.open(io.BytesIO(image_bytes))
            result = self.remove_background(image)
            img_buffer = io.BytesIO()
            result.save(img_buffer, format="PNG")
            return img_buffer.getvalue()
        except Exception as e:
            logger.error(f"BRIA bytes processing failed: {e}")
            raise


_bria_processor: BRIAProcessor | None = None


def get_bria_processor(device: str = "cpu") -> BRIAProcessor:
    """Get or create a global BRIA processor instance."""
    global _bria_processor
    if _bria_processor is None:
        _bria_processor = BRIAProcessor(device=device)
    return _bria_processor


def remove_background_bria(image_bytes: bytes, device: str = "cpu") -> bytes:
    """
    Remove background using BRIA RMBG-1.4 (compatible with existing API).

    Args:
        image_bytes: Input image as bytes
        device: Device to run on

    Returns:
        PNG bytes with transparent background
    """
    processor = get_bria_processor(device)
    return processor.remove_background_bytes(image_bytes)
