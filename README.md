# BioSample Metadata Fetcher

Automated scripts to fetch BioSample metadata from NCBI Assembly accession numbers and output as clean TSV files.

## Features

- Fetches BioSample metadata linked to Assembly accessions
- Automatic retry logic for failed requests
- Rate limiting to respect NCBI guidelines
- Properly handles commas in field values (e.g., geographic locations)
- Outputs clean TSV with single header row
- Progress tracking and error reporting

## Two Implementations

### 1. Bash Script (using EDirect)
**File:** `fetch_biosample_metadata.sh`

**Requirements:**
- NCBI EDirect utilities (esearch, elink, efetch, xtract)
- Python 3 (for CSV to TSV conversion)
- Bash shell

**Installation of EDirect:**
```bash
# On macOS/Linux
sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"

# Add to PATH
export PATH=${PATH}:${HOME}/edirect
```

**Usage:**
```bash
chmod +x fetch_biosample_metadata.sh
./fetch_biosample_metadata.sh AssemblyAcNu.txt BioSampleMetadata.tsv
```

**Advantages:**
- Uses official NCBI command-line tools
- Very efficient and fast
- Already working solution (your current method)

---

### 2. Python Script (using Biopython)
**File:** `fetch_biosample_metadata.py`

**Requirements:**
- Python 3.6+
- Biopython

**Installation:**
```bash
pip install biopython
```

**Usage:**
```bash
# Basic usage
python fetch_biosample_metadata.py AssemblyAcNu.txt BioSampleMetadata.tsv

# With custom email (recommended by NCBI)
python fetch_biosample_metadata.py AssemblyAcNu.txt BioSampleMetadata.tsv --email your@email.com

# Adjust delay between requests (default: 0.5 seconds)
python fetch_biosample_metadata.py AssemblyAcNu.txt BioSampleMetadata.tsv --delay 1.0
```

**Advantages:**
- More portable (works on any system with Python)
- Better error handling and reporting
- Easier to customize and extend
- Adds assembly_accession and biosample_accession to output

---

## Input Format

Create a text file with one Assembly accession per line:

**AssemblyAcNu.txt:**
```
GCA_048058675.1
GCA_048058775.1
GCA_048058575.1
GCA_048058475.1
```

---

## Output Format

Clean TSV file with standardized columns:

**BioSampleMetadata.tsv:**
```
assembly_accession	biosample_accession	strain	collection_date	depth	geo_loc_name	...
GCA_048058675.1	SAMN39255711	A35a-5a	2009	10 cm	Denmark: Roskilde Fjord, Jyllinge harbor	...
GCA_048058775.1	SAMN39255712	A36a-5a	2009	10 cm	Denmark: Roskilde Fjord, Jyllinge harbor	...
```

---

## Supported BioSample Attributes

The scripts recognize and properly parse these common attributes:

**Core Attributes:**
- strain
- collection_date
- depth
- env_broad_scale, env_local_scale, env_medium
- geo_loc_name
- isol_growth_condt
- lat_lon
- num_replicons
- ref_biomaterial
- type-material

**Extended Attributes:**
- isolation_source, collected_by
- host, tissue, age, sex, dev_stage
- biomaterial_provider, culture_collection
- specimen_voucher, cultivar, ecotype, isolate, sub_strain
- cell_line, cell_type
- serovar, serotype, pathovar
- genotype, phenotype
- note, temp, altitude, sample_type
- organism

To add more attributes, edit the `KNOWN_ATTRIBUTES` set in either script.

---

## Rate Limiting

Both scripts implement rate limiting to comply with NCBI's guidelines:

- **Without API key:** 3 requests/second (scripts default to 0.5s delay = 2 req/s)
- **With API key:** 10 requests/second

For large datasets, consider getting an NCBI API key:
1. Create NCBI account: https://www.ncbi.nlm.nih.gov/account/
2. Get API key from account settings
3. Set environment variable: `export NCBI_API_KEY=your_key_here`

---

## Error Handling

Both scripts include:

1. **Retry logic:** Up to 3 attempts per accession
2. **Progress tracking:** Shows current progress during execution
3. **Error reporting:** Logs failed accessions
4. **Graceful degradation:** Continues processing even if some accessions fail

---

## Troubleshooting

### Bash Script Issues:

**"command not found: esearch"**
- Install NCBI EDirect utilities (see Installation section)

**"500 Internal Server Error"**
- NCBI server issue - the retry logic will handle this
- If persistent, increase sleep delay in the script

**"EMPTY RESULT"**
- Assembly accession may not have linked BioSample
- Check accession number is correct

### Python Script Issues:

**"ModuleNotFoundError: No module named 'Bio'"**
```bash
pip install biopython
```

**"HTTP Error 429: Too Many Requests"**
- Increase delay: `--delay 1.0`
- Get NCBI API key (see Rate Limiting section)

**Network timeout errors**
- Check internet connection
- Retry with fewer concurrent requests

---

## Examples

### Example 1: Basic Usage
```bash
# Create input file
cat > assemblies.txt << EOF
GCA_048058675.1
GCA_048058775.1
GCA_048058575.1
EOF

# Run script
./fetch_biosample_metadata.sh assemblies.txt output.tsv
```

### Example 2: Python with Custom Settings
```bash
python fetch_biosample_metadata.py \
    assemblies.txt \
    output.tsv \
    --email researcher@university.edu \
    --delay 0.4
```

### Example 3: Process Large Dataset
```bash
# Split large file into chunks of 100
split -l 100 large_assemblies.txt chunk_

# Process each chunk
for chunk in chunk_*; do
    python fetch_biosample_metadata.py $chunk output_${chunk}.tsv
    sleep 60  # Pause between chunks
done

# Combine results (skip headers from all but first file)
head -1 output_chunk_aa.tsv > final_output.tsv
tail -n +2 -q output_chunk_*.tsv >> final_output.tsv
```

---

## Performance

Approximate processing times:

| Accessions | Time (0.5s delay) | Time (0.4s delay) |
|------------|-------------------|-------------------|
| 10         | ~10 seconds       | ~8 seconds        |
| 100        | ~80 seconds       | ~65 seconds       |
| 1000       | ~13 minutes       | ~11 minutes       |

*Times include retry attempts for failed requests*

---

## Citation

If you use these scripts in your research, please cite:

- NCBI Resource Coordinators. Database resources of the National Center for Biotechnology Information. Nucleic Acids Res. 2016.
- NCBI EDirect: https://www.ncbi.nlm.nih.gov/books/NBK179288/
- Biopython: Cock et al. Bioinformatics 2009.

---

## License

These scripts are provided as-is for research purposes. Feel free to modify and distribute.

---

## Contact

For issues or questions:
- NCBI EDirect documentation: https://www.ncbi.nlm.nih.gov/books/NBK179288/
- Biopython documentation: https://biopython.org/
- NCBI E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25500/
