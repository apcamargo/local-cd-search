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

### 1. Download databases

Download the full CDD reference database (recommended for comprehensive annotation):

```sh
local-cd-search download database cdd
```

Or download specific subsets:

```sh
# COG database only (for COG functional annotation)
local-cd-search download database cog

# Multiple databases
local-cd-search download database cog pfam tigr
```

Available databases:
 - `cdd`
 - `cdd_ncbi`
 - `cog`
 - `kog`
 - `pfam`
 - `prk`
 - `smart`
 - `tigr`

### 2. Annotate proteins

```sh
local-cd-search annotate proteins.faa results.tsv database
```

The tool auto-detects which databases are available and uses them for annotation.

## Output

`local-cd-search` produces a tab-separated file with hits filtered by CDD's curated bit-score thresholds:

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
| `--data-mode` | `-m` | `std \| rep \| full` | Redundancy level of domain hit data passed to `rpsbproc`: `rep` (best model per region of the query), `std` (best model per source per region), `full` (all models meeting E-value significance). | `std` |
| `--tmp-dir` | | `DIRECTORY` | Directory to store intermediate files. | `tmp` |
| `--keep-tmp` | | flag | Keep intermediate temporary files. | |
| `--quiet` | | flag | Suppress non-error console output. | |
| `--help` | `-h` | flag | Show help message and exit. | |
