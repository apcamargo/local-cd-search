# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-01-07

### Added

- Add support for functional site annotation, enabled through the `--sites-output` / `-s` option.
- Add the `incomplete` and `superfamily_pssm_id` columns to the domain annotation TSV output.

### Changed

- Switch to `tempfile` for automatic temporary directory management. Intermediate files are now deleted by default unless a persistent directory is specified with `--tmp-dir`. The `--keep-tmp` option has been removed as it is now redundant

## [0.2.0] - 2025-12-30

### Added

- Add the `ensure_pal_file` function, which sets a `.pal` file for the downloaded databases. These files set constant values for `STATS_NSEQ` and `STATS_TOTLEN` to ensure the computed E-values are identical to the ones computed by the CD-Search web service.

## [0.1.0] - 2025-12-29

### Added
- First release.
