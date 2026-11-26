import subprocess
import sys
import unittest
from human3d import __version__

class FoundationTest(unittest.TestCase):
    def test_version(self):
        result = subprocess.run([sys.executable, "-m", "human3d", "--version"],
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), __version__)
