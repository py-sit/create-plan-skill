from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkspaceAndPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.init_module = load_module(
            "init_plan_workspace",
            ROOT / "scripts" / "init_plan_workspace.py",
        )

    def render_workspace(self, language: str) -> tuple[Path, str]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        workspace = Path(temporary.name)
        self.init_module.build_workspace(
            workspace,
            "Factory Reliability Plan",
            False,
            language,
        )
        self.assertTrue((workspace / "diagrams" / "architecture.mmd").is_file())
        self.assertTrue((workspace / "diagrams" / "user-flow.mmd").is_file())
        rendered = workspace / "diagrams" / "rendered"
        Image.new("RGB", (1000, 600), "white").save(rendered / "architecture.png")
        Image.new("RGB", (1000, 600), "white").save(rendered / "user-flow.png")
        proposal = workspace / "proposal.md"
        if language == "en-US":
            references = workspace / "references"
            references.mkdir(exist_ok=True)
            (references / "source.md").write_text("# Source\n", encoding="utf-8")
            proposal.write_text(
                proposal.read_text(encoding="utf-8")
                + (
                    "\nReference: [validation source](references/source.md) and "
                    "[external source](https://example.com/docs?a=1&b=2)\n"
                ),
                encoding="utf-8",
            )
        output = workspace / "output" / "pdf" / "formal-plan.pdf"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "render_plan_pdf.py"),
                str(proposal),
                "--output",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        text = "\n".join(
            page.extract_text() or "" for page in PdfReader(str(output)).pages
        )
        return workspace, text

    def test_english_workspace_and_pdf_are_fully_localized(self) -> None:
        workspace, text = self.render_workspace("en-US")
        proposal = (workspace / "proposal.md").read_text(encoding="utf-8")

        self.assertIn('language: "en-US"', proposal)
        self.assertIn("## 1. Executive Summary", proposal)
        self.assertIn("Recommended approach", text)
        self.assertIn("Document status", text)
        self.assertIn("Contents", text)
        self.assertIn("validation source", text)
        self.assertNotIn("[validation source]", text)
        self.assertNotIn("(references/source.md)", text)
        self.assertRegex(text, r"Page\s+\d+")
        self.assertNotIn("推荐方案", text)
        self.assertNotIn("目录", text)

        reader = PdfReader(str(workspace / "output" / "pdf" / "formal-plan.pdf"))
        uris: list[str] = []
        for page in reader.pages:
            for annotation_reference in page.get("/Annots", []):
                annotation = annotation_reference.get_object()
                action = annotation.get("/A")
                if action and action.get("/URI"):
                    uris.append(str(action.get("/URI")))
        self.assertIn("https://example.com/docs?a=1&b=2", uris)
        self.assertFalse(any(uri.startswith("file://") for uri in uris))

    def test_chinese_workspace_remains_backward_compatible(self) -> None:
        workspace, text = self.render_workspace("zh-CN")
        proposal = (workspace / "proposal.md").read_text(encoding="utf-8")

        self.assertIn('language: "zh-CN"', proposal)
        self.assertIn("## 1. 执行摘要", proposal)
        self.assertIn("推荐方案", text)
        self.assertIn("目录", text)

    def test_pdf_pages_and_contact_sheet_are_generated(self) -> None:
        workspace, _ = self.render_workspace("en-US")
        pdf = workspace / "output" / "pdf" / "formal-plan.pdf"
        pages_dir = workspace / "tmp" / "rendered-pages"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "render_pdf_pages.py"),
                str(pdf),
                "--output-dir",
                str(pages_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        page_images = sorted(pages_dir.glob("page-*.png"))
        self.assertEqual(len(page_images), len(PdfReader(str(pdf)).pages))

        contact_sheet = workspace / "tmp" / "contact-sheet.png"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "create_pdf_contact_sheet.py"),
                str(pages_dir),
                "--output",
                str(contact_sheet),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with Image.open(contact_sheet) as image:
            self.assertGreater(image.width, 500)
            self.assertGreater(image.height, 500)

    def test_rendered_pages_keep_numeric_order_after_page_nine(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        pdf = root / "twelve-pages.pdf"
        document = canvas.Canvas(str(pdf), pagesize=A4)
        for page in range(1, 13):
            shade = page / 13
            document.setFillColorRGB(shade, shade, shade)
            document.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
            document.showPage()
        document.save()

        pages_dir = root / "pages"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "render_pdf_pages.py"),
                str(pdf),
                "--output-dir",
                str(pages_dir),
                "--dpi",
                "72",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        center_values: list[int] = []
        for page_path in sorted(pages_dir.glob("page-*.png")):
            with Image.open(page_path).convert("RGB") as image:
                center_values.append(image.getpixel((image.width // 2, image.height // 2))[0])
        self.assertEqual(len(center_values), 12)
        self.assertEqual(center_values, sorted(center_values))


if __name__ == "__main__":
    unittest.main()
