"""
Financial statement generation from XBRL data.
"""

import os
import re
import pandas as pd
from .analyzer import categorize_concepts, identify_contexts, get_statement_data, create_pivot_view


def format_concept_name(concept):
    """
    Format prefixed concept names for display.

    Args:
        concept (str): Concept name

    Returns:
        str: Formatted concept name
    """
    # Remove prefix if present
    if ':' in concept:
        concept = concept.split(':', 1)[1]

    # Add space before each capital letter and capitalize first letter
    formatted = re.sub(r'(?<!^)(?=[A-Z])', ' ', concept)
    return formatted.title()


def create_balance_sheet(df, concepts, context_types, verbose=False):
    """
    Create a formatted balance sheet report.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        concepts (list): List of balance sheet concepts
        context_types (dict): Dictionary mapping context types to context IDs
        verbose (bool): Whether to print detailed generation

    Returns:
        str: Formatted balance sheet report
    """
    # Define sections and their patterns (case-insensitive)
    sections = {
        'Assets': ['asset', 'activo', 'cash', 'inventory', 'receivable', 'property', 'investment'],
        'Liabilities': ['liability', 'pasivo', 'payable', 'debt', 'borrowing', 'loan'],
        'Equity': ['equity', 'patrimonio', 'capital', 'retained', 'earning', 'reserve', 'share']
    }

    report = "BALANCE SHEET\n============\n"

    # Process current and previous periods
    for period_label, context_id in [
        ('Current Period', context_types.get('current_period')),
        ('Previous Period', context_types.get('previous_period'))
    ]:
        if not context_id:
            if verbose:
                print(f"Skipping {period_label} for balance sheet - no context ID available")
            continue

        report += f"\n{period_label}:\n"
        if verbose:
            print(f"\nGenerating balance sheet for {period_label} (context: {context_id})")
        data = get_statement_data(df, concepts, context_id, verbose)

        if data.empty:
            report += "  No data available for this period\n"
            continue

        # Process each section
        for section, patterns in sections.items():
            section_items = []

            # Filter concepts for this section (case-insensitive)
            section_concepts = [c for c in concepts if any(p.lower() in c.lower() for p in patterns)]
            if not section_concepts:
                if verbose:
                    print(f"No concepts found for section: {section}")
                continue

            section_data = data[data['prefixed_concept'].isin(section_concepts)]

            if section_data.empty:
                if verbose:
                    print(f"No data found for section: {section}")
                continue

            # Sort and prepare items
            for _, row in section_data.iterrows():
                concept = format_concept_name(row['prefixed_concept'])
                try:
                    value = row['numeric_value']  # Use the converted numeric value
                    unit = row['unit']
                    section_items.append((concept, unit, value))
                except (ValueError, KeyError):
                    if verbose:
                        print(f"Warning: Could not convert value for {concept}: {row['value']}")

            # Only add section if it has items
            if section_items:
                report += f"\n{section}:\n"
                for concept, unit, value in section_items:
                    report += f"  {concept}: {unit} {value:,.2f}\n"

    return report


