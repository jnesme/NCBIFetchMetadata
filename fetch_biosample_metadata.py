#!/usr/bin/env python3

"""
Script: fetch_biosample_metadata.py
Description: Fetch BioSample metadata from Assembly accession numbers
             and output as a clean TSV file with proper handling of commas
Usage: python fetch_biosample_metadata.py <input_file> <output_file> [--email your@email.com]
Example: python fetch_biosample_metadata.py AssemblyAcNu.txt BioSampleMetadata.tsv
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
            
            # Fetch BioSample data
            handle = Entrez.efetch(db="biosample", id=biosample_id, retmode="xml")
            biosample_records = Entrez.read(handle)
            handle.close()
            
            if not biosample_records:
                print(f"  WARNING: Empty BioSample record for {assembly_acc}")
                return None
            
            # Parse attributes
            biosample_record = biosample_records[0]
            attributes = {}
            
            # Add BioSample accession
            if 'Accession' in biosample_record:
                attributes['biosample_accession'] = biosample_record['Accession']
            
            # Parse all attributes
            if 'Attributes' in biosample_record:
                for attr in biosample_record['Attributes']:
                    attr_name = attr.get('attribute_name', 'unknown')
                    attr_value = attr.get('content', '')
                    if attr_name in KNOWN_ATTRIBUTES or attr_name == 'biosample_accession':
                        attributes[attr_name] = attr_value
            
            return attributes
            
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
        description='Fetch BioSample metadata from Assembly accessions'
    )
    parser.add_argument('input_file', help='Input file with Assembly accession numbers (one per line)')
    parser.add_argument('output_file', help='Output TSV file')
    parser.add_argument('--email', default='user@example.com', 
                       help='Email for NCBI (required by NCBI policy)')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='Delay between requests in seconds (default: 0.5)')
    
    args = parser.parse_args()
    
    # Set email for NCBI
    Entrez.email = args.email
    
    print("=" * 80)
    print("Fetching BioSample metadata from Assembly accessions")
    print("=" * 80)
    print(f"Input file: {args.input_file}")
    print(f"Output file: {args.output_file}")
    print(f"Email: {args.email}")
    print()
    
    # Read assembly accessions
    try:
        with open(args.input_file, 'r') as f:
            accessions = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)
    
    print(f"Total accessions to process: {len(accessions)}\n")
    
    # Fetch metadata for each assembly
    all_data = []
    successful = 0
    failed = 0
    
    for i, accession in enumerate(accessions, 1):
        print(f"[{i}/{len(accessions)}] Processing: {accession}")
        
        metadata = fetch_biosample_from_assembly(accession)
        
        if metadata:
            # Add assembly accession to the record
            metadata['assembly_accession'] = accession
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
