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
    buf=io.BytesIO();c=Canvas(buf,pagesize=(526,650))
    # Use the empty upper-left corner of P02 for a compact vertical key.
    c.setFillColorRGB(1,1,1);c.setStrokeColorRGB(.5,.5,.5);c.setLineWidth(.45)
    c.rect(32,599,82,36,fill=1,stroke=1);c.setFillColorRGB(0,0,0);c.setFont('Times-Roman',6.3)
    blue=(.02,.29,.51);orange=(.72,.35,.16)
    for y,label,color,dash in [(629,'Forward',blue,[]),(621,'Reverse',blue,[3,2]),(605,'CMA-ES',orange,[1,2])]:
        c.setStrokeColorRGB(*color);c.setLineWidth(1);c.setDash(dash);c.line(36,y,50,y)
        c.drawString(55,y-2,label)
    c.setDash();c.setStrokeColorRGB(*blue);c.setLineWidth(.7)
    diamond=c.beginPath();diamond.moveTo(43,615);diamond.lineTo(45,613);diamond.lineTo(43,611)
    diamond.lineTo(41,613);diamond.close();c.drawPath(diamond);c.drawString(55,611,'Gear change')
    c.save();buf.seek(0);sheet.merge_page(PdfReader(buf).pages[0])
    sheet.compress_content_streams()
    out.add_metadata({'/Title':'Representative MATLAB trajectory panels','/Author':'Bai Li'})
    out.write(R/'figures/representative.pdf')
if __name__=='__main__':main()
