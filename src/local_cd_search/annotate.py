from pathlib import Path

from local_cd_search.logger import console
from local_cd_search.utils import PathLike, ensure_dir, run_and_log


def run_pipeline(
    input_fasta: PathLike,
    db_dir: PathLike,
    tmp_dir: PathLike,
    threads: int,
    evalue: float = 0.01,
    data_mode: str = "std",
) -> Path:
    """
    Run the annotation pipeline using the Cog and data located under `db_dir`.

    Parameters
    ----------
    input_fasta : str | Path
        Path to the input FASTA file.
    db_dir : str | Path
        Directory that contains `Cog` and `data` subdirectories.
    tmp_dir : str | Path
        Directory where intermediate files will be written.
    threads : int
        Number of threads to use for rpsblast.
    evalue : float
        Maximum E-value allowed for RPS-BLAST hits.
    data_mode : str
        Mode for rpsbproc data redundancy: 'std', 'rep', or 'full'.

    Returns
    -------
    Path
        Path to the final rpsbproc output file (to be parsed).
    """
    base = Path(db_dir)
    data_dir = base / "data"

    # Look only for the known database directory names inside `db_dir`.
    # For each allowed name present as a directory we build the conventional
    # prefix `base/Name/Name` to pass to rpsblast.
    allowed = ["Cdd", "Cdd_NCBI", "Cog", "Kog", "Pfam", "Prk", "Smart", "Tigr"]
    db_roots = []
    if base.exists():
        for name in allowed:
            dirp = base / name
            if dirp.exists() and dirp.is_dir():
                # Construct prefix like 'database/Cog/Cog' as requested
                db_roots.append(str(dirp / name))

    if not db_roots or not data_dir.exists():
        console.log(
            "Required database(s) or data directory not found. Please run the 'download' command first."
        )
        raise FileNotFoundError(
            "Database directories or data directory missing in db_dir"
        )

    # Ensure temporary directory exists and prepare intermediate file paths inside it
    tmp_path = ensure_dir(tmp_dir)

    prefix = Path(input_fasta).stem
    results_asn = tmp_path / f"{prefix}_rpsblast.asn"
    final_annotation = tmp_path / f"{prefix}_rpsbproc.txt"

    # Run RPS-BLAST
    console.log(f"Running RPS-BLAST on {input_fasta}...")
    # Log which databases will be used (short names only, e.g. Pfam, Smart, Tigr)
    short_names = [str(Path(p).name) for p in db_roots]
    console.log("Databases to be used for annotation: " + ", ".join(short_names))

    # Build the -db argument by concatenating discovered database paths.
    # When multiple databases are present, they are supplied together as a
    # single argument (space-separated) so rpsblast receives them all.
    db_arg = " ".join(db_roots)
    rpsblast_cmd = [
        "rpsblast",
        "-query",
        str(input_fasta),
        "-db",
        db_arg,
        "-evalue",
        str(evalue),
        "-outfmt",
        "11",
        "-num_threads",
        str(threads),
        "-seg",
        "no",
        "-comp_based_stats",
        "1",
        "-out",
        str(results_asn),
    ]
    rpsblast_log = tmp_path / "rpsblast.log"
    with console.status(f"Running RPS-BLAST on {input_fasta}..."):
        run_and_log(rpsblast_cmd, rpsblast_log)
        console.log("RPS-BLAST completed.")

    # Run rpsbproc
    rpsbproc_cmd = [
        "rpsbproc",
        "-q",
        "-m",
        data_mode,
        "-i",
        str(results_asn),
        "-o",
        str(final_annotation),
        "-d",
        str(data_dir),
    ]
    rpsbproc_log = tmp_path / "rpsbproc.log"
    with console.status("Processing with rpsbproc..."):
        run_and_log(rpsbproc_cmd, rpsbproc_log)
        console.log("rpsbproc completed.")

    return final_annotation


__all__ = ["run_pipeline"]
