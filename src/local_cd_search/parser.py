import csv
from contextlib import ExitStack
from pathlib import Path
from typing import Optional

from local_cd_search.utils import PathLike, ensure_dir


def parse_rpsbproc(
    input_file: PathLike,
    output_file: PathLike,
    sites_output_file: Optional[PathLike] = None,
    include_ns: bool = False,
    include_sf: bool = False,
) -> None:
    """
    Parse rpsbproc-formatted output and write a simplified tab-delimited table.

    This reads the rpsbproc/domains-style output and produces a TSV with the
    following columns:

        query, hit_type, pssm_id, from, to, evalue, bitscore, accession,
        short_name, incomplete, superfamily_pssm_id

    If `sites_output_file` is provided, it also parses the SITES block and produces
    a TSV with the following columns:

        query, annot_type, title, coordinates, complete_size, mapped_size, source_domain

    Parameters
    ----------
    input_file : str | pathlib.Path
        Path to the rpsbproc input file.
    output_file : str | pathlib.Path
        Path to write the parsed tab-delimited output.
    sites_output_file : str | pathlib.Path, optional
        Path to write the parsed functional sites table.
    include_ns : bool
        Include non-specific hits when True.
    include_sf : bool
        Include superfamily hits when True.

    Notes
    -----
    The function ensures the parent directory for output files exists and
    writes the output in UTF-8.
    """
    headers = [
        "query",
        "hit_type",
        "pssm_id",
        "from",
        "to",
        "evalue",
        "bitscore",
        "accession",
        "short_name",
        "incomplete",
        "superfamily_pssm_id",
    ]

    site_headers = [
        "query",
        "annot_type",
        "title",
        "coordinates",
        "complete_size",
        "mapped_size",
        "source_domain",
    ]

    allowed_types = {"Specific"}
    allowed_site_types = {"Specific"}

    if include_ns:
        allowed_types.add("Non-specific")
    if include_sf:
        allowed_types.add("Superfamily")

    # If including non-specific or superfamily domains, include Generic sites
    if include_ns or include_sf:
        allowed_site_types.add("Generic")

    # Ensure output directory exists
    ensure_dir(Path(output_file).parent)
    if sites_output_file:
        ensure_dir(Path(sites_output_file).parent)

    # Read input and write output using explicit UTF-8 encoding
    with ExitStack() as stack:
        inf = stack.enter_context(open(input_file, encoding="utf-8"))
        outf = stack.enter_context(open(output_file, "w", newline="", encoding="utf-8"))

        writer = csv.writer(outf, delimiter="\t")
        writer.writerow(headers)

        sites_writer = None
        if sites_output_file:
            sites_outf = stack.enter_context(
                open(sites_output_file, "w", newline="", encoding="utf-8")
            )
            sites_writer = csv.writer(sites_outf, delimiter="\t")
            sites_writer.writerow(site_headers)

        current_query = None
        in_domain_block = False
        in_sites_block = False

        for line in inf:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("QUERY"):
                parts = line.split("\t")
                # Defensive: the original format stores query metadata; try to extract the query name if present
                if len(parts) >= 5:
                    current_query = parts[4].strip().split()[0]
                else:
                    # Fallback: keep the whole line as query identifier if fields are unexpected
                    current_query = parts[-1].strip() if parts else None
                in_domain_block = False
                in_sites_block = False
                continue

            if line.startswith("DOMAINS"):
                in_domain_block = True
                continue
            if line.startswith("ENDDOMAINS"):
                in_domain_block = False
                continue

            if line.startswith("SITES"):
                in_sites_block = True
                continue
            if line.startswith("ENDSITES"):
                in_sites_block = False
                continue

            if line.startswith("ENDQUERY"):
                in_domain_block = False
                in_sites_block = False
                continue

            if in_domain_block:
                data = line.split("\t")
                # Ensure there are enough columns before indexing
                if len(data) >= 12:
                    hit_type = data[2].strip()
                    if hit_type in allowed_types:
                        # Compose row matching the headers above
                        row = [
                            current_query,
                            hit_type,
                            data[3].strip(),
                            data[4].strip(),
                            data[5].strip(),
                            data[6].strip(),
                            data[7].strip(),
                            data[8].strip(),
                            data[9].strip(),
                            data[10].strip(),
                            data[11].strip(),
                        ]
                        writer.writerow(row)

            if in_sites_block and sites_writer:
                data = line.split("\t")
                # Ensure enough columns. 8 columns expected based on analysis
                if len(data) >= 8:
                    annot_type = data[2].strip()
                    if annot_type in allowed_site_types:
                        # query, annot_type, title, coordinates, complete_size, mapped_size, source_domain
                        # Columns in file: 0:ordinal, 1:query, 2:type, 3:title, 4:coords, 5:complete, 6:mapped, 7:source
                        row = [
                            current_query,
                            annot_type,
                            data[3].strip(),
                            data[4].strip(),
                            data[5].strip(),
                            data[6].strip(),
                            data[7].strip(),
                        ]
                        sites_writer.writerow(row)
