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
    def launch(self, options):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "snapshot"

            def launched(command, **kwargs):
                if "runFullPack" in command:
                    output.mkdir()
                    (output / "manifest.json").write_text("{}", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0)

            arguments = [str(SCRIPT), "--output", str(output), "--python", sys.executable] + options
            with patch.object(full_pack.sys, "argv", arguments), \
                    patch.object(full_pack.subprocess, "run", side_effect=launched) as run, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    result = full_pack.main()
                except SystemExit as error:
                    self.fail(f"The public full-pack CLI rejected its callsite option: {error.code}")

            return result, run.call_args_list[0].args[0]

    def test_opt_in_reaches_native_launch_without_enabling_nei_reference(self):
        result, launch = self.launch(["--native-recipe-callsites"])
        self.assertEqual(0, result)
        self.assertIn("-PdataNativeRecipeCallsites=true", launch)
        self.assertNotIn("-PdataNeiReference=true", launch)

    def test_default_launch_does_not_request_native_collection(self):
        result, launch = self.launch([])
        self.assertEqual(0, result)
        self.assertNotIn("-PdataNativeRecipeCallsites=true", launch)
        self.assertNotIn("-PdataNeiReference=true", launch)


if __name__ == "__main__":
    unittest.main()
