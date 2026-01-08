# local-cd-search

A command-line tool for local protein domain annotation using NCBI's [Conserved Domain Database (CDD)](https://www.ncbi.nlm.nih.gov/Structure/cdd/cdd.shtml).

## Background

NCBI CD-Search is a widely used tool for functional annotation of proteins. It uses RPS-BLAST to search protein sequences against position-specific scoring matrices (PSSMs) from the CDD database. PSSMs offer higher sensitivity for detecting distant homologs than searches against individual protein sequences, while remaining substantially faster than HMM-based annotation.

While the CD-Search [web interface](https://www.ncbi.nlm.nih.gov/Structure/cdd/wrpsb.cgi) is convenient for small queries, it is not well suited for large-scale annotation. `local-cd-search` enables local protein annotation and automates the entire workflow: downloading PSSM databases from CDD, running RPS-BLAST, post-processing results with [`rpsbproc`](https://ftp.ncbi.nlm.nih.gov/pub/mmdb/cdd/rpsbproc/README) to filter hits using CDD's curated bit-score thresholds.

## Installation

The easiest way to install `local-cd-search` is with [Pixi](https://pixi.sh/), which will manage dependencies automatically and make `local-cd-search` available for execution from anywhere.

```sh
pixi global install -c conda-forge -c bioconda local-cd-search
```

Alternatively, you can install it from PyPI. In this case, `rpsblast` and `rpsbproc` must be installed separately. To install `local-cd-search` from PyPI using [uv](https://docs.astral.sh/uv/), run:

```sh
uv tool install local-cd-search
```

## Quick start

### Download PSSM databases

Download the full CDD database, which is a collection of six individual databases (see table below):

```sh
local-cd-search download database cdd
```

Or download individual databases. For example:

```sh
# COG database
local-cd-search download database cog

# Multiple databases
local-cd-search download database cog pfam tigr
```

The databases available for download are:

| Database | Name | Description |
| -------- | ---- | ----------- |
| `cdd` | [CDD](https://www.ncbi.nlm.nih.gov/cdd) | Collection of PSSMs derived from multiple sources (all databases listed below except KOG) |
| `cdd_ncbi` | [NCBI-curated domains](https://www.ncbi.nlm.nih.gov/Structure/cdd/cdd_help.shtml#NCBI_curated_domains) | Domain models that leverage 3D structural data to define precise boundaries |
| `cog` | [COG](https://www.ncbi.nlm.nih.gov/research/cog) | Groups of orthologous Prokaryotic proteins |
| `kog` | [KOG](https://ftp.ncbi.nlm.nih.gov/pub/COG/KOG) | Groups of orthologous Eukaryotic proteins |
| `pfam` | [Pfam](https://www.ebi.ac.uk/interpro/entry/pfam/#table) | Large collection of protein families and domains from diverse taxa |
| `prk` | [PRK](https://www.ncbi.nlm.nih.gov/proteinclusters) | NCBI collection of protein clusters containing reference sequences from prokaryotic genomes |
| `smart` | [SMART](https://smart.embl.de/smart/change_mode.cgi) | Models of domains from proteins involved in signaling, extracellular, and regulatory functions |
| `tigr` | [TIGRFAM](https://www.ncbi.nlm.nih.gov/refseq/annotation_prok/tigrfams/) | Manually curated models for functional annotation of microbial proteins |

### Annotate proteins

To run annotation on a FASTA file of protein sequences (in this example, `proteins.faa`) and save results to `results.tsv`, run the following command:

```sh
local-cd-search annotate proteins.faa results.tsv database
```

The `local-cd-search` will automatically detect which databases are available and will them for annotation.

## Output

The output of `local-cd-search annotate` is a tab-separated file with hits filtered by CDD's curated bit-score thresholds. The following columns are included:

| Column | Description |
|--------|-------------|
| query | Protein identifier |
| hit_type | Specific, Non-specific, or Superfamily |
| pssm_id | CDD PSSM identifier |
| from | Start position in query |
| to | End position in query |
| evalue | E-value |
| bitscore | Bit score |
| accession | Domain accession |
| short_name | Domain short name (e.g., COG0001) |
| incomplete | Indicates if there are more than 20% missing from the N- or C- terminal ends (-, N, C, or NC) |
| superfamily_pssm_id | Superfamily PSSM identifier |

### hit_type

- **Specific**: The top-ranking RPS-BLAST hit (compared to other hits in overlapping intervals) that meets or exceeds a domain-specific E-value threshold. It represents a very high confidence that the query sequence belongs to the same protein family as the sequences used to create the domain model.
- **Non-specific**: Hits that meet or exceed the RPS-BLAST threshold for statistical significance (default E-value cutoff of 0.01).
- **Superfamily**: The domain cluster to which the specific and/or non-specific hits belong. This is a set of conserved domain models that generate overlapping annotation on the same protein sequences and are assumed to represent evolutionarily related domains.

### incomplete

Indicates if there are more than 20% missing from the N- or C- terminal compared to the original domain. Possible values are:
- **-**: No more than 20% shorter on either terminals.
- **N**: N-terminal has 20% or more missing.
- **C**: C-terminal has 20% or more missing.
- **NC**: Both terminals have 20% or more missing.

## Functional sites output

If `--sites-output` is specified, an additional tab-separated file is created with functional site annotations. The following columns are included:

| Column | Description |
|--------|-------------|
| query | Protein identifier |
| annot_type | Specific or Generic |
| title | Description of the functional site |
| coordinates | Residues and their positions (e.g., H94,Y96) |
| complete_size | Total number of residues in the site |
| mapped_size | Number of residues mapped to the query |
| source_domain | PSSM ID of the domain where the site is defined |

## Usage

### `download` subcommand

```
local-cd-search download [OPTIONS] DB_DIR DATABASE...
```

| Option | Short | Argument | Description | Default |
| ------ | ----- | -------- | ----------- | ------- |
| `--force` | | flag | Force re-download even if files are already present. | |
| `--quiet` | | flag | Suppress non-error console output. | |
| `--help` | `-h` | flag | Show help message and exit. | |

### `annotate` subcommand

```
local-cd-search annotate [OPTIONS] INPUT_FILE OUTPUT_FILE DB_DIR
```

| Option | Short | Argument | Description | Default |
| ------ | ----- | -------- | ----------- | ------- |
| `--evalue` | `-e` | `FLOAT (≥ 0)` | Maximum allowed E-value for hits. | `0.01` |
| `--ns` | | flag | Include non-specific hits in the output results table. | |
| `--sf` | | flag | Include superfamily hits in the output results table. | |
| `--threads` | | `INTEGER` | Number of threads to use for `rpsblast`. | `0` |
| `--sites-output` | `-s` | `FILE` | Path to write functional site annotations. | |
| `--data-mode` | `-m` | `std \| rep \| full` | Redundancy level of domain hit data passed to `rpsbproc`: `rep` (best model per region of the query), `std` (best model per source per region), `full` (all models meeting E-value significance). | `std` |
| `--tmp-dir` | | `DIRECTORY` | Directory to store intermediate files. If not specified, temporary files will be deleted after execution. | |
| `--quiet` | | flag | Suppress non-error console output. | |
| `--help` | `-h` | flag | Show help message and exit. | |
