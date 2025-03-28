"""
XBRL Parser - A module for parsing and analyzing XBRL financial reports.
"""

from .parser import XBRLParser, parse_xbrl_file, find_xbrl_files
from .analyzer import categorize_concepts, identify_contexts
from .generator import generate_financial_statements, create_excel_report

__version__ = '0.1.0'
__all__ = [
    'XBRLParser',
    'parse_xbrl_file',
    'find_xbrl_files',
    'categorize_concepts',
    'identify_contexts',
    'generate_financial_statements',
    'create_excel_report'
]