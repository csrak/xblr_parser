"""
Core XBRL parsing functionality.
"""

import os
import glob
from lxml import etree


def find_xbrl_files(directory):
    """
    Find XBRL instance files in the specified directory.

    Args:
        directory (str): Path to the directory to search

    Returns:
        list: Paths to XBRL files
    """
    all_files = []
    all_files.extend(glob.glob(os.path.join(directory, "*.xbrl")))
    all_files.extend(glob.glob(os.path.join(directory, "*[0-9].xml")))

    # Filter out known non-instance files
    return [f for f in all_files if not any(x in os.path.basename(f).lower()
                                            for x in ["_lab", "label", "dim_", "def"])]


def get_local_name(tag):
    """
    Extract local name from a namespaced tag, handling different tag types safely.

    Args:
        tag: XML element tag (string or cython object)

    Returns:
        str or None: Local name of the tag, or None if it can't be determined
    """
    # Check if tag is a string
    if isinstance(tag, str):
        return tag.split('}', 1)[1] if '}' in tag else tag
    # Handle case where tag is a function or other non-string type
    else:
        # Convert to string to see what type it is
        tag_str = str(tag)
        if '<cyfunction' in tag_str or '<cython_function_or_method' in tag_str:
            # This is likely a comment, PI or other special node
            return None
        return tag_str


def parse_xbrl_file(file_path, verbose=False):
    """
    Parse an XBRL file and extract facts.

    Args:
        file_path (str): Path to the XBRL file
        verbose (bool): Whether to print detailed information during parsing

    Returns:
        list: Extracted facts
    """
    try:
        # Parse the XML file with a permissive parser
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        tree = etree.parse(file_path, parser)
        root = tree.getroot()

        if verbose:
            print(f"Root element: {root.tag}")
            print(f"Namespaces: {root.nsmap}")

        # Extract contexts using element tree iteration
        contexts = {}

        # Find all context elements
        for elem in root.iter():
            # Skip elements with non-string tags
            if not isinstance(elem.tag, str):
                continue

            # Get local name safely
            local_name = get_local_name(elem.tag)
            if local_name != 'context':
                continue

            context_id = elem.get('id')
            if not context_id:
                continue

            # Initialize context data
            context_data = {
                'period_type': None,
                'dimensions': {}
            }

            # Find period element
            period = None
            for child in elem:
                if not isinstance(child.tag, str):
                    continue
                child_name = get_local_name(child.tag)
                if child_name == 'period':
                    period = child
                    break

            if period is not None:
                # Check for instant
                instant = None
                for p_child in period:
                    if not isinstance(p_child.tag, str):
                        continue
                    p_child_name = get_local_name(p_child.tag)
                    if p_child_name == 'instant':
                        instant = p_child
                        break

                if instant is not None:
                    context_data['period_type'] = 'instant'
                    context_data['instant'] = instant.text.strip() if instant.text else None
                else:
                    # Look for start/end dates
                    start_date = None
                    end_date = None

                    for p_child in period:
                        if not isinstance(p_child.tag, str):
                            continue
                        p_child_name = get_local_name(p_child.tag)
                        if p_child_name == 'startDate':
                            start_date = p_child
                        elif p_child_name == 'endDate':
                            end_date = p_child

                    context_data['period_type'] = 'duration'
                    context_data[
                        'start_date'] = start_date.text.strip() if start_date is not None and start_date.text else None
                    context_data['end_date'] = end_date.text.strip() if end_date is not None and end_date.text else None

            # Find segment for dimensions
            segment = None
            for child in elem:
                if not isinstance(child.tag, str):
                    continue
                child_name = get_local_name(child.tag)
                if child_name == 'entity':
                    for e_child in child:
                        if not isinstance(e_child.tag, str):
                            continue
                        e_child_name = get_local_name(e_child.tag)
                        if e_child_name == 'segment':
                            segment = e_child
                            break

            if segment is not None:
                for dim in segment:
                    if not isinstance(dim.tag, str):
                        continue
                    dim_name = get_local_name(dim.tag)
                    if 'explicitMember' in dim_name:
                        dimension = dim.get('dimension')
                        if dimension:
                            dimension_name = get_local_name(dimension)
                            member_value = dim.text.strip() if dim.text else None
                            if member_value:
                                context_data['dimensions'][dimension_name] = member_value

            # Store context
            contexts[context_id] = context_data

        if verbose:
            print(f"Extracted {len(contexts)} contexts")

        # Extract facts
        facts = []

        # Skip these names as they're structural elements
        skip_names = ['context', 'unit', 'schemaRef', 'roleRef', 'arcroleRef']

        # Iterate through all elements
        for elem in root.iter():
            # Skip elements with non-string tags
            if not isinstance(elem.tag, str):
                continue

            # Check if it has a contextRef attribute
            context_ref = elem.get('contextRef')
            if not context_ref or context_ref not in contexts:
                continue

            # Get local name and namespace prefix
            tag = elem.tag
            if '}' in tag:
                ns, local_name = tag.split('}', 1)
                ns = ns.strip('{')
                # Try to find the prefix for this namespace
                prefix = None
                for p, u in root.nsmap.items():
                    if u == ns:
                        prefix = p
                        break

                # Store the prefixed name for better identification
                if prefix:
                    prefixed_name = f"{prefix}:{local_name}"
                else:
                    prefixed_name = local_name
            else:
                local_name = tag
                prefixed_name = local_name

            # Skip structural elements
            if local_name in skip_names:
                continue

            # Get value
            value = elem.text
            if value is not None:
                value = value.strip()
            else:
                # Skip elements with no value
                continue

            # Get unit
            unit_ref = elem.get('unitRef')

            # Create fact record
            fact = {
                'concept': local_name,
                'prefixed_concept': prefixed_name,
                'value': value,
                'unit': unit_ref,
                'context_id': context_ref,
                'period_type': contexts[context_ref]['period_type'],
            }

            # Add period information based on type
            if contexts[context_ref]['period_type'] == 'instant':
                fact['date'] = contexts[context_ref].get('instant')
            else:
                fact['start_date'] = contexts[context_ref].get('start_date')
                fact['end_date'] = contexts[context_ref].get('end_date')

            # Add dimensions
            fact['dimensions'] = contexts[context_ref].get('dimensions', {})

            facts.append(fact)

        if verbose:
            print(f"Extracted {len(facts)} facts")
        return facts

    except Exception as e:
        if verbose:
            print(f"Error parsing {file_path}: {str(e)}")
            import traceback
            traceback.print_exc()
        return []


