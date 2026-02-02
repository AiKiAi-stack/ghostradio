"""
QR Code Utility
Generates QR codes for episode and feed links
"""

import io
import qrcode
import base64
from typing import Optional
from .logger import get_logger

logger = get_logger("qrcode_utils")


def generate_qrcode_base64(
    url: str, box_size: int = 10, border: int = 4
) -> Optional[str]:
    """
    Generate a QR code image as a base64 encoded PNG string
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        logger.error(f"Error generating QR code for {url}", error=e)
        return None


def generate_feed_qr_payload(rss_url: str) -> dict:
    """Generate payload for feed QR code including subscription links"""
    qr_data = generate_qrcode_base64(rss_url)

    # Apple Podcasts uses pcast:// or podcasts:// scheme
    apple_podcasts_url = rss_url.replace("http://", "pcast://").replace(
        "https://", "pcast://"
    )

    return {
        "rss_url": rss_url,
        "apple_podcasts_url": apple_podcasts_url,
        "qr_code": qr_data,
    }
