# type: ignore
"""Test cases for sfd.common.datetime module.

This module provides comprehensive test coverage for datetime utility functions
including time formatting and date range generation functionality.
"""

import datetime

import pytest
from django.test import TestCase

from sfd.common.datetime import format_hhmm, month_dates


@pytest.mark.unit
@pytest.mark.common
class FormatHHMMTest(TestCase):
    """Test cases for the format_hhmm function.

    Tests the formatting of timedelta objects into HH:MM string format,
    covering various time ranges, edge cases, and boundary conditions.
    """

    def test_format_hhmm_zero_timedelta(self):
        """Test formatting of zero timedelta.

        Verifies that a zero timedelta is properly formatted as "00:00".
        """
        td = datetime.timedelta(seconds=0)
        result = format_hhmm(td)
        self.assertEqual(result, "00:00")

    def test_format_hhmm_minutes_only(self):
        """Test formatting of timedelta with minutes only.

        Tests various minute values without full hours to ensure
        proper formatting and zero-padding.
        """
        test_cases = [
            (datetime.timedelta(minutes=1), "00:01"),
            (datetime.timedelta(minutes=30), "00:30"),
            (datetime.timedelta(minutes=59), "00:59"),
        ]

        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_hhmm(td)
                self.assertEqual(result, expected)

    def test_format_hhmm_hours_only(self):
        """Test formatting of timedelta with full hours only.

        Tests various hour values without additional minutes to ensure
        proper formatting of the minutes component as "00".
        """
        test_cases = [
            (datetime.timedelta(hours=1), "01:00"),
            (datetime.timedelta(hours=8), "08:00"),
            (datetime.timedelta(hours=12), "12:00"),
            (datetime.timedelta(hours=24), "24:00"),
        ]

        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_hhmm(td)
                self.assertEqual(result, expected)

    def test_format_hhmm_hours_and_minutes(self):
        """Test formatting of timedelta with both hours and minutes.

        Tests various combinations of hours and minutes to ensure
        proper formatting of complete time values.
        """
        test_cases = [
            (datetime.timedelta(hours=1, minutes=30), "01:30"),
            (datetime.timedelta(hours=8, minutes=45), "08:45"),
            (datetime.timedelta(hours=12, minutes=15), "12:15"),
            (datetime.timedelta(hours=23, minutes=59), "23:59"),
        ]

        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_hhmm(td)
                self.assertEqual(result, expected)

    def test_format_hhmm_with_seconds(self):
        """Test formatting of timedelta with seconds component.

        Verifies that seconds are properly truncated/ignored and do not
        affect the HH:MM formatting, following the expected behavior.
        """
        test_cases = [
            (datetime.timedelta(hours=2, minutes=30, seconds=45), "02:30"),
            (datetime.timedelta(minutes=15, seconds=30), "00:15"),
            (datetime.timedelta(seconds=45), "00:00"),
            (datetime.timedelta(seconds=119), "00:01"),  # 1 minute 59 seconds = 1 minute
        ]

        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_hhmm(td)
                self.assertEqual(result, expected)

    def test_format_hhmm_large_values(self):
        """Test formatting of timedelta with large hour values.

        Tests that the function properly handles timedelta values exceeding
        24 hours, which may occur in work time calculations or duration tracking.
        """
        test_cases = [
            (datetime.timedelta(hours=25), "25:00"),
            (datetime.timedelta(hours=48, minutes=30), "48:30"),
            (datetime.timedelta(hours=100, minutes=15), "100:15"),
        ]

        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_hhmm(td)
                self.assertEqual(result, expected)

    def test_format_hhmm_from_total_seconds(self):
        """Test formatting of timedelta created from total seconds.

        Verifies proper handling when timedelta is created from various
        total_seconds values, ensuring correct conversion logic.
        """
        test_cases = [
            (datetime.timedelta(seconds=3661), "01:01"),  # 1 hour 1 minute 1 second
            (datetime.timedelta(seconds=7200), "02:00"),  # 2 hours exactly
            (datetime.timedelta(seconds=90061), "25:01"),  # 25 hours 1 minute 1 second
        ]

        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_hhmm(td)
                self.assertEqual(result, expected)


