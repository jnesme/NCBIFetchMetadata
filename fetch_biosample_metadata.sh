#!/bin/bash

###############################################################################
# Script: fetch_biosample_metadata.sh
# Description: Fetch BioSample metadata from Assembly or nucleotide accession
#              numbers and output as a clean TSV file with proper handling of commas
# Usage: ./fetch_biosample_metadata.sh <input_file> <output_file> [assembly|nucleotide]
# Example: ./fetch_biosample_metadata.sh AssemblyAcNu.txt BioSampleMetadata.tsv
#          ./fetch_biosample_metadata.sh nuc_ids.txt output.tsv nucleotide
###############################################################################

set -e  # Exit on error

# Check arguments
if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    echo "Usage: $0 <input_file> <output_tsv_file> [assembly|nucleotide]"
    echo "Example: $0 AssemblyAcNu.txt BioSampleMetadata.tsv"
    echo "         $0 nuc_ids.txt output.tsv nucleotide"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"
DB="${3:-assembly}"
TEMP_CSV="${OUTPUT_FILE%.tsv}_temp.csv"

# Validate db argument
if [ "$DB" != "assembly" ] && [ "$DB" != "nucleotide" ]; then
    echo "Error: Invalid database '$DB'. Must be 'assembly' or 'nucleotide'."
    exit 1
fi

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found"
    exit 1
fi

# Check if EDirect tools are installed
if ! command -v esearch &> /dev/null; then
    echo "Error: NCBI EDirect tools not found. Please install from:"
    echo "https://www.ncbi.nlm.nih.gov/books/NBK179288/"
    exit 1
fi

echo "========================================================================"
echo "Fetching BioSample metadata from ${DB} accessions"
echo "========================================================================"
echo "Input file: $INPUT_FILE"
echo "Output file: $OUTPUT_FILE"
echo "Database: $DB"
echo "Total accessions: $(wc -l < $INPUT_FILE)"
echo ""

# Remove old temp file if exists
rm -f "$TEMP_CSV"

# Counter for progress
total=$(wc -l < "$INPUT_FILE")
current=0

# Loop through assembly accessions
while read -r accession; do
    # Skip empty lines
    [ -z "$accession" ] && continue
    
    current=$((current + 1))
    echo "[$current/$total] Processing: $accession"
    
    # Retry logic (up to 3 attempts)
    for attempt in 1 2 3; do
        result=$(esearch -db "$DB" -query "$accession" 2>/dev/null |
                 elink -target biosample 2>/dev/null | 
                 efetch -format xml 2>/dev/null | 
                 xtract -pattern BioSample -element accession -block Attributes -group Attribute -element Attribute@attribute_name Attribute 2>/dev/null | 
                 tr '\t' ',' || echo "")
        
        if [ -n "$result" ]; then
            echo "$result" >> "$TEMP_CSV"
            break
        else
            if [ $attempt -lt 3 ]; then
                echo "  Attempt $attempt failed, retrying..."
                sleep 2
            else
                echo "  WARNING: Failed to fetch data for $accession after 3 attempts"
            fi
        fi
    done
    
    # Rate limiting - sleep between requests
    sleep 0.5
    
done < "$INPUT_FILE"

echo ""
echo "========================================================================"
echo "Converting to TSV format"
echo "========================================================================"

# Convert CSV to TSV using Python
python3 << 'PYTHON_SCRIPT'
import csv
import sys
from collections import defaultdict

# Known BioSample attribute names (extend as needed)
known_attributes = {
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

temp_csv = sys.argv[1]
output_tsv = sys.argv[2]

# Read and parse the CSV file
all_data = []
all_keys = set()

with open(temp_csv, 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        # Split by comma
        parts = line.split(',')
        
        sample_dict = {}
        i = 0
        
        while i < len(parts):
            if parts[i] in known_attributes:
                key = parts[i]
                value_parts = []
                i += 1
                
                # Collect value parts until we hit another known attribute
                while i < len(parts) and parts[i] not in known_attributes:
                    value_parts.append(parts[i])
                    i += 1
                
                # Join value parts with comma (to restore original value)
                value = ','.join(value_parts)
                sample_dict[key] = value
                all_keys.add(key)
            else:
                i += 1
        
        if sample_dict:
            all_data.append(sample_dict)

# Sort keys for consistent column order
sorted_keys = sorted(all_keys)

# Write to TSV
with open(output_tsv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=sorted_keys, delimiter='\t', 
                           extrasaction='ignore', restval='')
    
    # Write header
    writer.writeheader()
    
    # Write data
    for sample in all_data:
        writer.writerow(sample)

print(f"Successfully converted {len(all_data)} samples")
print(f"Found {len(sorted_keys)} unique attributes")
print(f"Output written to: {output_tsv}")

PYTHON_SCRIPT "$TEMP_CSV" "$OUTPUT_FILE"

# Clean up temp file
rm -f "$TEMP_CSV"

echo ""
echo "========================================================================"
echo "DONE!"
echo "========================================================================"
echo "Output file: $OUTPUT_FILE"
echo "Preview:"
echo ""
head -3 "$OUTPUT_FILE" | cut -f1-5

exit 0
