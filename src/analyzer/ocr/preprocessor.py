"""
Image preprocessing for better OCR results.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional, Union
import os


class ImagePreprocessor:
    """Preprocesses images for optimal OCR recognition."""

    def __init__(self):
        self.debug_mode = False

    def preprocess(self, image: Union[str, Image.Image, np.ndarray],
                   output_path: str = None) -> np.ndarray:
        """
        Preprocess image for OCR.

        Args:
            image: Path to image file, PIL Image, or numpy array
            output_path: Optional path to save preprocessed image

        Returns:
            Preprocessed image as numpy array
        """
        # Load image
        img = self._load_image(image)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply preprocessing steps
        processed = self._enhance_text(gray)

        if output_path:
            cv2.imwrite(output_path, processed)

        return processed

    def _load_image(self, image: Union[str, Image.Image, np.ndarray]) -> np.ndarray:
        """Load image from various sources."""
        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"Image not found: {image}")
            return cv2.imread(image)
        elif isinstance(image, Image.Image):
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        elif isinstance(image, np.ndarray):
            return image
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    def _enhance_text(self, gray: np.ndarray) -> np.ndarray:
        """Enhance text visibility in grayscale image."""
        # Resize if too small (OCR works better on larger images)
        height, width = gray.shape
        if width < 1000:
            scale = 1000 / width
            gray = cv2.resize(gray, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(denoised)

        # Binarization - adaptive threshold works well for varied backgrounds
        binary = cv2.adaptiveThreshold(
            contrast, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )

        # Optional: Morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return binary

    def detect_table_regions(self, image: Union[str, Image.Image, np.ndarray]
                             ) -> list:
        """
        Detect table-like regions in image (useful for draft boards).

        Returns list of bounding boxes (x, y, w, h) for detected regions.
        """
        img = self._load_image(image)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        # Filter for rectangular regions
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Filter small regions
            if w > 100 and h > 50:
                regions.append((x, y, w, h))

        return sorted(regions, key=lambda r: (r[1], r[0]))  # Sort by y, then x

    def extract_rows(self, image: Union[str, Image.Image, np.ndarray],
                     min_row_height: int = 20) -> list:
        """
        Extract individual rows from an image (useful for player lists).

        Returns list of cropped row images.
        """
        img = self._load_image(image)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Horizontal projection profile
        h_proj = np.sum(gray, axis=1)

        # Find row boundaries based on white space
        threshold = np.mean(h_proj) * 0.9
        in_row = False
        row_start = 0
        rows = []

        for i, val in enumerate(h_proj):
            if not in_row and val < threshold:
                in_row = True
                row_start = i
            elif in_row and val >= threshold:
                if i - row_start >= min_row_height:
                    rows.append(img[row_start:i, :])
                in_row = False

        return rows

    def crop_region(self, image: Union[str, Image.Image, np.ndarray],
                    bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """Crop a region from the image."""
        img = self._load_image(image)
        x, y, w, h = bbox
        return img[y:y+h, x:x+w]

    def auto_rotate(self, image: Union[str, Image.Image, np.ndarray]) -> np.ndarray:
        """Auto-rotate image if skewed."""
        img = self._load_image(image)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect lines
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)

        if lines is None:
            return img

        # Calculate average angle
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = theta * 180 / np.pi - 90
            if -45 < angle < 45:
                angles.append(angle)

        if not angles:
            return img

        avg_angle = np.median(angles)

        # Rotate if significant skew
        if abs(avg_angle) > 0.5:
            h, w = img.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
            img = cv2.warpAffine(img, matrix, (w, h),
                                  flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)

        return img
