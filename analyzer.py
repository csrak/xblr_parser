"""
Analysis and categorization of XBRL data.
"""

import re
import pandas as pd
from collections import defaultdict


def convert_to_dataframe(facts):
    """
    Convert extracted facts to a pandas DataFrame.

    Args:
        facts (list): List of fact dictionaries

    Returns:
        pandas.DataFrame: DataFrame containing the facts
    """
    df = pd.DataFrame(facts)

    if 'unit' in df.columns:
        df['unit'] = df['unit'].fillna('NoUnit')

    # Process dimensions into separate columns
    if facts and 'dimensions' in facts[0]:
        all_dims = set()
        for fact in facts:
            all_dims.update(fact.get('dimensions', {}).keys())

        # Create columns for dimensions
        for dim in all_dims:
            df[f'dim_{dim}'] = None
            for i, row in df.iterrows():
                dims = row.get('dimensions', {})
                if dim in dims:
                    df.at[i, f'dim_{dim}'] = dims[dim]

        # Drop the dimensions column
        if 'dimensions' in df.columns:
            df = df.drop('dimensions', axis=1)

    # Add numeric value column
    if 'value' in df.columns:
        df['numeric_value'] = pd.to_numeric(df['value'], errors='coerce')

    return df


def analyze_concepts(df, verbose=False):
    """
    Analyze and categorize concepts in the XBRL data.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        verbose (bool): Whether to print detailed analysis

    Returns:
        tuple: (all_concepts, prefixes)
    """
    # Get all unique prefixed concepts
    all_concepts = sorted(df['prefixed_concept'].unique())

    if verbose:
        print(f"\nFound {len(all_concepts)} unique prefixed concepts")

    # Count occurrences and show the most common
    concept_counts = df['prefixed_concept'].value_counts()
    if verbose:
        print("\nTop 20 most common concepts:")
        for concept, count in concept_counts.head(20).items():
            # Get a sample value
            sample_value = df[df['prefixed_concept'] == concept]['numeric_value'].iloc[0]
            print(f"- {concept}: {count} occurrences, sample value: {sample_value}")

    # Group concepts by prefix
    prefixes = defaultdict(list)
    for concept in all_concepts:
        if ':' in concept:
            prefix = concept.split(':', 1)[0]
            prefixes[prefix].append(concept)

    if verbose:
        print("\nConcepts grouped by prefix:")
        for prefix, concepts in prefixes.items():
            print(f"- {prefix}: {len(concepts)} concepts")
            # Show a few examples
            for concept in sorted(concepts)[:3]:
                print(f"  - {concept}")
            if len(concepts) > 3:
                print(f"  - ... and {len(concepts) - 3} more")

    return all_concepts, prefixes


def categorize_concepts(df, verbose=False):
    """
    Categorize concepts into financial statement types.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        verbose (bool): Whether to print detailed categorization

    Returns:
        dict: Dictionary of concept lists by statement type
    """
    # First analyze concepts to understand the taxonomy structure
    all_concepts, prefixes = analyze_concepts(df, verbose)

    # Define common IFRS taxonomy prefixes
    ifrs_prefix = next((p for p in prefixes.keys() if 'ifrs' in p.lower()), None)

    # Balance sheet concepts based on IFRS taxonomy
    balance_sheet_patterns = [
        'Asset', 'Liability', 'Equity', 'Cash', 'Inventory', 'Property',
        'Receivable', 'Payable', 'Debt', 'Investment', 'Activo', 'Pasivo',
        'Patrimonio', 'CashAndCashEquivalent', 'FinancialAsset', 'FinancialLiability',
        'CurrentAsset', 'NonCurrentAsset', 'CurrentLiability', 'NonCurrentLiability',
        'Capital', 'Retained', 'Earning', 'Reserve', 'Share', 'Intangible'
    ]

    # Income statement concepts based on IFRS taxonomy
    income_statement_patterns = [
        'Revenue', 'Income', 'Expense', 'Profit', 'Loss', 'Tax', 'Earning',
        'Cost', 'Operating', 'Finance', 'Dividend', 'ComprehensiveIncome',
        'Gain', 'Sale', 'ProfitBeforeTax', 'ProfitAfterTax', 'Ingreso', 'Gasto',
        'Resultado', 'Venta', 'Costo', 'Impuesto', 'Administrativo', 'Financiero'
    ]

    # Cash flow statement concepts based on IFRS taxonomy
    cashflow_patterns = [
        'CashFlow', 'Cash', 'Financing', 'Investing', 'Operating', 'Flujo',
        'Efectivo', 'Financiamiento', 'Inversion', 'Operacion', 'NetIncrease',
        'NetDecrease', 'ProceedsFrom', 'PaymentsTo', 'Proceed', 'Payment'
    ]

    # Special handling for IFRS taxonomy concepts
    balance_sheet_concepts = []
    income_statement_concepts = []
    cashflow_concepts = []

    # Process all concepts - use prefixed concepts for better matching
    for concept in all_concepts:
        concept_lower = concept.lower()

        # Categorize by patterns
        if any(p.lower() in concept_lower for p in balance_sheet_patterns):
            balance_sheet_concepts.append(concept)

        if any(p.lower() in concept_lower for p in income_statement_patterns):
            income_statement_concepts.append(concept)

        if any(p.lower() in concept_lower for p in cashflow_patterns):
            cashflow_concepts.append(concept)

        # Special handling for IFRS taxonomy
        if ifrs_prefix and concept.startswith(f"{ifrs_prefix}:"):
            # Common IFRS balance sheet elements
            if any(x in concept for x in ['Asset', 'Liability', 'Equity', 'Balance']):
                balance_sheet_concepts.append(concept)

            # Common IFRS income statement elements
            elif any(x in concept for x in ['Revenue', 'Income', 'Expense', 'Profit', 'Loss']):
                income_statement_concepts.append(concept)

            # Common IFRS cash flow elements
            elif any(x in concept for x in ['CashFlow', 'Cash', 'Financing', 'Investing', 'Operating']):
                cashflow_concepts.append(concept)

    if verbose:
        print(f"\nCategorized concepts:")
        print(f"- Balance Sheet: {len(balance_sheet_concepts)} concepts")
        print(f"- Income Statement: {len(income_statement_concepts)} concepts")
        print(f"- Cash Flow: {len(cashflow_concepts)} concepts")

    # No concepts? Use all concepts as a fallback
    if len(balance_sheet_concepts) < 5 or len(income_statement_concepts) < 5 or len(cashflow_concepts) < 5:
        if verbose:
            print("\nWarning: Few concepts were categorized. Using all concepts in each statement type.")
        # Make unique sets
        all_concepts_set = set(all_concepts)
        return {
            'balance_sheet': list(all_concepts_set),
            'income_statement': list(all_concepts_set),
            'cashflow': list(all_concepts_set)
        }

    return {
        'balance_sheet': balance_sheet_concepts,
        'income_statement': income_statement_concepts,
        'cashflow': cashflow_concepts
    }


