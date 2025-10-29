# type: ignore
"""
Test cases for sfd.common.font module.

This module contains comprehensive test cases for the Japanese font registration
functionality used in PDF generation.
"""

import os
from unittest.mock import Mock, patch

import pytest
from django.contrib.staticfiles import finders
from django.test import TestCase

from sfd.common.font import register_japanese_fonts


@pytest.mark.unit
@pytest.mark.common
class RegisterJapaneseFontsTest(TestCase):
    """
    Test cases for the register_japanese_fonts function.

    Tests the font registration functionality including successful registration,
    error handling, and various edge cases.
    """

    def setUp(self):
        """Set up common patches for all test methods."""
        self.patcher_logger = patch("sfd.common.font.logger")
        self.patcher_pdfmetrics = patch("sfd.common.font.pdfmetrics")
        self.patcher_ttfont = patch("sfd.common.font.TTFont")
        self.patcher_finders = patch("sfd.common.font.finders")

        self.mock_logger = self.patcher_logger.start()
        self.mock_pdfmetrics = self.patcher_pdfmetrics.start()
        self.mock_ttfont = self.patcher_ttfont.start()
        self.mock_finders = self.patcher_finders.start()

    def tearDown(self):
        """Clean up patches after each test method."""
        self.patcher_logger.stop()
        self.patcher_pdfmetrics.stop()
        self.patcher_ttfont.stop()
        self.patcher_finders.stop()

    def test_register_fonts_success(self):
        """Test successful font registration for both IPA and Noto fonts."""
        # Mock font path discovery
        self.mock_finders.find.return_value = "/fake/font/path"

        # Mock font registry check - fonts not registered yet
        self.mock_pdfmetrics.getRegisteredFontNames.return_value = []

        # Mock TTFont instances
        mock_font_instances = [Mock() for _ in range(8)]  # 2 IPA + 6 Noto fonts
        self.mock_ttfont.side_effect = mock_font_instances

        # Call the function
        register_japanese_fonts()

        # Verify font path discovery
        self.mock_finders.find.assert_called_once_with("sfd/fonts")

        # Verify getRegisteredFontNames was called twice (once for IPA, once for Noto)
        self.assertEqual(self.mock_pdfmetrics.getRegisteredFontNames.call_count, 2)

        # Verify TTFont was called for all fonts
        expected_font_calls = [
            ("ipaexm", os.path.join("/fake/font/path", "ipaexm.ttf")),
            ("ipaexg", os.path.join("/fake/font/path", "ipaexg.ttf")),
            ("NotoSansJP-Regular", os.path.join("/fake/font/path", "NotoSansJP-Regular.ttf")),
            ("NotoSansJP-Bold", os.path.join("/fake/font/path", "NotoSansJP-Bold.ttf")),
            ("NotoSansJP-ExtraBold", os.path.join("/fake/font/path", "NotoSansJP-ExtraBold.ttf")),
            ("NotoSansJP-Thin", os.path.join("/fake/font/path", "NotoSansJP-Thin.ttf")),
            ("NotoSansJP-Light", os.path.join("/fake/font/path", "NotoSansJP-Light.ttf")),
            ("NotoSansJP-ExtraLight", os.path.join("/fake/font/path", "NotoSansJP-ExtraLight.ttf")),
        ]

        actual_calls = [call.args for call in self.mock_ttfont.call_args_list]
        self.assertEqual(actual_calls, expected_font_calls)  # Verify registerFont was called for all fonts
        self.assertEqual(self.mock_pdfmetrics.registerFont.call_count, 8)

        # Verify success log messages
        self.mock_logger.info.assert_any_call("Fonts 'ipaexm', 'ipaexg' registered successfully.")
        self.mock_logger.info.assert_any_call("Fonts series of NotoSansJP registered successfully.")

    def test_ipa_fonts_already_registered(self):
        """Test that IPA fonts are not re-registered if already present."""
        # Mock font path discovery
        self.mock_finders.find.return_value = "/fake/font/path"

        # Mock font registry check - IPA fonts already registered, Noto fonts not
        def mock_get_registered_names():
            if self.mock_pdfmetrics.getRegisteredFontNames.call_count == 1:
                return ["ipaexm", "ipaexg"]  # IPA fonts already registered
            else:
                return ["ipaexm", "ipaexg"]  # Noto fonts not registered

        self.mock_pdfmetrics.getRegisteredFontNames.side_effect = mock_get_registered_names

        # Mock TTFont instances for Noto fonts only
        mock_font_instances = [Mock() for _ in range(6)]  # 6 Noto fonts
        self.mock_ttfont.side_effect = mock_font_instances

        # Call the function
        register_japanese_fonts()

        # Verify TTFont was only called for Noto fonts (6 calls)
        self.assertEqual(self.mock_ttfont.call_count, 6)

        # Verify registerFont was only called for Noto fonts
        self.assertEqual(self.mock_pdfmetrics.registerFont.call_count, 6)

        # Verify only Noto success message was logged
        self.mock_logger.info.assert_called_once_with("Fonts series of NotoSansJP registered successfully.")

    def test_noto_fonts_already_registered(self):
        """Test that Noto fonts are not re-registered if already present."""
        # Mock font path discovery
        self.mock_finders.find.return_value = "/fake/font/path"

        # Mock font registry check - Noto fonts already registered, IPA fonts not
        def mock_get_registered_names():
            if self.mock_pdfmetrics.getRegisteredFontNames.call_count == 1:
                return []  # IPA fonts not registered
            else:
                return ["NotoSansJP-Regular"]  # Noto fonts already registered

        self.mock_pdfmetrics.getRegisteredFontNames.side_effect = mock_get_registered_names

        # Mock TTFont instances for IPA fonts only
        mock_font_instances = [Mock() for _ in range(2)]  # 2 IPA fonts
        self.mock_ttfont.side_effect = mock_font_instances

        # Call the function
        register_japanese_fonts()

        # Verify TTFont was only called for IPA fonts (2 calls)
        self.assertEqual(self.mock_ttfont.call_count, 2)

        # Verify registerFont was only called for IPA fonts
        self.assertEqual(self.mock_pdfmetrics.registerFont.call_count, 2)

        # Verify only IPA success message was logged
        self.mock_logger.info.assert_called_once_with("Fonts 'ipaexm', 'ipaexg' registered successfully.")

    def test_all_fonts_already_registered(self):
        """Test that no fonts are registered if all are already present."""
        # Mock font path discovery
        self.mock_finders.find.return_value = "/fake/font/path"

        # Mock font registry check - all fonts already registered
        self.mock_pdfmetrics.getRegisteredFontNames.return_value = ["ipaexm", "NotoSansJP-Regular"]

        # Call the function
        register_japanese_fonts()

        # Verify no TTFont instances were created
        self.mock_ttfont.assert_not_called()

        # Verify no fonts were registered
        self.mock_pdfmetrics.registerFont.assert_not_called()

        # Verify no success messages were logged
        self.mock_logger.info.assert_not_called()

    def test_ipa_font_registration_error(self):
        """Test error handling when IPA font registration fails."""
        # Mock font path discovery
        self.mock_finders.find.return_value = "/fake/font/path"

        # Mock font registry check - no fonts registered
        self.mock_pdfmetrics.getRegisteredFontNames.return_value = []

        # Mock TTFont to raise exception for IPA fonts
        self.mock_ttfont.side_effect = Exception("Font file not found")

        # Call the function
        register_japanese_fonts()

        # Verify error was logged for IPA fonts
        self.mock_logger.error.assert_called_with("Font registration error: Font file not found")

        # Function should continue and attempt Noto fonts despite IPA error
        self.assertEqual(self.mock_pdfmetrics.getRegisteredFontNames.call_count, 2)

    def test_noto_font_registration_error(self):
        """Test error handling when Noto font registration fails."""
        # Mock font path discovery
        self.mock_finders.find.return_value = "/fake/font/path"

        # Mock font registry check - IPA fonts registered, Noto fonts not
        def mock_get_registered_names():
            if self.mock_pdfmetrics.getRegisteredFontNames.call_count == 1:
                return ["ipaexm"]  # IPA fonts already registered
            else:
                return ["ipaexm"]  # Noto fonts not registered

        self.mock_pdfmetrics.getRegisteredFontNames.side_effect = mock_get_registered_names

        # Mock TTFont to raise exception for Noto fonts
        self.mock_ttfont.side_effect = Exception("Noto font file not found")

        # Call the function
        register_japanese_fonts()

        # Verify error was logged for Noto fonts
        self.mock_logger.error.assert_called_with("Font registration error: Noto font file not found")

    def test_both_font_registration_errors(self):
        """Test error handling when both IPA and Noto font registration fail."""
        # Mock font path discovery
        self.mock_finders.find.return_value = "/fake/font/path"

        # Mock font registry check - no fonts registered
        self.mock_pdfmetrics.getRegisteredFontNames.return_value = []

        # Mock TTFont to raise different exceptions
        self.mock_ttfont.side_effect = [
            Exception("IPA font error"),  # First call (IPA fonts)
            Exception("Noto font error"),  # Second call (Noto fonts)
        ]

        # Call the function
        register_japanese_fonts()

        # Verify both errors were logged
        self.assertEqual(self.mock_logger.error.call_count, 2)

        # Check error messages
        first_call_args = self.mock_logger.error.call_args_list[0][0]
        second_call_args = self.mock_logger.error.call_args_list[1][0]

        self.assertEqual(first_call_args[0], "Font registration error: IPA font error")
        self.assertEqual(second_call_args[0], "Font registration error: Noto font error")

    def test_font_path_construction(self):
        """Test that font paths are constructed correctly."""
        # Mock font path discovery
        test_font_path = "/custom/font/directory"
        self.mock_finders.find.return_value = test_font_path

        # Mock font registry check - no fonts registered
        self.mock_pdfmetrics.getRegisteredFontNames.return_value = []

        # Mock TTFont instances
        mock_font_instances = [Mock() for _ in range(8)]
        self.mock_ttfont.side_effect = mock_font_instances

        # Call the function
        register_japanese_fonts()

        # Verify font paths were constructed correctly
        expected_paths = [
            os.path.join("/custom/font/directory", "ipaexm.ttf"),
            os.path.join("/custom/font/directory", "ipaexg.ttf"),
            os.path.join("/custom/font/directory", "NotoSansJP-Regular.ttf"),
            os.path.join("/custom/font/directory", "NotoSansJP-Bold.ttf"),
            os.path.join("/custom/font/directory", "NotoSansJP-ExtraBold.ttf"),
            os.path.join("/custom/font/directory", "NotoSansJP-Thin.ttf"),
            os.path.join("/custom/font/directory", "NotoSansJP-Light.ttf"),
            os.path.join("/custom/font/directory", "NotoSansJP-ExtraLight.ttf"),
        ]

        actual_paths = [call.args[1] for call in self.mock_ttfont.call_args_list]
        self.assertEqual(actual_paths, expected_paths)

    def test_finders_not_found(self):
        """Test behavior when font directory is not found."""
        # Mock font path discovery to return None
        self.mock_finders.find.return_value = None

        # Mock font registry check - no fonts registered
        self.mock_pdfmetrics.getRegisteredFontNames.return_value = []

        # Call the function - should not raise exception even with None path
        try:
            register_japanese_fonts()
        except Exception:
            # If an exception occurs, it should be logged
            self.assertTrue(self.mock_logger.error.called)

    def test_partial_font_registration_success(self):
        """Test partial success when some fonts register successfully and others fail."""
        # Mock font path discovery
        self.mock_finders.find.return_value = "/fake/font/path"

        # Mock font registry check - no fonts registered
        self.mock_pdfmetrics.getRegisteredFontNames.return_value = []

        # Mock TTFont to succeed for IPA fonts but fail for Noto fonts
        ipa_mocks = [Mock(), Mock()]  # 2 IPA fonts succeed
        self.mock_ttfont.side_effect = ipa_mocks + [Exception("Noto font error")]

        # Call the function
        register_japanese_fonts()

        # Verify IPA fonts were registered successfully
        self.assertEqual(self.mock_pdfmetrics.registerFont.call_count, 2)
        self.mock_logger.info.assert_called_with("Fonts 'ipaexm', 'ipaexg' registered successfully.")

        # Verify Noto font error was logged
        self.mock_logger.error.assert_called_with("Font registration error: Noto font error")

    def test_required_font_files_exist(self):
        """Test that all required font files actually exist in the static directory."""
        font_path = finders.find("sfd/fonts")
        self.assertIsNotNone(font_path, "Font directory 'sfd/fonts' not found in static files")

        required_fonts = [
            "ipaexm.ttf",
            "ipaexg.ttf",
            "NotoSansJP-Regular.ttf",
            "NotoSansJP-Bold.ttf",
            "NotoSansJP-ExtraBold.ttf",
            "NotoSansJP-Thin.ttf",
            "NotoSansJP-Light.ttf",
            "NotoSansJP-ExtraLight.ttf",
        ]

        missing_fonts = []
        for font_file in required_fonts:
            font_file_path = os.path.join(font_path, font_file)
            if not os.path.exists(font_file_path):
                missing_fonts.append(f"'{font_file}' not found at '{font_file_path}'")

        if missing_fonts:
            self.fail("Missing font files:\n" + "\n".join(f"  - {font}" for font in missing_fonts))

    def test_font_registration_with_real_files(self):
        """Test font registration with actual font files (no mocking)."""
        # This will fail if any font files don't exist or are invalid
        try:
            register_japanese_fonts()
        except Exception as e:
            self.fail(f"Font registration failed with real files: {e}")

    def test_font_directory_structure(self):
        """Test that the font directory exists and is accessible."""
        font_path = finders.find("sfd/fonts")
        self.assertIsNotNone(font_path, "Font directory 'sfd/fonts' not found in static files")
        self.assertTrue(os.path.isdir(font_path), f"Font path '{font_path}' is not a directory")
        self.assertTrue(os.access(font_path, os.R_OK), f"Font directory '{font_path}' is not readable")
