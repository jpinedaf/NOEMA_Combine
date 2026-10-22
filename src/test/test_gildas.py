from pathlib import Path

from noema_combine.gildas import GildasRunner


def test_script_only_runner_retains_generated_script(tmp_path: Path):
    runner = GildasRunner(execute=False, workdir=tmp_path)
    result = runner.run_class("say 'hello'")

    assert result.executed is False
    assert result.succeeded is True
    assert result.script_path.exists()
    assert result.script_path.read_text() == "say 'hello'"


def test_runner_executes_configured_program_and_checks_outputs(tmp_path: Path):
    executable = tmp_path / "fake_gildas"
    executable.write_text(
        "#!/bin/sh\n"
        "touch expected.out\n"
    )
    executable.chmod(0o755)

    runner = GildasRunner(
        execute=True,
        workdir=tmp_path,
        commands={"class": str(executable)},
    )
    result = runner.run_class("say 'hello'", expected_outputs=[tmp_path / "expected.out"])

    assert result.executed is True
    assert result.returncode == 0
    assert result.succeeded is True
    assert (tmp_path / "expected.out").exists()


def test_runner_can_remove_scripts_after_execution(tmp_path: Path):
    executable = tmp_path / "fake_gildas"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    runner = GildasRunner(
        execute=True,
        workdir=tmp_path,
        commands={"mapping": str(executable)},
        keep_scripts=False,
    )

    result = runner.run_mapping("exit")

    assert not result.script_path.exists()


def test_runner_runs_setup_command_before_gildas_program(tmp_path: Path):
    setup = tmp_path / "setup.sh"
    setup.write_text("touch setup-ran\n")
    executable = tmp_path / "fake_mapping"
    executable.write_text("#!/bin/sh\ntouch expected.out\n")
    executable.chmod(0o755)
    runner = GildasRunner(
        execute=True,
        workdir=tmp_path,
        commands={"mapping": str(executable)},
        setup=f"source {setup}",
    )

    result = runner.run_mapping(
        "exit",
        expected_outputs=[tmp_path / "setup-ran", tmp_path / "expected.out"],
    )

    assert result.executed is True
    assert result.succeeded is True
    assert result.command[0] == "/bin/bash"
    assert (tmp_path / "setup-ran").exists()


def test_runner_can_source_a_file_defining_a_setup_function(tmp_path: Path):
    setup_file = tmp_path / "gildas_functions.sh"
    setup_file.write_text("gildas_test() { touch function-setup-ran; }\n")
    executable = tmp_path / "fake_mapping"
    executable.write_text("#!/bin/sh\ntouch expected.out\n")
    executable.chmod(0o755)
    runner = GildasRunner(
        execute=True,
        workdir=tmp_path,
        commands={"mapping": str(executable)},
        setup="gildas_test",
        setup_file=setup_file,
        env={"HOME": str(tmp_path)},
    )

    result = runner.run_mapping(
        "exit",
        expected_outputs=[tmp_path / "function-setup-ran", tmp_path / "expected.out"],
    )

    assert result.succeeded is True
    assert (tmp_path / "function-setup-ran").exists()


def test_runner_sends_exit_to_noninteractive_gildas(tmp_path: Path):
    executable = tmp_path / "fake_gildas"
    executable.write_text(
        "#!/bin/sh\n"
        "read command\n"
        "[ \"$command\" = exit ]\n"
    )
    executable.chmod(0o755)
    runner = GildasRunner(
        execute=True,
        workdir=tmp_path,
        commands={"class": str(executable)},
    )

    result = runner.run_class("say 'hello'")

    assert result.succeeded is True
