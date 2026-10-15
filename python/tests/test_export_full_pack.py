import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "export_full_pack.py"
SPEC = importlib.util.spec_from_file_location("export_full_pack", SCRIPT)
full_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(full_pack)


class FullPackCallsiteOptionTest(unittest.TestCase):
    def launch(self, options, *, publish_reference=True, launch_returncode=0):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "snapshot"

            def launched(command, **kwargs):
                if "runFullPack" in command:
                    output.mkdir()
                    (output / "manifest.json").write_text("{}", encoding="utf-8")
                    if "-PdataNeiReference=true" in command and publish_reference:
                        (output / "nei-reference").mkdir()
                        (output / "nei-reference" / "summary.json").write_text("{}", encoding="utf-8")
                    return subprocess.CompletedProcess(command, launch_returncode)
                return subprocess.CompletedProcess(command, 0)

            arguments = [str(SCRIPT), "--output", str(output), "--python", sys.executable] + options
            with patch.object(full_pack.sys, "argv", arguments), \
                    patch.object(full_pack.subprocess, "run", side_effect=launched) as run, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    result = full_pack.main()
                except SystemExit as error:
                    self.fail(f"The public full-pack CLI rejected its options: {error.code}")

            return result, [call.args[0] for call in run.call_args_list]

    def test_opt_in_reaches_native_launch_without_enabling_nei_reference(self):
        result, commands = self.launch(["--native-recipe-callsites"])
        launch = commands[0]
        self.assertEqual(0, result)
        self.assertIn("-PdataNativeRecipeCallsites=true", launch)
        self.assertNotIn("-PdataNeiReference=true", launch)

    def test_default_launch_does_not_request_native_collection(self):
        result, commands = self.launch([])
        launch = commands[0]
        self.assertEqual(0, result)
        self.assertNotIn("-PdataNativeRecipeCallsites=true", launch)
        self.assertNotIn("-PdataNeiReference=true", launch)
        self.assertFalse(any(arg.startswith("-PdataNeiReferenceScope=") for arg in launch))
        self.assertEqual(2, len(commands))

    def test_still_reference_scope_reaches_the_existing_launch(self):
        result, commands = self.launch(["--nei-reference", "forestry_still"])
        launch = commands[0]
        self.assertEqual(0, result)
        self.assertIn("-PdataNeiReference=true", launch)
        self.assertIn("-PdataNeiReferenceScope=forestry_still", launch)
        self.assertNotIn("-PdataNativeRecipeCallsites=true", launch)
        self.assertEqual(2, len(commands))
        self.assertEqual([sys.executable, "-m", "gtnh_data", "import"], commands[1][:4])

    def test_bare_and_explicit_all_reference_keep_unscoped_launch(self):
        for options in (["--nei-reference"], ["--nei-reference", "all"]):
            with self.subTest(options=options):
                result, commands = self.launch(options)
                self.assertEqual(0, result)
                self.assertEqual(["-PdataNeiReference=true"],
                    [arg for arg in commands[0] if arg.startswith("-PdataNeiReference")])
                self.assertEqual(2, len(commands))

    def test_unknown_reference_scope_is_rejected_before_launch(self):
        with patch.object(full_pack.sys, "argv", [str(SCRIPT), "--nei-reference", "unknown"]), \
                patch.object(full_pack.subprocess, "run") as run, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                full_pack.main()
        self.assertEqual(2, error.exception.code)
        run.assert_not_called()

    def test_scoped_reference_still_requires_summary_before_import(self):
        result, commands = self.launch(["--nei-reference", "forestry_still"], publish_reference=False)
        self.assertEqual(1, result)
        self.assertEqual(1, len(commands))

    def test_failed_launch_does_not_import_for_a_reference_scope(self):
        result, commands = self.launch(["--nei-reference", "forestry_still"], launch_returncode=7)
        self.assertEqual(7, result)
        self.assertEqual(1, len(commands))


if __name__ == "__main__":
    unittest.main()
