"""
Command-line interface for the XBRL parser.
"""

import os
import argparse
import pandas as pd

from .parser import XBRLParser
from .analyzer import convert_to_dataframe
from .generator import generate_financial_statements, create_excel_report
from .utils import save_to_csv, create_simplified_excel, print_data_summary


def main():
    """Main CLI function for the XBRL parser."""
    parser = argparse.ArgumentParser(description='Parse XBRL files and generate financial statements')
    parser.add_argument('directory', help='Directory containing XBRL files')
    parser.add_argument('--output', '-o', default='.', help='Output directory for reports')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--format', '-f', choices=['txt', 'excel', 'csv', 'all'], default='all',
                        help='Output format (default: all)')

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)

    # Initialize parser
    xbrl_parser = XBRLParser(verbose=args.verbose)

    # Parse XBRL files
    facts = xbrl_parser.parse_directory(args.directory)

    if not facts:
        print("No facts were extracted from XBRL files.")
        return 1

    # Convert to DataFrame
    df = convert_to_dataframe(facts)

    # Print data summary
    if args.verbose:
        print_data_summary(df)

    # Generate and save outputs based on format
    if args.format in ['txt', 'all']:
        # Generate text report
        report = generate_financial_statements(df, args.verbose)
        report_file = os.path.join(args.output, "financial_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Text report saved to: {report_file}")

    if args.format in ['excel', 'all']:
        # Generate Excel report
        excel_file = os.path.join(args.output, "financial_statements.xlsx")
        create_excel_report(df, excel_file, args.verbose)
        print(f"Excel report saved to: {excel_file}")

        # Create simplified Excel
        simplified_file = os.path.join(args.output, "financial_data_simplified.xlsx")
        create_simplified_excel(df, simplified_file)
        print(f"Simplified data saved to: {simplified_file}")

    if args.format in ['csv', 'all']:
        # Save raw data to CSV
        csv_file = os.path.join(args.output, "financial_data.csv")
        save_to_csv(df, csv_file)
        print(f"CSV data saved to: {csv_file}")

    print("\nProcessing complete!")
    return 0


if __name__ == "__main__":
    exit(main())