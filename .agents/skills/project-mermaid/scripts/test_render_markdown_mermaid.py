#!/usr/bin/env python3

import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("render_markdown_mermaid.py")
SPEC = importlib.util.spec_from_file_location("render_markdown_mermaid", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RenderMarkdownMermaidTests(unittest.TestCase):
    def test_extracts_backtick_and_tilde_fences(self):
        markdown = """# Draft

```mermaid
flowchart LR
    A --> B
```

~~~MERMAID
sequenceDiagram
    A->>B: call
~~~~
"""
        fences = MODULE.extract_mermaid_fences(markdown)
        self.assertEqual(2, len(fences))
        self.assertEqual((3, 6), (fences[0].start_line, fences[0].end_line))
        self.assertIn("sequenceDiagram", fences[1].source)

    def test_ignores_non_mermaid_fence(self):
        markdown = "```go\nfunc main() {}\n```\n"
        self.assertEqual([], MODULE.extract_mermaid_fences(markdown))

    def test_rejects_unclosed_fence(self):
        with self.assertRaisesRegex(ValueError, "unclosed Mermaid fence"):
            MODULE.extract_mermaid_fences("```mermaid\nflowchart LR\n")

    def test_reads_png_dimensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "image.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 640, 480))
            self.assertEqual((640.0, 480.0), MODULE.output_dimensions(path))


if __name__ == "__main__":
    unittest.main()
