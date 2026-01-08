import sys
import tempfile
from pathlib import Path

import rich_click as click

from local_cd_search.annotate import run_pipeline
from local_cd_search.download import prepare_databases
from local_cd_search.logger import console, set_quiet
from local_cd_search.parser import parse_rpsbproc
from local_cd_search.utils import persistent_dir


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
@click.option(
    "--sf", is_flag=True, help="Include superfamily hits in the output results table."
)
@click.option("--quiet", is_flag=True, help="Suppress non-error console output.")
@click.option(
    "--tmp-dir",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Directory to store intermediate files. If not specified, temporary files will be deleted after execution.",
    show_default=False,
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
@click.option(
    "-s",
    "--sites-output",
    "sites_output",
    type=click.Path(writable=True),
    default=None,
    help="Path to write functional site annotations.",
    show_default=False,
)
def annotate(
    input_file,
    output_file,
    db_dir,
    evalue,
    ns,
    sf,
    quiet,
    tmp_dir,
    threads,
    data_mode,
    sites_output,
):
    """
    Run the annotation pipeline.
    """
    try:
        if quiet:
            set_quiet(True)

        # Determine context manager for temporary directory
        if tmp_dir:
            # User provided a directory: ensure it exists and do NOT delete it.
            dir_context = persistent_dir(tmp_dir)
            console.log(f"Using provided temporary directory: {tmp_dir}")
        else:
            # No directory provided: use a temporary one that cleans up automatically.
            dir_context = tempfile.TemporaryDirectory()

        with dir_context as d:
            # tempfile.TemporaryDirectory yields a string, ensure it's a Path
            tmp_path = Path(d)

            # Run pipeline with the provided db_dir so intermediates are written there
            result = run_pipeline(
                input_file, db_dir, tmp_path, threads, evalue, data_mode
            )
            intermediate_path = Path(result)

            # Step 2: Use the local parser module as a library
            console.log(f"Generating the output results table: {output_file}")
            if sites_output:
                console.log(
                    f"Generating the output functional sites table: {sites_output}"
                )

            parse_rpsbproc(
                input_file=str(intermediate_path),
                output_file=output_file,
                sites_output_file=sites_output,
                include_ns=ns,
                include_sf=sf,
            )

        console.log(f"Results saved to {output_file}")
        if sites_output:
            console.log(f"Functional sites saved to {sites_output}")

    except Exception:
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