class XBRLParser:
    """
    A class for parsing XBRL documents and extracting financial data.
    """

    def __init__(self, verbose=False):
        """
        Initialize the XBRL parser.

        Args:
            verbose (bool): Whether to print detailed information during parsing
        """
        self.verbose = verbose

    def find_files(self, directory):
        """
        Find XBRL files in the specified directory.

        Args:
            directory (str): Path to the directory to search

        Returns:
            list: Paths to XBRL files
        """
        return find_xbrl_files(directory)

    def parse_file(self, file_path):
        """
        Parse an XBRL file and extract facts.

        Args:
            file_path (str): Path to the XBRL file

        Returns:
            list: Extracted facts
        """
        return parse_xbrl_file(file_path, self.verbose)

    def parse_directory(self, directory):
        """
        Parse all XBRL files in a directory and combine their facts.

        Args:
            directory (str): Path to the directory to search

        Returns:
            list: Combined facts from all XBRL files
        """
        xbrl_files = self.find_files(directory)

        if not xbrl_files:
            if self.verbose:
                print("No XBRL files found.")
            return []

        if self.verbose:
            print(f"Found {len(xbrl_files)} XBRL files:")
            for file in xbrl_files:
                print(f"  - {os.path.basename(file)}")

        # Process each file
        all_facts = []
        for file_path in xbrl_files:
            if self.verbose:
                print(f"\nProcessing: {os.path.basename(file_path)}")
            facts = self.parse_file(file_path)
            if self.verbose:
                print(f"  - Extracted {len(facts)} facts")
            all_facts.extend(facts)

        if self.verbose and all_facts:
            print(f"\nTotal facts extracted: {len(all_facts)}")

        return all_facts