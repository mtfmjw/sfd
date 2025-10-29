import logging
import os

from django.contrib.staticfiles import finders
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)


def register_japanese_fonts():
    """
    Register Japanese fonts for PDF generation using ReportLab.

    This function registers Japanese TrueType fonts with ReportLab's PDF generation
    system to enable proper Japanese text rendering in PDF documents. It registers
    two font families: IPA fonts and Noto Sans JP fonts with various weights.

    Font Families Registered:
        IPA Fonts:
            - ipaexm: IPA Mincho font for serif Japanese text
            - ipaexg: IPA Gothic font for sans-serif Japanese text

        Noto Sans JP Fonts:
            - NotoSansJP-Regular: Regular weight
            - NotoSansJP-Bold: Bold weight
            - NotoSansJP-ExtraBold: Extra bold weight
            - NotoSansJP-Thin: Thin weight
            - NotoSansJP-Light: Light weight
            - NotoSansJP-ExtraLight: Extra light weight

    Raises:
        Exception: Logs error if font files are not found or registration fails.
                  The function continues execution even if some fonts fail to register.

    Note:
        - Font files must be located in the 'sfd/fonts' static directory
        - Fonts are only registered if not already present in ReportLab's registry
        - Errors are logged but do not stop the registration process
        - This function should be called during Django application startup

    Example:
        >>> register_japanese_fonts()
        # Fonts are now available for use in ReportLab PDF generation
        # canvas.setFont('NotoSansJP-Regular', 12)
    """
    font_path = finders.find("sfd/fonts")

    if "ipaexm" not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont("ipaexm", os.path.join(font_path, "ipaexm.ttf")))  # type: ignore
            pdfmetrics.registerFont(TTFont("ipaexg", os.path.join(font_path, "ipaexg.ttf")))  # type: ignore
            logger.info("Fonts 'ipaexm', 'ipaexg' registered successfully.")
        except Exception as e:
            logger.error(f"Font registration error: {e}")

    if "NotoSansJP-Regular" not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont("NotoSansJP-Regular", os.path.join(font_path, "NotoSansJP-Regular.ttf")))  # type: ignore
            pdfmetrics.registerFont(TTFont("NotoSansJP-Bold", os.path.join(font_path, "NotoSansJP-Bold.ttf")))  # type: ignore
            pdfmetrics.registerFont(TTFont("NotoSansJP-ExtraBold", os.path.join(font_path, "NotoSansJP-ExtraBold.ttf")))  # type: ignore
            pdfmetrics.registerFont(TTFont("NotoSansJP-Thin", os.path.join(font_path, "NotoSansJP-Thin.ttf")))  # type: ignore
            pdfmetrics.registerFont(TTFont("NotoSansJP-Light", os.path.join(font_path, "NotoSansJP-Light.ttf")))  # type: ignore
            pdfmetrics.registerFont(TTFont("NotoSansJP-ExtraLight", os.path.join(font_path, "NotoSansJP-ExtraLight.ttf")))  # type: ignore
            logger.info("Fonts series of NotoSansJP registered successfully.")
        except Exception as e:
            logger.error(f"Font registration error: {e}")
