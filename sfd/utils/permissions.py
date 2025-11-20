"""
Permission utilities for controlling access to sensitive encrypted data.

This module provides utilities to check if a user has permission to view
encrypted personal information.
"""

from django.contrib.auth.models import User


def can_view_personal_info(user: User) -> bool:
    """
    Check if user has permission to view personal information.

    Args:
        user: Django User object

    Returns:
        True if user has permission, False otherwise
    """
    if not user or not user.is_authenticated:
        return False

    # Superusers can always view
    if user.is_superuser:
        return True

    # Check for specific permission
    return user.has_perm("sfd.view_personal_info")


def can_edit_personal_info(user: User) -> bool:
    """
    Check if user has permission to edit personal information.

    Args:
        user: Django User object

    Returns:
        True if user has permission, False otherwise
    """
    if not user or not user.is_authenticated:
        return False

    # Superusers can always edit
    if user.is_superuser:
        return True

    # Check for specific permission
    return user.has_perm("sfd.change_personal_info")


def mask_sensitive_data(data: str, visible_chars: int = 3) -> str:
    """
    Mask sensitive data for users without proper permissions.

    Args:
        data: The sensitive data to mask
        visible_chars: Number of characters to keep visible

    Returns:
        Masked string

    Example:
        >>> mask_sensitive_data("山田太郎", 1)
        "山***"
        >>> mask_sensitive_data("080-1234-5678", 3)
        "080********"
    """
    if not data:
        return ""

    if len(data) <= visible_chars:
        return "*" * len(data)

    return data[:visible_chars] + "*" * (len(data) - visible_chars)


def get_masked_person_name(person, user: User) -> str:
    """
    Get person's full name, masked if user doesn't have permission.

    Args:
        person: Person model instance
        user: Django User object

    Returns:
        Full name or masked name based on permissions
    """
    if can_view_personal_info(user):
        return f"{person.family_name} {person.name}"

    # Return masked version
    family_masked = mask_sensitive_data(person.family_name, 1)
    name_masked = mask_sensitive_data(person.name, 1)
    return f"{family_masked} {name_masked}"


def get_masked_phone(phone_number: str, user: User) -> str:
    """
    Get phone number, masked if user doesn't have permission.

    Args:
        phone_number: Phone number string
        user: Django User object

    Returns:
        Phone number or masked phone based on permissions
    """
    if can_view_personal_info(user):
        return phone_number

    return mask_sensitive_data(phone_number, 3)
