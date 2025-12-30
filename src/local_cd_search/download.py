import contextlib
import gzip
import shutil
import urllib.request
from collections.abc import Sequence
from functools import partial
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from local_cd_search.logger import console as central_console
from local_cd_search.utils import downloader_context, ensure_dir, remove_dir


class FileDownloader:
    """Small helper that downloads a URL while showing a rich progress bar."""

    def __init__(self, console: Console | None = None) -> None:
        """
        Initialize a FileDownloader.

        Parameters
        ----------
        console:
            Optional rich `Console` instance. When omitted, defaults to the
            package central console's raw console.
        """
        # Prefer a real Console instance. The package central_console exposes
        # a `.raw` Console which we use as the default.
        if console is None:
            self.console: Console = central_console.raw
        else:
            self.console = console

    def _copy_url(
        self, task_id: TaskID, progress: Progress, url: str, destination: Path
    ) -> None:
        with urllib.request.urlopen(url) as response:
            content_length = response.info().get("Content-length")
            if content_length:
                progress.update(task_id, total=int(content_length))

            with open(destination, "wb") as dest_file:
                progress.start_task(task_id)
                for data in iter(partial(response.read, 32768), b""):
                    dest_file.write(data)
                    progress.update(task_id, advance=len(data))

    def download(self, url: str, destination: str | Path, filename: str) -> None:
        """Download `url` to `destination` while showing a progress bar."""
        progress = Progress(
            TextColumn("{task.fields[filename]}", justify="right", style="green"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "|",
            DownloadColumn(),
            "|",
            TransferSpeedColumn(),
            "|",
            TimeRemainingColumn(elapsed_when_finished=True),
            console=self.console,
            transient=True,
        )
        with progress:
            task_id = progress.add_task("download", filename=filename, start=False)
            self._copy_url(task_id, progress, url, Path(destination))


def prepare_databases(
    db_dir: str | Path,
    databases: Sequence[str] | None = None,
    force: bool = False,
) -> None:
    """
    Download and prepare one or more CDD-derived databases and CDD metadata under `db_dir`.

    By default (when `databases` is None) this will behave like the prior
    implementation and download the `cog` database and the CDD metadata.

    Supported database keys (case-sensitive):
        - "cdd"        -> Cdd_LE.tar.gz
        - "cdd_ncbi"   -> Cdd_NCBI_LE.tar.gz
        - "cog"        -> Cog_LE.tar.gz
        - "kog"        -> Kog_LE.tar.gz
        - "pfam"       -> Pfam_LE.tar.gz
        - "prk"        -> Prk_LE.tar.gz
        - "smart"      -> Smart_LE.tar.gz
        - "tigr"       -> Tigr_LE.tar.gz

    Parameters
    ----------
    db_dir : str | Path
        Directory where database directories (e.g. `Cog`, `Pfam`) and `data`
        directory will be created.
    databases : Sequence[str] | None
        Sequence of database keys to download. If None, defaults to ["cog"].
    force : bool
        If True, re-download and overwrite existing files/directories.
    """
    # Default to original behavior if nothing provided
    if databases is None:
        databases = ["cog"]

    # Validate databases and map to tarball prefixes / target directory names
    allowed = {
        "cdd": "Cdd",
        "cdd_ncbi": "Cdd_NCBI",
        "cog": "Cog",
        "kog": "Kog",
        "pfam": "Pfam",
        "prk": "Prk",
        "smart": "Smart",
        "tigr": "Tigr",
    }

    invalid = [d for d in databases if d not in allowed]
    if invalid:
        raise ValueError(
            f"Invalid database keys: {invalid}. Allowed values: {sorted(allowed.keys())}"
        )

    base = Path(db_dir)
    # Ensure data directory (CDD metadata) exists
    data_dir = ensure_dir(base / "data")

    # Base URL for the tarballs
    base_tar_url = "https://ftp.ncbi.nih.gov/pub/mmdb/cdd/little_endian"

    # Use the downloader context which handles quiet-mode console -> devnull.
    with downloader_context() as (dl, _devnull):
        # Download each requested database sequentially
        for db_key in databases:
            prefix = allowed[db_key]
            target_dir = ensure_dir(base / prefix)

            # If directory exists and not forcing, skip
            if any(target_dir.iterdir()) and not force:
                central_console.log(
                    f"{prefix} database already present at {target_dir}; skipping download."
                )
                continue

            # If force is requested and target exists, remove then recreate
            if any(target_dir.iterdir()) and force:
                remove_dir(
                    target_dir,
                    on_error_message=f"Error: failed to remove existing {prefix} directory at {target_dir}:",
                )
                ensure_dir(target_dir)

            with central_console.status(
                f"Downloading {db_key.lower()} PSSM database..."
            ):
                tar_name = f"{prefix}_LE.tar.gz"
                tar_path = target_dir / tar_name
                dl.download(f"{base_tar_url}/{tar_name}", tar_path, tar_name)
                shutil.unpack_archive(str(tar_path), str(target_dir), "gztar")
                with contextlib.suppress(Exception):
                    tar_path.unlink()
                central_console.log(f"{db_key.lower()} database download complete.")

        # 2. CDD Metadata (always sync metadata as before)
        # If force is requested and the data directory exists, attempt removal first
        if data_dir.exists() and force:
            # remove_dir prints a styled error and raises on failure
            remove_dir(
                data_dir,
                on_error_message=f"Error: failed to remove existing data directory at {data_dir}:",
            )
            # recreate directory after successful removal
            ensure_dir(data_dir)

        with central_console.status("Downloading CDD metadata..."):
            base_url = "https://ftp.ncbi.nih.gov/pub/mmdb/cdd"
            files = [
                "bitscore_specific.txt",
                "cddid.tbl.gz",
                "cdtrack.txt",
                "family_superfamily_links",
                "cddannot.dat.gz",
                "cddannot_generic.dat.gz",
            ]

            for file_name in files:
                output_name = file_name.replace(".gz", "")
                target_path = data_dir / output_name

                # If the target already exists and force is not requested, skip this file
                if target_path.exists() and not force:
                    central_console.log(
                        f"{output_name} already exists. Skipping download."
                    )
                    continue

                if file_name.endswith(".gz"):
                    temp_gz = data_dir / file_name
                    dl.download(f"{base_url}/{file_name}", temp_gz, file_name)
                    with (
                        gzip.open(temp_gz, "rt") as f_in,
                        open(target_path, "w") as f_out,
                    ):
                        for line in f_in:
                            f_out.write(line)
                    with contextlib.suppress(Exception):
                        temp_gz.unlink()
                else:
                    dl.download(f"{base_url}/{file_name}", target_path, file_name)
        central_console.log("CDD metadata download complete.")


__all__ = ["prepare_databases", "FileDownloader"]
