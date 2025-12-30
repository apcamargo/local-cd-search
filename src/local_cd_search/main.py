import sys
from pathlib import Path

import rich_click as click

from local_cd_search.annotate import run_pipeline
from local_cd_search.download import prepare_databases
from local_cd_search.logger import console, set_quiet
from local_cd_search.parser import parse_rpsbproc
from local_cd_search.utils import ensure_dir, remove_dir


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    """
    local-cd-search CLI group. Use the `download` subcommand to retrieve
    CDD metadata and the COG database. Use the `annotate` subcommand to
    run the annotation pipeline using an existing database/data directory.
    """
    pass


@main.command()
@click.argument(
    "db_dir", type=click.Path(file_okay=False, dir_okay=True, writable=True)
)
@click.argument(
    "databases",
    nargs=-1,
    required=True,
    type=click.Choice(
        ["cdd", "cdd_ncbi", "cog", "kog", "pfam", "prk", "smart", "tigr"],
        case_sensitive=False,
    ),
)
@click.option(
    "--force", is_flag=True, help="Force re-download even if files are present."
)
@click.option("--quiet", is_flag=True, help="Suppress non-error console output.")
def download(db_dir, databases, force, quiet):
    """
    Download one or more PSSM databases and CDD metadata into DB_DIR.
    """
    try:
        if quiet:
            set_quiet(True)

        console.log(f"Preparing to download databases into: {db_dir}")
        db_list = [d.lower() for d in databases]
        prepare_databases(db_dir, databases=db_list, force=force)
        console.log(f"Databases downloaded to: {db_dir}")

    except Exception:
        console.print_exception()
        sys.exit(1)


@main.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_file", type=click.Path(writable=True))
@click.argument("db_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "-e",
    "--evalue",
    default=0.01,
    type=click.FloatRange(min=0, max=None),
    show_default=True,
    help="Maximum allowed E-value for hits.",
)
@click.option(
    "--ns", is_flag=True, help="Include non-specific hits in the output results table."
)
@click.option("--sf", is_flag=True, help="Include superfamily hits in the output results table.")
@click.option("--quiet", is_flag=True, help="Suppress non-error console output.")
@click.option("--keep-tmp", is_flag=True, help="Keep intermediate temporary files.")
@click.option(
    "--tmp-dir",
    default="tmp",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Directory to store intermediate files.",
    show_default=True,
)
@click.option(
    "--threads",
    default=0,
    type=int,
    show_default=True,
    help="Number of threads to use for rpsblast.",
)
@click.option(
    "-m",
    "--data-mode",
    "data_mode",
    type=click.Choice(["std", "rep", "full"]),
    default="std",
    show_default=True,
    help=(
        "Redundancy level of domain hit data passed to rpsbproc. "
        "'rep' (best model per region of the query), 'std' "
        "(best model per source per region of the query), 'full' "
        "(all models meeting E-value significance)."
    ),
)
def annotate(
    input_file,
    output_file,
    db_dir,
    evalue,
    ns,
    sf,
    quiet,
    keep_tmp,
    tmp_dir,
    threads,
    data_mode,
):
    """
    Run the annotation pipeline.
    """
    try:
        if quiet:
            set_quiet(True)

        # Ensure the tmp directory exists before running the pipeline so
        # intermediates are created directly inside it.
        tmp_dir_path = ensure_dir(tmp_dir)

        # Run pipeline with the provided db_dir so intermediates are written there
        result = run_pipeline(
            input_file, db_dir, tmp_dir_path, threads, evalue, data_mode
        )
        intermediate_path = Path(result)

        # Step 2: Use the local parser module as a library
        console.log(f"Generating the output results table: {output_file}")
        parse_rpsbproc(
            input_file=str(intermediate_path),
            output_file=output_file,
            include_ns=ns,
            include_sf=sf,
        )

        # Remove the whole tmp directory unless the user requested to keep it.
        try:
            if not keep_tmp and tmp_dir_path.exists():
                remove_dir(tmp_dir_path)
                console.log(f"Removed temporary directory: {tmp_dir_path}")
        except Exception:
            console.log("Warning: failed to remove temporary directory.")
            console.print_exception()

        console.log(f"Results saved to {output_file}")

    except Exception:
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
