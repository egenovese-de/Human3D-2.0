import builtins
import contextlib
import io
import unittest
from unittest.mock import patch
from human3d.__main__ import main

class DependencyFailures(unittest.TestCase):
    def test_operation_import_failures(self):
        for args, module in [
            (["detect-target", "project", "--model", "model.task"], "session"),
            (["freeze-neutral", "assets", "output"], "bootstrap"),
            (["freeze-project", "project", "--assets", "assets"], "project_store"),
            (["inspect-body", "project"], "project_store"),
        ]:
            for error in (ImportError("missing dependency"), OSError("native library unavailable")):
                with self.subTest(args=args, error=type(error).__name__):
                    original = builtins.__import__
                    def failing(name, *a, **kw):
                        if name == module:
                            raise error
                        return original(name, *a, **kw)
                    stderr = io.StringIO()
                    with patch("sys.argv", ["human3d", *args]), patch("builtins.__import__", side_effect=failing), contextlib.redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as result:
                            main()
                    self.assertEqual(result.exception.code, 1)
                    self.assertIn(str(error), stderr.getvalue())
                    self.assertNotIn("Traceback", stderr.getvalue())