@pytest.mark.unit
@pytest.mark.common
class MonthDatesTest(TestCase):
    """Test cases for the month_dates function.

    Tests the generation of complete date lists for given months,
    covering various month lengths, leap years, and edge cases.
    """

    def test_month_dates_january(self):
        """Test month_dates for January (31-day month).

        Verifies that all 31 dates in January are properly generated
        and returned in the correct order.
        """
        given_date = datetime.date(2024, 1, 15)  # January 15, 2024
        result = month_dates(given_date)

        self.assertEqual(len(result), 31)
        self.assertEqual(result[0], datetime.date(2024, 1, 1))
        self.assertEqual(result[-1], datetime.date(2024, 1, 31))

        # Verify all dates are consecutive
        for i in range(1, len(result)):
            expected_date = result[0] + datetime.timedelta(days=i)
            self.assertEqual(result[i], expected_date)

    def test_month_dates_april(self):
        """Test month_dates for April (30-day month).

        Verifies that all 30 dates in April are properly generated
        for a month with fewer than 31 days.
        """
        given_date = datetime.date(2024, 4, 10)  # April 10, 2024
        result = month_dates(given_date)

        self.assertEqual(len(result), 30)
        self.assertEqual(result[0], datetime.date(2024, 4, 1))
        self.assertEqual(result[-1], datetime.date(2024, 4, 30))

    def test_month_dates_february_non_leap(self):
        """Test month_dates for February in a non-leap year.

        Verifies that February in a non-leap year returns exactly
        28 dates, testing the leap year logic.
        """
        given_date = datetime.date(2023, 2, 14)  # February 14, 2023 (non-leap year)
        result = month_dates(given_date)

        self.assertEqual(len(result), 28)
        self.assertEqual(result[0], datetime.date(2023, 2, 1))
        self.assertEqual(result[-1], datetime.date(2023, 2, 28))

    def test_month_dates_february_leap_year(self):
        """Test month_dates for February in a leap year.

        Verifies that February in a leap year returns exactly
        29 dates, properly handling the leap day.
        """
        given_date = datetime.date(2024, 2, 14)  # February 14, 2024 (leap year)
        result = month_dates(given_date)

        self.assertEqual(len(result), 29)
        self.assertEqual(result[0], datetime.date(2024, 2, 1))
        self.assertEqual(result[-1], datetime.date(2024, 2, 29))

    def test_month_dates_first_day_of_month(self):
        """Test month_dates when given the first day of the month.

        Ensures the function works correctly when the input date
        is already the first day of the target month.
        """
        given_date = datetime.date(2024, 3, 1)  # March 1, 2024
        result = month_dates(given_date)

        self.assertEqual(len(result), 31)
        self.assertEqual(result[0], datetime.date(2024, 3, 1))
        self.assertEqual(result[-1], datetime.date(2024, 3, 31))

    def test_month_dates_last_day_of_month(self):
        """Test month_dates when given the last day of the month.

        Ensures the function works correctly when the input date
        is the last day of the target month.
        """
        given_date = datetime.date(2024, 5, 31)  # May 31, 2024
        result = month_dates(given_date)

        self.assertEqual(len(result), 31)
        self.assertEqual(result[0], datetime.date(2024, 5, 1))
        self.assertEqual(result[-1], datetime.date(2024, 5, 31))

    def test_month_dates_december(self):
        """Test month_dates for December (year-end month).

        Verifies proper handling of the last month of the year,
        ensuring no year-boundary issues occur.
        """
        given_date = datetime.date(2024, 12, 25)  # December 25, 2024
        result = month_dates(given_date)

        self.assertEqual(len(result), 31)
        self.assertEqual(result[0], datetime.date(2024, 12, 1))
        self.assertEqual(result[-1], datetime.date(2024, 12, 31))

    def test_month_dates_different_years(self):
        """Test month_dates for the same month in different years.

        Verifies that the function correctly handles the same month
        across different years, especially for leap year variations.
        """
        # Test February in different years
        feb_2023 = month_dates(datetime.date(2023, 2, 15))  # Non-leap year
        feb_2024 = month_dates(datetime.date(2024, 2, 15))  # Leap year

        self.assertEqual(len(feb_2023), 28)
        self.assertEqual(len(feb_2024), 29)

        # Test same month, different years
        jan_2023 = month_dates(datetime.date(2023, 1, 15))
        jan_2024 = month_dates(datetime.date(2024, 1, 15))

        self.assertEqual(len(jan_2023), 31)
        self.assertEqual(len(jan_2024), 31)
        self.assertNotEqual(jan_2023[0].year, jan_2024[0].year)

    def test_month_dates_all_months(self):
        """Test month_dates for all 12 months to verify correct lengths.

        Comprehensive test ensuring that each month returns the correct
        number of days according to the calendar system.
        """
        year = 2024  # Leap year for complete testing
        expected_lengths = {
            1: 31,  # January
            2: 29,  # February (leap year)
            3: 31,  # March
            4: 30,  # April
            5: 31,  # May
            6: 30,  # June
            7: 31,  # July
            8: 31,  # August
            9: 30,  # September
            10: 31,  # October
            11: 30,  # November
            12: 31,  # December
        }

        for month, expected_length in expected_lengths.items():
            with self.subTest(month=month):
                given_date = datetime.date(year, month, 15)
                result = month_dates(given_date)
                self.assertEqual(len(result), expected_length)
                self.assertEqual(result[0], datetime.date(year, month, 1))
                self.assertEqual(result[-1], datetime.date(year, month, expected_length))

    def test_month_dates_return_type(self):
        """Test that month_dates returns the correct data types.

        Verifies that the function returns a list containing
        datetime.date objects as specified in the function signature.
        """
        given_date = datetime.date(2024, 6, 15)
        result = month_dates(given_date)

        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(date, datetime.date) for date in result))

    def test_month_dates_order_verification(self):
        """Test that month_dates returns dates in chronological order.

        Ensures that the returned list is properly sorted from the
        first day to the last day of the month.
        """
        given_date = datetime.date(2024, 8, 20)
        result = month_dates(given_date)

        # Verify chronological order
        for i in range(1, len(result)):
            self.assertLess(result[i - 1], result[i])

        # Verify consecutive days
        for i in range(1, len(result)):
            expected_diff = datetime.timedelta(days=1)
            actual_diff = result[i] - result[i - 1]
            self.assertEqual(actual_diff, expected_diff)
