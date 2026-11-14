"""Arrange twelve existing MATLAB vector panels; preserve their original geometry and colors."""
import copy,io
from pathlib import Path
from pypdf import PdfReader,PdfWriter,Transformation
from pypdf.generic import RectangleObject
from reportlab.pdfgen.canvas import Canvas
R=Path(__file__).resolve().parents[1]
def main():
    selected={'parking':[2,5,9],'uav':[2,4,8],'arm':[2,4,9],'trailer':[4,8,11]}
    out=PdfWriter();sheet=out.add_blank_page(526,650)
    for row,(kind,ids) in enumerate(selected.items()):
        source=PdfReader(R/'figures'/f'{kind}.pdf').pages[0]
        for col,j in enumerate(ids):
            oldcol=(j-1)%3;oldrow=(j-1)//3
            # Original plate positions from bench/plots.m, in PDF points.
            left=oldcol*172.8+8;bottom=72*(7.43-2.21*oldrow)-13
            box=(left,bottom,left+170,bottom+157)
            page=copy.copy(source);page.cropbox=RectangleObject(box)
            sheet.merge_transformed_page(page,Transformation().translate(3+col*174-left,650-(row+1)*158-bottom),expand=False)
    buf=io.BytesIO();c=Canvas(buf,pagesize=(526,650));c.setFont('Times-Roman',7)
    c.setFillColorRGB(0,0,0);c.setFont('Times-Roman',7)
    c.setStrokeColorRGB(.02,.29,.51);c.line(47,624,64,624);c.drawString(69,621,'RegionCovOpt')
    c.setStrokeColorRGB(.72,.35,.16);c.setDash(1,2);c.line(47,614,64,614);c.setDash();c.drawString(69,611,'CMA-ES')
    c.setStrokeColorRGB(.3,.3,.3);c.rect(43,608,106,23,fill=0,stroke=1)
    c.save();buf.seek(0);sheet.merge_page(PdfReader(buf).pages[0])
    out.add_metadata({'/Title':'Representative MATLAB trajectory panels','/Author':'Bai Li'})
    out.write(R/'figures/representative.pdf')
if __name__=='__main__':main()
