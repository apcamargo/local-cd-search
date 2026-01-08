import contextlib
import os
import subprocess
import sys
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import IO, TYPE_CHECKING

from rich.console import Console as RichConsole

from .logger import console

if TYPE_CHECKING:
    from .download import FileDownloader

PathLike = str | Path
CmdType = Sequence[str | Path | bytes]


def ensure_dir(path: PathLike) -> Path:
    """
    Ensure that `path` exists as a directory and return a Path object.

    This is idempotent and will create parent directories as needed.

    Parameters
    ----------
    path : str | Path
        Directory path to ensure exists.

    Returns
    -------
    Path
        A pathlib.Path object for the created/existing directory.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def styled_error(message: str, *, exit_code: int | None = None) -> None:
    """
    Print a styled error message to stderr using rich and optionally exit.

    Parameters
    ----------
    message : str
        Error text to display.
    exit_code : int, optional
        If provided, call ``sys.exit(exit_code)`` after printing.
    """
    err_console = RichConsole(stderr=True, style="bold red")
    err_console.print(message)
    if exit_code is not None:
        sys.exit(exit_code)


def remove_dir(path: PathLike, *, on_error_message: str | None = None) -> None:
    """
    Remove a directory tree at `path`.

    On failure, prints a styled error and re-raises the exception.

    Parameters
    ----------
    path : str | Path
        Directory to remove.
    on_error_message : str, optional
        Message prefix to display alongside exception info.

    Raises
    ------
    Exception
        The original exception raised by ``shutil.rmtree`` on failure.
    """
    p = Path(path)
    try:
        if p.exists():
            # Import locally to keep module import cost small.
            import shutil

            shutil.rmtree(p)
    except Exception as exc:
        msg = on_error_message or f"Error: failed to remove directory at {p}:"
        styled_error(f"{msg} {exc}")
        raise


def _format_command(cmd: CmdType) -> str:
    """Return a human-friendly representation of `cmd` for logs and errors."""
    return " ".join(str(x) for x in cmd)


def run_and_log(
    cmd: CmdType, log_path: PathLike, *, raise_on_err: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command and stream stdout/stderr to a log file.

    The function writes both stdout and stderr into `log_path`. If the process
    exits with a non-zero status, a styled error is printed pointing the user
    to the log file.

    Parameters
    ----------
    cmd : Sequence[str | Path | bytes]
        Command as a sequence of arguments.
    log_path : str | Path
        File path to capture stdout/stderr.
    raise_on_err : bool
        Whether to raise on non-zero exit. Default is True.

    Returns
    -------
    subprocess.CompletedProcess
        The completed process on success.

    Raises
    ------
    subprocess.CalledProcessError
        If the command fails and `raise_on_err` is True.
    """
    log_p = Path(log_path)
    ensure_dir(log_p.parent)

    with open(log_p, "w") as fout:
        try:
            completed = subprocess.run(
                list(map(str, cmd)), stdout=fout, stderr=fout, check=True
            )
            return completed
        except subprocess.CalledProcessError as e:
            command_str = _format_command(cmd)
            styled_error(f"Error: '{command_str}' failed. See log: {log_p}")
            if raise_on_err:
                raise
            # Returning the exception object is useful for callers that inspect it.
            return e  # type: ignore[return-value]


@contextmanager
def persistent_dir(path: PathLike) -> Generator[Path, None, None]:
    """
    Context manager that ensures a directory exists and yields its path.

    Unlike tempfile.TemporaryDirectory, this does NOT delete the directory
    upon exit.

    Parameters
    ----------
    path : str | Path
        Directory path to ensure exists.

    Yields
    ------
    Path
        The path to the existing directory.
    """
    p = ensure_dir(path)
    yield p


@contextmanager
def downloader_context(
    use_console: RichConsole | None = None,
) -> Generator[tuple["FileDownloader", IO[str] | None], None, None]:
    """
    Context manager that yields a configured FileDownloader instance.

    When the package central console is in quiet mode, this helper opens a
    RichConsole that writes to os.devnull and constructs FileDownloader with
    it. The devnull file is closed automatically when exiting the context.

    Parameters
    ----------
    use_console : rich.console.Console, optional
        Rich Console to use instead of the package default console.

    Yields
    ------
    tuple[FileDownloader, IO[str] | None]
        A tuple containing the FileDownloader instance and an optional file
        object (writing to os.devnull) when quiet-mode suppression is active.
    """
    # Import FileDownloader lazily to avoid a top-level circular import
    from .download import FileDownloader

    devnull: IO | None = None
    try:
        active_console = use_console if use_console is not None else console
        if getattr(active_console, "is_quiet", False):
            devnull = open(os.devnull, "w")  # noqa: SIM115
            dl = FileDownloader(RichConsole(file=devnull))
        else:
            dl = FileDownloader()
    except Exception:
        # If anything goes wrong constructing the devnull console, fall back
        # to the default downloader instance.
        dl = FileDownloader()
        if devnull is not None:
            try:
                devnull.close()
            except Exception:
                devnull = None

    try:
        yield dl, devnull
    finally:
        if devnull is not None:
            with contextlib.suppress(Exception):
                devnull.close()
