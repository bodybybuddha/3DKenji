"""Thumbnail generation and fallback logic."""

from typing import Optional
from pathlib import Path
import base64


GENERIC_PLACEHOLDER_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <defs>
    <style>
      .bg { fill: #f0f0f0; }
      .text { fill: #999; font-family: Arial, sans-serif; font-size: 14px; text-anchor: middle; }
      .icon { fill: #ccc; }
    </style>
  </defs>
  <rect class="bg" width="200" height="200"/>
  <text class="text" x="100" y="90">3D Model</text>
  <text class="text" x="100" y="110" style="font-size: 12px;">No Preview</text>
  <path class="icon" d="M100,50 L150,70 L150,130 L100,150 L50,130 L50,70 Z" stroke="#ccc" stroke-width="1" fill="none"/>
</svg>
"""


class ThumbnailService:
    """Service for generating and managing thumbnails."""

    @staticmethod
    def get_placeholder_thumbnail() -> str:
        """
        Get a placeholder thumbnail as a data URI.

        Returns:
            Data URI (data:image/svg+xml;base64,...) for placeholder image.
        """
        svg_bytes = GENERIC_PLACEHOLDER_SVG.encode("utf-8")
        b64_svg = base64.b64encode(svg_bytes).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64_svg}"

    @staticmethod
    def get_thumbnail_for_model(
        model_filename: str,
        preview_image_url: Optional[str] = None,
        storage_key: Optional[str] = None,
    ) -> str:
        """
        Get thumbnail URL for a 3D model.

        Logic:
        1. If preview_image_url provided, use it
        2. If could generate render from model file, use it (stub for now)
        3. Otherwise, return placeholder

        Args:
            model_filename: Name of the model file (e.g., "cube.stl").
            preview_image_url: Optional URL to preview image.
            storage_key: Storage key for the model file (for future rendering).

        Returns:
            URL or data URI for thumbnail image.
        """
        # If preview image provided, use it
        if preview_image_url:
            return preview_image_url

        # TODO: If storage_key provided and model is renderable (.stl, .3mf),
        # could generate a render using a 3D viewer library
        # For MVP, just return placeholder

        return ThumbnailService.get_placeholder_thumbnail()

    @staticmethod
    def get_project_thumbnail(
        preview_image_url: Optional[str] = None,
        featured_model_filename: Optional[str] = None,
    ) -> str:
        """
        Get thumbnail for a project.

        Logic:
        1. If preview_image_url provided, use it
        2. If featured model filename provided, try to render it
        3. Otherwise, return placeholder

        Args:
            preview_image_url: Optional custom project thumbnail URL.
            featured_model_filename: Optional featured model to render.

        Returns:
            URL or data URI for project thumbnail.
        """
        if preview_image_url:
            return preview_image_url

        # For MVP, just return placeholder
        return ThumbnailService.get_placeholder_thumbnail()
