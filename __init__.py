"""
TeamCity Monitor - Un outil de surveillance des builds TeamCity
"""

__version__ = "1.0.0"

from .core.client import ApiClient
from .api.services.teamcity_fetcher import fetch_teamcity_builds_alternative

__all__ = ['ApiClient', 'fetch_teamcity_builds_alternative'] 