def create_income_statement(df, concepts, context_types, verbose=False):
    """
    Create a formatted income statement report.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        concepts (list): List of income statement concepts
        context_types (dict): Dictionary mapping context types to context IDs
        verbose (bool): Whether to print detailed generation

    Returns:
        str: Formatted income statement report
    """
    # Define sections and their patterns (case-insensitive)
    sections = {
        'Revenue': ['revenue', 'ingreso', 'income', 'sale', 'venta'],
        'Expenses': ['expense', 'gasto', 'cost', 'costo', 'charge'],
        'Profit/Loss': ['profit', 'loss', 'ganancia', 'perdida', 'resultado', 'earning'],
        'Other Items': ['tax', 'impuesto', 'comprehensive', 'other', 'otro', 'dividend']
    }

    report = "INCOME STATEMENT\n===============\n"

    # Process current and previous periods
    for period_label, context_id in [
        ('Current Period', context_types.get('current_year_accumulated')),
        ('Previous Period', context_types.get('previous_year_accumulated'))
    ]:
        if not context_id:
            if verbose:
                print(f"Skipping {period_label} for income statement - no context ID available")
            continue

        report += f"\n{period_label}:\n"
        if verbose:
            print(f"\nGenerating income statement for {period_label} (context: {context_id})")
        data = get_statement_data(df, concepts, context_id, verbose)

        if data.empty:
            report += "  No data available for this period\n"
            continue

        # Process each section
        for section, patterns in sections.items():
            section_items = []

            # Filter concepts for this section (case-insensitive)
            section_concepts = [c for c in concepts if any(p.lower() in c.lower() for p in patterns)]
            if not section_concepts:
                if verbose:
                    print(f"No concepts found for section: {section}")
                continue

            section_data = data[data['prefixed_concept'].isin(section_concepts)]

            if section_data.empty:
                if verbose:
                    print(f"No data found for section: {section}")
                continue

            # Sort and prepare items
            for _, row in section_data.iterrows():
                concept = format_concept_name(row['prefixed_concept'])
                try:
                    value = row['numeric_value']  # Use the converted numeric value
                    unit = row['unit']
                    section_items.append((concept, unit, value))
                except (ValueError, KeyError):
                    if verbose:
                        print(f"Warning: Could not convert value for {concept}: {row['value']}")

            # Only add section if it has items
            if section_items:
                report += f"\n{section}:\n"
                for concept, unit, value in section_items:
                    report += f"  {concept}: {unit} {value:,.2f}\n"

    return report


def create_cashflow_statement(df, concepts, context_types, verbose=False):
    """
    Create a formatted cash flow statement report.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        concepts (list): List of cash flow statement concepts
        context_types (dict): Dictionary mapping context types to context IDs
        verbose (bool): Whether to print detailed generation

    Returns:
        str: Formatted cash flow statement report
    """
    # Define sections and their patterns (case-insensitive)
    sections = {
        'Operating Activities': ['operating', 'operacion', 'operation'],
        'Investing Activities': ['investing', 'inversion', 'investment'],
        'Financing Activities': ['financing', 'financiamiento', 'finance'],
        'Cash Summary': ['cashandcashequivalent', 'efectivo', 'netincrease', 'netdecrease', 'beginning', 'end']
    }

    report = "CASH FLOW STATEMENT\n==================\n"

    # Try different context types if specific cash flow contexts aren't available
    context_priorities = [
        ('current_year_accumulated', 'previous_year_accumulated'),  # First choice
        ('current_period', 'previous_period')  # Fallback option
    ]

    for current_key, previous_key in context_priorities:
        current_context = context_types.get(current_key)
        previous_context = context_types.get(previous_key)

        if current_context or previous_context:
            if verbose:
                print(f"Using context types: {current_key} and {previous_key} for cash flow statement")
            break
    else:
        if verbose:
            print("No suitable context types found for cash flow statement")
        return "CASH FLOW STATEMENT\n==================\n\nNo suitable data found for cash flow statement"

    # Process current and previous periods
    for period_label, context_id in [
        ('Current Period', current_context),
        ('Previous Period', previous_context)
    ]:
        if not context_id:
            if verbose:
                print(f"Skipping {period_label} for cash flow statement - no context ID available")
            continue

        report += f"\n{period_label}:\n"
        if verbose:
            print(f"\nGenerating cash flow statement for {period_label} (context: {context_id})")
        data = get_statement_data(df, concepts, context_id, verbose)

        if data.empty:
            report += "  No data available for this period\n"
            continue

        # Process each section
        for section, patterns in sections.items():
            section_items = []

            # Filter concepts for this section (case-insensitive comparison)
            section_concepts = [c for c in concepts if any(p.lower() in c.lower() for p in patterns)]
            if not section_concepts:
                if verbose:
                    print(f"No concepts found for section: {section}")
                continue

            section_data = data[data['prefixed_concept'].isin(section_concepts)]

            if section_data.empty:
                if verbose:
                    print(f"No data found for section: {section}")
                continue

            # Sort and prepare items
            for _, row in section_data.iterrows():
                concept = format_concept_name(row['prefixed_concept'])
                try:
                    value = row['numeric_value']  # Use the converted numeric value
                    unit = row['unit']
                    section_items.append((concept, unit, value))
                except (ValueError, KeyError):
                    if verbose:
                        print(f"Warning: Could not convert value for {concept}: {row['value']}")

            # Only add section if it has items
            if section_items:
                report += f"\n{section}:\n"
                for concept, unit, value in section_items:
                    report += f"  {concept}: {unit} {value:,.2f}\n"

    return report


