"""
Email module for Sacco Ticket System
Handles email fetching, sending, and AI analysis
"""

from .fetcher import EmailFetcher
from .analyzer import AIEmailAnalyzer

__all__ = ['EmailFetcher', 'AIEmailAnalyzer']