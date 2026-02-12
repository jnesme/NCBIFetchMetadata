#!/usr/bin/env python3

"""
Script: fetch_biosample_metadata.py
Description: Fetch BioSample metadata from Assembly or nucleotide accession
             numbers and output as a clean TSV file with proper handling of commas
Usage: python fetch_biosample_metadata.py <input_file> <output_file> [--db assembly|nucleotide] [--email your@email.com]
Example: python fetch_biosample_metadata.py AssemblyAcNu.txt BioSampleMetadata.tsv
         python fetch_biosample_metadata.py nucleotide_ids.txt output.tsv --db nucleotide
"""

import sys
import csv
import time
import argparse
from collections import defaultdict

try:
    from Bio import Entrez
except ImportError:
    print("Error: Biopython not installed. Install with: pip install biopython")
    sys.exit(1)


# Known BioSample attribute names (extend as needed)
KNOWN_ATTRIBUTES = {
    'strain', 'collection_date', 'depth', 'env_broad_scale', 
    'env_local_scale', 'env_medium', 'geo_loc_name', 'isol_growth_condt',
    'lat_lon', 'num_replicons', 'ref_biomaterial', 'type-material',
    'isolation_source', 'collected_by', 'host', 'tissue', 'age',
    'sex', 'dev_stage', 'biomaterial_provider', 'culture_collection',
    'specimen_voucher', 'cultivar', 'ecotype', 'isolate', 'sub_strain',
    'cell_line', 'cell_type', 'serovar', 'serotype', 'pathovar',
    'genotype', 'phenotype', 'note', 'temp', 'altitude', 'sample_type',
    'BioSampleModel', 'organism'
}


def fetch_biosample_record(biosample_id, accession_label):
    """
    Fetch and parse a BioSample record given its NCBI ID.

    Args:
        biosample_id: NCBI internal BioSample ID
        accession_label: Original accession string (for log messages)

    Returns:
        Dictionary of BioSample attributes or None if failed
    """
    handle = Entrez.efetch(db="biosample", id=biosample_id, retmode="xml")
    biosample_records = Entrez.read(handle)
    handle.close()

    if not biosample_records:
        print(f"  WARNING: Empty BioSample record for {accession_label}")
        return None

    biosample_record = biosample_records[0]
    attributes = {}

    if 'Accession' in biosample_record:
        attributes['biosample_accession'] = biosample_record['Accession']

    if 'Attributes' in biosample_record:
        for attr in biosample_record['Attributes']:
            attr_name = attr.get('attribute_name', 'unknown')
            attr_value = attr.get('content', '')
            if attr_name in KNOWN_ATTRIBUTES or attr_name == 'biosample_accession':
                attributes[attr_name] = attr_value

    return attributes


def fetch_biosample_from_assembly(assembly_acc, max_retries=3):
    """
    Fetch BioSample metadata from an Assembly accession number

    Args:
        assembly_acc: Assembly accession number (e.g., GCA_048058675.1)
        max_retries: Maximum number of retry attempts

    Returns:
        Dictionary of BioSample attributes or None if failed
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Search for assembly
            handle = Entrez.esearch(db="assembly", term=assembly_acc)
            record = Entrez.read(handle)
            handle.close()

            if not record['IdList']:
                print(f"  WARNING: No assembly found for {assembly_acc}")
                return None

            assembly_id = record['IdList'][0]

            # Link to BioSample
            handle = Entrez.elink(dbfrom="assembly", db="biosample", id=assembly_id)
            link_record = Entrez.read(handle)
            handle.close()

            # Check if link exists
            if not link_record[0]['LinkSetDb']:
                print(f"  WARNING: No BioSample linked to {assembly_acc}")
                return None

            biosample_id = link_record[0]['LinkSetDb'][0]['Link'][0]['Id']
            return fetch_biosample_record(biosample_id, assembly_acc)

        except Exception as e:
            if attempt < max_retries:
                print(f"  Attempt {attempt} failed: {e}. Retrying...")
                time.sleep(2)
            else:
                print(f"  ERROR: Failed after {max_retries} attempts: {e}")
                return None

    return None


def fetch_biosample_from_nucleotide(nuc_acc, max_retries=3):
    """
    Fetch BioSample metadata from a nucleotide accession number

    Args:
        nuc_acc: Nucleotide accession number (e.g., FJ457244.1)
        max_retries: Maximum number of retry attempts

    Returns:
        Dictionary of BioSample attributes or None if failed
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Search for nucleotide
            handle = Entrez.esearch(db="nucleotide", term=nuc_acc)
            record = Entrez.read(handle)
            handle.close()

            if not record['IdList']:
                print(f"  WARNING: No nucleotide record found for {nuc_acc}")
                return None

            nuc_id = record['IdList'][0]

            # Link to BioSample
            handle = Entrez.elink(dbfrom="nucleotide", db="biosample", id=nuc_id)
            link_record = Entrez.read(handle)
            handle.close()

            if not link_record[0]['LinkSetDb']:
                print(f"  WARNING: No BioSample linked to {nuc_acc}")
                return None

            biosample_id = link_record[0]['LinkSetDb'][0]['Link'][0]['Id']
            return fetch_biosample_record(biosample_id, nuc_acc)

        except Exception as e:
            if attempt < max_retries:
                print(f"  Attempt {attempt} failed: {e}. Retrying...")
                time.sleep(2)
            else:
                print(f"  ERROR: Failed after {max_retries} attempts: {e}")
                return None

    return None