def identify_contexts(df, verbose=False):
    """
    Identify the context IDs for different statement periods.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        verbose (bool): Whether to print detailed identification

    Returns:
        dict: Dictionary mapping context types to context IDs
    """
    context_types = {}

    # Get all unique context IDs
    contexts = df['context_id'].unique()

    if verbose:
        print(f"\nFound {len(contexts)} unique context IDs in the data")

    # Count occurrences of each context ID
    context_counts = df['context_id'].value_counts()
    if verbose:
        print("\nMost common context IDs:")
        for context, count in context_counts.head(10).items():
            print(f"- {context}: {count} facts")

    # Look for specific patterns in context IDs
    period_patterns = {
        'current_period': ['cierre', 'actual', 'corriente', 'current', 'present'],
        'previous_period': ['anterior', 'previo', 'previous', 'prior'],
        'current_year_accumulated': ['acumulado', 'ytd', 'accumulated'],
        'previous_year_accumulated': ['acumulado.*anterior', 'ytd.*prev']
    }

    # Try to identify contexts based on patterns
    for period_type, patterns in period_patterns.items():
        for pattern in patterns:
            matching_contexts = [c for c in contexts
                                 if re.search(pattern, c, re.IGNORECASE)]
            if matching_contexts:
                # Use the one with the most facts
                best_match = sorted(
                    matching_contexts,
                    key=lambda c: context_counts.get(c, 0),
                    reverse=True
                )[0]
                context_types[period_type] = best_match
                if verbose:
                    print(f"Identified {period_type}: {best_match} ({context_counts.get(best_match, 0)} facts)")
                break

    # If we couldn't identify specific context types, use the most common contexts
    if len(context_types) < 2:
        if verbose:
            print("\nWarning: Could not identify enough context types by patterns. Using most common contexts.")
        most_common = context_counts.head(4)
        if len(most_common) >= 1 and 'current_period' not in context_types:
            context_types['current_period'] = most_common.index[0]
        if len(most_common) >= 2 and 'previous_period' not in context_types:
            context_types['previous_period'] = most_common.index[1]
        if len(most_common) >= 3 and 'current_year_accumulated' not in context_types:
            context_types['current_year_accumulated'] = most_common.index[2]
        if len(most_common) >= 4 and 'previous_year_accumulated' not in context_types:
            context_types['previous_year_accumulated'] = most_common.index[3]

    if verbose:
        print("\nFinal context types:")
        for context_type, context_id in context_types.items():
            print(f"- {context_type}: {context_id}")

    return context_types


def get_statement_data(df, concepts, context_id, verbose=False):
    """
    Extract data for a specific statement type and context period.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
        concepts (list): List of concept names to include
        context_id (str): Context ID to filter by
        verbose (bool): Whether to print detailed extraction

    Returns:
        pandas.DataFrame: Filtered DataFrame with statement data
    """
    if context_id is None:
        if verbose:
            print(f"Warning: No context ID provided for statement data extraction")
        return pd.DataFrame()  # Return empty DataFrame

    # Use prefixed_concept for filtering
    filtered_data = df[(df['prefixed_concept'].isin(concepts)) & (df['context_id'] == context_id)]

    if verbose:
        print(f"Found {len(filtered_data)} facts for context ID '{context_id}'")

    # Convert values to float, handling scientific notation
    filtered_data = filtered_data.copy()

    # If numeric_value column doesn't exist, create it
    if 'numeric_value' not in filtered_data.columns:
        filtered_data['numeric_value'] = pd.to_numeric(filtered_data['value'], errors='coerce')

    # Print a few examples of the data
    if verbose and not filtered_data.empty:
        print("Sample data:")
        sample = filtered_data.head(3)
        for _, row in sample.iterrows():
            print(f"  {row['prefixed_concept']}: {row['unit']} {row['numeric_value']:,.2f}")

    return filtered_data


def create_pivot_view(df):
    """
    Create a pivot table view of the data for easier analysis.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts

    Returns:
        pandas.DataFrame: Pivot table
    """
    # Ensure numeric values are properly converted
    df_copy = df.copy()
    if 'numeric_value' not in df_copy.columns:
        df_copy['numeric_value'] = pd.to_numeric(df_copy['value'], errors='coerce')

    # Create a pivot table with concepts as rows and contexts as columns
    pivot = df_copy.pivot_table(
        index='prefixed_concept',
        columns='context_id',
        values='numeric_value',
        aggfunc='first'  # Take the first value if there are duplicates
    )

    return pivot