def generate_financial_statements(df, verbose=False):
    """
    Generate formatted financial statements from XBRL data.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        verbose (bool): Whether to print detailed generation

    Returns:
        str: Formatted financial report
    """
    # Categorize concepts for each statement type
    statement_concepts = categorize_concepts(df, verbose)

    # Identify context periods
    context_types = identify_contexts(df, verbose)

    # Generate reports
    balance_sheet = create_balance_sheet(
        df, statement_concepts['balance_sheet'], context_types, verbose)

    income_statement = create_income_statement(
        df, statement_concepts['income_statement'], context_types, verbose)

    cashflow_statement = create_cashflow_statement(
        df, statement_concepts['cashflow'], context_types, verbose)

    # Combine reports
    full_report = f"{balance_sheet}\n\n{income_statement}\n\n{cashflow_statement}"

    return full_report


def create_excel_report(df, output_file="financial_statements.xlsx", verbose=False):
    """
    Generate Excel file with financial statements as separate sheets.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        output_file (str): Path to save the Excel file
        verbose (bool): Whether to print detailed generation

    Returns:
        str: Path to the saved Excel file
    """
    # Categorize concepts for each statement type
    statement_concepts = categorize_concepts(df, verbose)

    # Identify context periods
    context_types = identify_contexts(df, verbose)

    # Create Excel writer
    with pd.ExcelWriter(output_file) as writer:
        # Balance Sheet - Current Period
        if 'current_period' in context_types:
            bs_data = get_statement_data(
                df, statement_concepts['balance_sheet'], context_types['current_period'], verbose)
            if not bs_data.empty:
                bs_data.to_excel(writer, sheet_name='Balance Sheet (Current)')

        # Balance Sheet - Previous Period
        if 'previous_period' in context_types:
            bs_data_prev = get_statement_data(
                df, statement_concepts['balance_sheet'], context_types['previous_period'], verbose)
            if not bs_data_prev.empty:
                bs_data_prev.to_excel(writer, sheet_name='Balance Sheet (Previous)')

        # Income Statement - Current Year
        if 'current_year_accumulated' in context_types:
            is_data = get_statement_data(
                df, statement_concepts['income_statement'], context_types['current_year_accumulated'], verbose)
            if not is_data.empty:
                is_data.to_excel(writer, sheet_name='Income Statement (Current)')

        # Income Statement - Previous Year
        if 'previous_year_accumulated' in context_types:
            is_data_prev = get_statement_data(
                df, statement_concepts['income_statement'], context_types['previous_year_accumulated'], verbose)
            if not is_data_prev.empty:
                is_data_prev.to_excel(writer, sheet_name='Income Statement (Previous)')

        # Cash Flow Statement - Current Year
        if 'current_year_accumulated' in context_types:
            cf_data = get_statement_data(
                df, statement_concepts['cashflow'], context_types['current_year_accumulated'], verbose)
            if not cf_data.empty:
                cf_data.to_excel(writer, sheet_name='Cash Flow (Current)')

        # Cash Flow Statement - Previous Year
        if 'previous_year_accumulated' in context_types:
            cf_data_prev = get_statement_data(
                df, statement_concepts['cashflow'], context_types['previous_year_accumulated'], verbose)
            if not cf_data_prev.empty:
                cf_data_prev.to_excel(writer, sheet_name='Cash Flow (Previous)')

        # Create a pivotable view of the data
        pivot_df = create_pivot_view(df)
        pivot_df.to_excel(writer, sheet_name='Pivot View')

        # All data sheet for reference
        df.to_excel(writer, sheet_name='All Data')

    if verbose:
        print(f"Financial statements saved to {output_file}")
    return output_file