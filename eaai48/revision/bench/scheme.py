"""Vector diagram of the implemented search loop."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
R=Path(__file__).resolve().parents[1]
def main():
 c=canvas.Canvas(str(R/"figures/scheme.pdf"),pagesize=(502,129));navy=HexColor("#254962");gray=HexColor("#536574")
 def box(x,y,w,h,title,sub):
    c.setFillColor(HexColor("#f3f6f7"));c.setStrokeColor(navy);c.roundRect(x,y,w,h,3,fill=1,stroke=1)
    c.setFillColor(navy);c.setFont("Times-Bold",10);c.drawCentredString(x+w/2,y+h-15,title);c.setFont("Times-Roman",9);c.drawCentredString(x+w/2,y+8,sub)
 def arrow(points):
    from math import atan2,cos,sin
    c.setStrokeColor(gray);c.setFillColor(gray);c.setLineWidth(.9)
    for a,b in zip(points,points[1:]):c.line(*a,*b)
    a,b=points[-2:];v=atan2(b[1]-a[1],b[0]-a[0]);p=c.beginPath();p.moveTo(*b);p.lineTo(b[0]-6*cos(v-.43),b[1]-6*sin(v-.43));p.lineTo(b[0]-6*cos(v+.43),b[1]-6*sin(v+.43));p.close();c.drawPath(p,fill=1)
 c.translate(0,-44)
 box(3,131,148,38,"Boundary states and map","Evaluate stratified candidates")
 box(176,131,145,38,"Select region","Reserved or incumbent region")
 box(346,131,136,38,"Propose one trial","Mean, poll, refresh or Gaussian")
 box(346,48,136,38,"Decode and rank","Update incumbent and archive")
 box(176,48,145,38,"Update region","Mean, paths, covariance, scale")
 box(3,48,148,38,"Report search outcome","Best admissible motion or failure")
 arrow([(151,150),(176,150)]);arrow([(321,150),(346,150)]);arrow([(421,131),(421,86)]);arrow([(346,66),(321,66)]);arrow([(176,66),(151,66)])
 arrow([(247,86),(247,131)]);c.setFillColor(gray);c.setFont("Times-Italic",8);c.drawString(251,106,"budget remains")
 arrow([(482,67),(495,67),(495,151),(482,151)])
 c.drawCentredString(162,74,"stop")
 c.saveState();c.translate(492,106);c.rotate(90);c.drawCentredString(0,0,"next slot");c.restoreState()
 c.showPage();c.save()
if __name__=="__main__":main()

