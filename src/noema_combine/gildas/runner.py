"""Run generated CLASS, MAPPING, and CLIC scripts when requested."""

from __future__ import annotations

from dataclasses import dataclass
import os
import shlex
from pathlib import Path
import subprocess
import tempfile
from collections.abc import Iterable, Mapping


@dataclass(frozen=True)
class GildasResult:
    """Result of generating and optionally executing a GILDAS script."""

    program: str
    script_path: Path
    command: tuple[str, ...]
    executed: bool
    returncode: int | None
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        """Whether execution was skipped or completed successfully."""
        return not self.executed or self.returncode == 0


class GildasRunner:
    """Generate and optionally execute GILDAS command files.

    Execution defaults to enabled. Set ``execute=False`` for the script-only
    workflow; the generated script is retained in that mode by default.
    """

    def __init__(
        self,
        *,
        execute: bool = True,
        workdir: str | os.PathLike[str] = ".",
        commands: Mapping[str, str] | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        keep_scripts: bool | None = None,
        setup: str | None = None,
        shell: str = "/bin/bash",
        setup_file: str | os.PathLike[str] | None = None,
        interactive: bool = False,
    ) -> None:
        self.execute = execute
        self.workdir = Path(workdir).expanduser().resolve()
        self.commands = {
            "class": "class",
            "mapping": "mapping",
            "clic": "clic",
        }
        if commands:
            self.commands.update(commands)
        self.env = dict(env) if env is not None else None
        self.timeout = timeout
        self.keep_scripts = not execute if keep_scripts is None else keep_scripts
        self.setup = (setup or "").strip()
        self.shell = shell
        self.setup_file = str(setup_file) if setup_file else ""
        self.interactive = interactive

    def run(
        self,
        program: str,
        script: str,
        *,
        suffix: str = ".class",
        execute: bool | None = None,
        expected_outputs: Iterable[str | os.PathLike[str]] = (),
        keep_script: bool | None = None,
    ) -> GildasResult:
        """Write a script and optionally execute its GILDAS program.

        ``program`` may be ``class``, ``mapping``, or ``clic`` and can also be
        an explicit executable path. A non-zero exit status or missing expected
        output raises ``RuntimeError`` after the result has been captured.
        """
        if not script.strip():
            raise ValueError("GILDAS script cannot be empty")
        run_enabled = self.execute if execute is None else execute
        retain = self.keep_scripts if keep_script is None else keep_script
        self.workdir.mkdir(parents=True, exist_ok=True)
        command_program = self.commands.get(program, program)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            prefix="noema_combine_",
            dir=self.workdir,
            delete=False,
        ) as handle:
            handle.write(script)
            script_path = Path(handle.name)

        direct_command = (command_program, "-nw", "@", str(script_path))
        if self.setup or self.setup_file:
            setup_parts = []
            if self.setup_file:
                setup_parts.append(f"source {shlex.quote(self.setup_file)}")
            if self.setup:
                setup_parts.append(self.setup)
            setup_parts.append(f"exec {shlex.join(direct_command)}")
            command_text = " && ".join(setup_parts)
            shell_flags = "-ilc" if self.interactive else "-lc"
            command = (self.shell, shell_flags, command_text)
        else:
            command = direct_command
        result = GildasResult(
            program=program,
            script_path=script_path,
            command=command,
            executed=False,
            returncode=None,
            stdout="",
            stderr="",
        )
        try:
            if run_enabled:
                completed = subprocess.run(
                    command,
                    cwd=self.workdir,
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
                result = GildasResult(
                    program=program,
                    script_path=script_path,
                    command=command,
                    executed=True,
                    returncode=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
                if completed.returncode != 0:
                    raise RuntimeError(
                        f"GILDAS {program} failed with exit code {completed.returncode}: "
                        f"{completed.stderr.strip()}"
                    )

            if run_enabled:
                missing: list[str] = []
                for output in expected_outputs:
                    output_path = Path(output)
                    if not output_path.is_absolute():
                        output_path = self.workdir / output_path
                    if not output_path.exists():
                        missing.append(str(output_path))
                if missing:
                    raise RuntimeError(
                        f"GILDAS {program} did not create expected output(s): {', '.join(missing)}"
                    )
            return result
        finally:
            if not retain:
                script_path.unlink(missing_ok=True)

    def run_class(self, script: str, **kwargs: object) -> GildasResult:
        """Run or generate a CLASS script."""
        return self.run("class", script, suffix=".class", **kwargs)

    def run_mapping(self, script: str, **kwargs: object) -> GildasResult:
        """Run or generate a MAPPING script."""
        return self.run("mapping", script, suffix=".map", **kwargs)

    def run_clic(self, script: str, **kwargs: object) -> GildasResult:
        """Run or generate a CLIC script."""
        return self.run("clic", script, suffix=".clic", **kwargs)
