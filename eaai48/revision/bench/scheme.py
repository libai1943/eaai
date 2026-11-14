"""Draw the integrated RegionCovOpt search loop as a vector flowchart."""
from math import atan2, cos, sin
from pathlib import Path

from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 526, 143


def arrow(pdf, points):
    path = pdf.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    pdf.setLineWidth(0.8)
    pdf.drawPath(path)
    (x0, y0), (x, y) = points[-2:]
    angle = atan2(y - y0, x - x0)
    head = pdf.beginPath()
    head.moveTo(x, y)
    for side in (-0.42, 0.42):
        head.lineTo(x - 5*cos(angle + side), y - 5*sin(angle + side))
    head.close()
    pdf.drawPath(head, fill=1, stroke=0)


def operation(pdf, x, y, width, title, detail):
    height = 36
    pdf.setFillGray(0.96)
    pdf.setLineWidth(0.75)
    pdf.rect(x, y, width, height, fill=1)
    pdf.setFillGray(0)
    center = x + width/2
    lines = [(title, "Helvetica-Bold", 9)] + [(line, "Helvetica", 8.3) for line in detail]
    baseline = y + height/2 + (len(lines)-1)*5.3 - 3
    for label, face, size in lines:
        assert pdf.stringWidth(label, face, size) <= width-6, label
        pdf.setFont(face, size)
        pdf.drawCentredString(center, baseline, label)
        baseline -= 10.6


def main():
    pdf = canvas.Canvas(str(ROOT/"figures/scheme.pdf"), pagesize=(WIDTH, HEIGHT), invariant=True)
    pdf.setTitle("Integrated global exploration and local search in RegionCovOpt")
    pdf.setAuthor("Bai Li")
    pdf.setStrokeGray(0)
    pdf.setFillGray(0)
    # The single enclosing frame contains both loop scales.
    pdf.setDash(3, 2)
    pdf.setLineWidth(0.65)
    pdf.rect(118, 4, 406, 136)
    pdf.setDash()
    pdf.setFillColorRGB(1, 0.76, 0)
    pdf.rect(125, 119, 392, 16, fill=1)
    pdf.setFillGray(0)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(131, 123, "Integrated global exploration and local search")

    operation(pdf, 2, 76, 97, "Initialize records", ["Evaluate stratified", "motion parameters"])
    operation(pdf, 127, 76, 107, "Select a region", ["Cyclic reservation or", "current best region"])
    operation(pdf, 255, 76, 125, "Generate one trial", ["Uniform refresh when due", "Else mean, poll or Gaussian"])
    operation(pdf, 401, 76, 115, "Assess the motion", ["Decode and rank by", "violation, then cost"])
    operation(pdf, 401, 12, 115, "Retain improvements", ["Update regional archive", "and global incumbent"])
    operation(pdf, 127, 12, 107, "Adapt the region", ["Use batch ranks if the", "parent count is met"])
    operation(pdf, 2, 12, 97, "Return result", ["Best feasible motion", "or failure with violation"])

    arrow(pdf, [(99, 94), (127, 94)])
    arrow(pdf, [(234, 94), (255, 94)])
    arrow(pdf, [(380, 94), (401, 94)])
    arrow(pdf, [(458.5, 76), (458.5, 48)])
    arrow(pdf, [(401, 38), (317.5, 38), (317.5, 76)])
    arrow(pdf, [(401, 23), (234, 23)])
    arrow(pdf, [(180.5, 48), (180.5, 76)])
    # Both initialization and a completed batch can exhaust the budget.
    pdf.line(127, 30, 109, 30)
    pdf.line(109, 30, 109, 60)
    pdf.line(109, 60, 43, 60)
    pdf.line(43, 76, 43, 60)
    arrow(pdf, [(43, 60), (43, 48)])
    pdf.setFont("Helvetica", 8)
    pdf.drawString(184, 60, "Next batch")
    pdf.drawString(321, 60, "Next slot")
    pdf.drawCentredString(317.5, 12, "Batch ends")
    pdf.drawString(46, 63, "Budget exhausted")
    pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    main()
