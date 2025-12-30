import csv
from pathlib import Path

from local_cd_search.utils import PathLike, ensure_dir


def parse_rpsbproc(
    input_file: PathLike,
    output_file: PathLike,
    include_ns: bool = False,
    include_sf: bool = False,
) -> None:
    """
    Parse rpsbproc-formatted output and write a simplified tab-delimited table.

    This reads the rpsbproc/domains-style output and produces a TSV with the
    following columns:

        query, hit_type, pssm_id, from, to, evalue, bitscore, accession, short_name

    Parameters
    ----------
    input_file : str | pathlib.Path
        Path to the rpsbproc input file.
    output_file : str | pathlib.Path
        Path to write the parsed tab-delimited output.
    include_ns : bool
        Include non-specific hits when True.
    include_sf : bool
        Include superfamily hits when True.

    Notes
    -----
    The function ensures the parent directory for `output_file` exists and
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
    ]

    allowed_types = {"Specific"}
    if include_ns:
        allowed_types.add("Non-specific")
    if include_sf:
        allowed_types.add("Superfamily")

    # Ensure output directory exists
    ensure_dir(Path(output_file).parent)

    # Read input and write output using explicit UTF-8 encoding
    with (
        open(input_file, encoding="utf-8") as inf,
        open(output_file, "w", newline="", encoding="utf-8") as outf,
    ):
        writer = csv.writer(outf, delimiter="\t")
        writer.writerow(headers)

        current_query = None
        in_domain_block = False

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
                continue

            if line.startswith("DOMAINS"):
                in_domain_block = True
                continue
            if line.startswith("ENDDOMAINS") or line.startswith("ENDQUERY"):
                in_domain_block = False
                continue

            if in_domain_block:
                data = line.split("\t")
                # Ensure there are enough columns before indexing
                if len(data) >= 10:
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
                        ]
                        writer.writerow(row)