def parse_csv_to_dict(csv_line):
    """
    Parse a CSV line with attribute,value pairs into a dictionary
    Handles commas within values
    
    Args:
        csv_line: String with format "attr1,val1,attr2,val2,..."
        
    Returns:
        Dictionary of attributes
    """
    parts = csv_line.split(',')
    sample_dict = {}
    i = 0
    
    while i < len(parts):
        if parts[i] in KNOWN_ATTRIBUTES:
            key = parts[i]
            value_parts = []
            i += 1
            
            # Collect value parts until we hit another known attribute
            while i < len(parts) and parts[i] not in KNOWN_ATTRIBUTES:
                value_parts.append(parts[i])
                i += 1
            
            # Join value parts with comma (to restore original value)
            value = ','.join(value_parts)
            sample_dict[key] = value
        else:
            i += 1
    
    return sample_dict


def write_tsv(data, output_file):
    """
    Write list of dictionaries to TSV file
    
    Args:
        data: List of dictionaries
        output_file: Output TSV filename
    """
    if not data:
        print("No data to write")
        return
    
    # Get all unique keys
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())
    
    # Sort keys for consistent column order
    sorted_keys = sorted(all_keys)
    
    # Write TSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sorted_keys, delimiter='\t',
                               extrasaction='ignore', restval='')
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\nSuccessfully wrote {len(data)} samples to {output_file}")
    print(f"Columns: {len(sorted_keys)}")


def main():
    parser = argparse.ArgumentParser(
        description='Fetch BioSample metadata from Assembly or nucleotide accessions'
    )
    parser.add_argument('input_file', help='Input file with accession numbers (one per line)')
    parser.add_argument('output_file', help='Output TSV file')
    parser.add_argument('--db', choices=['assembly', 'nucleotide'], default='assembly',
                       help='NCBI database to search (default: assembly)')
    parser.add_argument('--email', default='user@example.com',
                       help='Email for NCBI (required by NCBI policy)')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='Delay between requests in seconds (default: 0.5)')
    
    args = parser.parse_args()
    
    # Set email for NCBI
    Entrez.email = args.email
    
    db_label = args.db.capitalize()
    print("=" * 80)
    print(f"Fetching BioSample metadata from {db_label} accessions")
    print("=" * 80)
    print(f"Input file: {args.input_file}")
    print(f"Output file: {args.output_file}")
    print(f"Database: {args.db}")
    print(f"Email: {args.email}")
    print()
    
    # Read accessions
    try:
        with open(args.input_file, 'r') as f:
            accessions = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)
    
    print(f"Total accessions to process: {len(accessions)}\n")
    
    # Choose fetch function based on database
    if args.db == 'nucleotide':
        fetch_fn = fetch_biosample_from_nucleotide
        accession_col = 'nucleotide_accession'
    else:
        fetch_fn = fetch_biosample_from_assembly
        accession_col = 'assembly_accession'

    # Fetch metadata for each accession
    all_data = []
    successful = 0
    failed = 0

    for i, accession in enumerate(accessions, 1):
        print(f"[{i}/{len(accessions)}] Processing: {accession}")

        metadata = fetch_fn(accession)

        if metadata:
            metadata[accession_col] = accession
            all_data.append(metadata)
            successful += 1
        else:
            failed += 1
        
        # Rate limiting
        if i < len(accessions):  # Don't sleep after last request
            time.sleep(args.delay)
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total processed: {len(accessions)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    # Write output
    if all_data:
        write_tsv(all_data, args.output_file)
        
        # Show preview
        print("\nPreview of output:")
        with open(args.output_file, 'r') as f:
            for i, line in enumerate(f):
                if i < 3:  # Show first 3 lines
                    print(line.rstrip())
                else:
                    break
    else:
        print("\nNo data retrieved. Output file not created.")
    
    print("\nDONE!")


if __name__ == '__main__':
    main()
