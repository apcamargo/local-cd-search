import re
from contextlib import AbstractContextManager, nullcontext
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.text import Text

try:
    # Configure rich-click globally if available
    import rich_click

    rich_click.USE_RICH_MARKUP = True
    rich_click.SHOW_ARGUMENTS = True
    rich_click.GROUP_ARGUMENTS_OPTIONS = True
except ImportError:
    # rich_click isn't available; the package still works without it
    pass


class CentralConsole:
    """
    A thin wrapper around rich.console.Console that supports global quiet mode.

    When quiet is enabled, ``log`` and ``print`` become no-ops.
    ``print_exception`` will still emit so errors remain visible by default.

    Parameters
    ----------
    console : rich.console.Console, optional
        An existing Console instance to wrap. If None, a new Console is created.
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()
        self._quiet = False

    def set_quiet(self, quiet: bool) -> None:
        """
        Enable or disable quiet mode.

        Parameters
        ----------
        quiet : bool
            If True, suppress log and print output.
        """
        self._quiet = bool(quiet)

    @property
    def is_quiet(self) -> bool:
        """Return True if quiet mode is enabled."""
        return bool(self._quiet)

    def log(self, *args: Any, **kwargs: Any) -> None:
        """
        Log a timestamped message with markup tags removed.

        Removes any bracketed markup tokens like [bold], [cyan], etc., then
        prints a timestamped line to the console.

        Parameters
        ----------
        *args : Any
            Values to log. Will be converted to strings and joined with spaces.
        **kwargs : Any
            Additional keyword arguments (currently unused).
        """
        if self._quiet:
            return

        # Combine args into a single string and remove bracketed tags
        raw = " ".join(str(a) for a in args)
        sanitized = re.sub(r"\[[^\]]*\]", "", raw)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        # Timestamp (HH:MM:SS) rendered with dim/log.time style
        t = datetime.now().strftime("%H:%M:%S")
        ts_text = Text(f"[{t}] ", style="log.time")

        # Print timestamp then sanitized message (no markup)
        self._console.print(ts_text, end="")
        self._console.print(Text(sanitized))

    def print(self, *args: Any, **kwargs: Any) -> None:
        """
        Print to console with markup tags removed. Suppressed when quiet.

        For full markup support, use ``console.raw.print(...)``.

        Parameters
        ----------
        *args : Any
            Values to print.
        **kwargs : Any
            Additional keyword arguments passed to Console.print.
        """
        if self._quiet:
            return

        # If first arg is a string and begins with newline(s), remove them.
        if args and isinstance(args[0], str) and args[0].startswith("\n"):
            first = args[0].lstrip("\n")
            args = (first,) + args[1:]

        # Sanitize string arguments by removing bracketed markup tokens
        sanitized_args = []
        for a in args:
            if isinstance(a, str):
                s = re.sub(r"\[[^\]]*\]", "", a)
                s = re.sub(r"\s+", " ", s).strip()
                sanitized_args.append(s)
            else:
                sanitized_args.append(a)

        self._console.print(*sanitized_args, **kwargs)

    def print_exception(self, *args: Any, **kwargs: Any) -> None:
        """
        Print an exception traceback. Always visible, even in quiet mode.

        Parameters
        ----------
        *args : Any
            Positional arguments passed to Console.print_exception.
        **kwargs : Any
            Keyword arguments passed to Console.print_exception.
        """
        self._console.print_exception(*args, **kwargs)

    @property
    def raw(self) -> Console:
        """Return the underlying rich.console.Console instance."""
        return self._console

    def status(self, message: str) -> AbstractContextManager:
        """
        Context manager for showing a spinner/status while work is performed.

        When quiet mode is enabled, returns a no-op context manager.

        Parameters
        ----------
        message : str
            Status message to display alongside the spinner.

        Returns
        -------
        AbstractContextManager
            A context manager that displays a status spinner.

        Examples
        --------
        >>> with console.status("Working..."):
        ...     do_work()
        """
        if self._quiet:
            return nullcontext()
        return self._console.status(message)


# Single shared console instance for the package
console = CentralConsole()


def set_quiet(quiet: bool = True) -> None:
    """
    Set the global quiet flag for the package console.

    Parameters
    ----------
    quiet : bool
        If True, ``console.log`` and ``console.print`` will be suppressed.
    """
    console.set_quiet(quiet)
