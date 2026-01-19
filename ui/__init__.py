"""
UI module for Sacco Ticket System
Handles user interface components and pages
"""

from .components import UIComponents
from .pages import (
    show_login_section,
    show_main_application,
    show_ai_dashboard,
    show_ticket_management,
    show_user_management,
    show_advanced_analytics,
    show_personal_analytics,
    show_settings
)

__all__ = [
    'UIComponents',
    'show_login_section',
    'show_main_application', 
    'show_ai_dashboard',
    'show_ticket_management',
    'show_user_management',
    'show_advanced_analytics',
    'show_personal_analytics',
    'show_settings'
]