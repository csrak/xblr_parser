"""
Helper functions for the XBRL parser.
"""

import os
import pandas as pd


def save_to_csv(df, output_path="financial_data.csv"):
    """
    Save DataFrame to CSV file.

    Args:
        df (pandas.DataFrame): DataFrame to save
        output_path (str): Path to save the CSV file

    Returns:
        str: Path to the saved CSV file
    """
    df.to_csv(output_path, index=False)
    return output_path


def create_simplified_excel(df, output_path="financial_data_simplified.xlsx"):
    """
    Create simplified Excel file with raw data and pivot table.

    Args:
        df (pandas.DataFrame): DataFrame to save
        output_path (str): Path to save the Excel file

    Returns:
        str: Path to the saved Excel file
    """
    # Create a copy with just the essential columns
    simplified_df = df[['prefixed_concept', 'value', 'unit', 'context_id']].copy()
    simplified_df['value'] = pd.to_numeric(simplified_df['value'], errors='coerce')

    # Create a pivot table for easier analysis
    pivot_df = simplified_df.pivot_table(
        index='prefixed_concept',
        columns='context_id',
        values='value',
        aggfunc='first'
    )

    # Save to Excel
    with pd.ExcelWriter(output_path) as writer:
        simplified_df.to_excel(writer, sheet_name='Raw Data')
        pivot_df.to_excel(writer, sheet_name='Pivot Table')

    return output_path


def print_data_summary(df):
    """
    Print summary information about the XBRL data.

    Args:
        df (pandas.DataFrame): DataFrame containing XBRL facts
    """
    print("\nData Summary:")
    print(f"- Total facts: {len(df)}")
    print(f"- Unique concepts: {df['concept'].nunique()}")
    print(f"- Unique prefixed concepts: {df['prefixed_concept'].nunique()}")
    print(f"- Unique contexts: {df['context_id'].nunique()}")

    # Handle None values in units
    units = [str(u) for u in df['unit'].unique() if u is not None]
    print(f"- Units: {', '.join(units)}")

    # Check for null units
    null_units_count = df['unit'].isna().sum()
    if null_units_count > 0:
        print(f"  (Note: {null_units_count} facts have no unit specified)")

    # Display the most common concepts
    print("\nMost common concepts:")
    for concept, count in df['prefixed_concept'].value_counts().head(10).items():
        print(f"- {concept}: {count} occurrences")