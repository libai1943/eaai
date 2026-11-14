"""Combine the 24 two-case vector plates and add a navigable index by model."""
from pathlib import Path
import subprocess
import tempfile
from PIL import Image
from pypdf import PdfReader, PdfWriter

root = Path(__file__).resolve().parents[1]
pages = root / "tmp/profile_pages"
def trim_vertical_margins(path):
    reader = PdfReader(path)
    if reader.metadata.get("/ProfileTrim") == "vertical":
        return
    page = reader.pages[0]
    with tempfile.TemporaryDirectory(dir=pages) as directory:
        preview = Path(directory)/"preview"
        subprocess.run(["pdftoppm","-png","-singlefile","-r","100",str(path),str(preview)],check=True)
        with Image.open(preview.with_suffix(".png")) as image:
            mask = image.convert("L").point(lambda v: 255 if v < 225 else 0)
            bounds = mask.getbbox()
            if not bounds:
                raise ValueError(f"Empty profile figure {path}")
            _, top, _, bottom = bounds
            height = float(page.mediabox.height)
            scale = height/image.height
            y0=max(0,(image.height-bottom)*scale-1.8)
            y1=min(height,(image.height-top)*scale+1.8)
            page.mediabox.lower_left=(0,y0)
            page.mediabox.upper_right=(float(page.mediabox.right),y1)
            page.cropbox=page.mediabox
        trimmed=PdfWriter()
        trimmed.add_page(page)
        trimmed.add_metadata({"/ProfileTrim":"vertical"})
        scratch=Path(directory)/"trimmed.pdf"
        with scratch.open("wb") as stream:
            trimmed.write(stream)
        scratch.replace(path)

for path in [root/"figures/profile_ground.pdf",root/"figures/profile_spatial.pdf",*sorted(pages.glob("profiles_*.pdf"))]:
    trim_vertical_margins(path)
writer = PdfWriter()
writer.add_metadata({"/Author":"Bai Li", "/Title":"RegionCovOpt: Best Accepted State and Control Profiles"})
families = ("Car parking", "Articulated docking", "Aerial vehicle", "Manipulator")
for n in range(24):
    reader = PdfReader(pages / f"profiles_{n+1:02d}.pdf")
    assert len(reader.pages) == 1
    writer.add_page(reader.pages[0])
    if n % 6 == 0:
        parent = writer.add_outline_item(families[n//6], n)
    first = 2 * (n % 6) + 1
    writer.add_outline_item(f"Cases {first:02d} and {first+1:02d}", n, parent=parent)
output = root / "output/pdf/RegionCovOpt_profiles.pdf"
with output.open("wb") as stream:
    writer.write(stream)
print("48 verified profiles in", len(PdfReader(output).pages), "vector pages")
