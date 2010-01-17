'''
Created on Dec 12, 2009

@author: J Bailey
'''
import math
class Hole:
    def __init__(self, x, y, r, idstr=''):
        self.x=float(x)
        self.y=float(y)
        self.radius=float(r)
        self.idstr=idstr
        self.hash=Hole.computeHash(self.x, self.y, self.radius)

    def __eq__(self,other):
        return (self.x == other.x and
                self.y == other.y and
                self.radius == other.radius)
   
    def __hash__(self):
        return self.hash
    
    def getInfo(self):
        return ("%.3f %.3f %.3f"%(self.x,self.y,self.radius),"RA DEC",self.idstr)
    
    def holeCompareX(self,other):
        return cmp(self.x,other.x)

    def holeCompareY(self,other):
        return cmp(self.y,other.y)

    def inRegion(self,(x0,y0,x1,y1)):
        ret=False
        if x0 > x1:
            left=x1
            right=x0
        else:
            left=x0
            right=x1
        if y0 > y1:
            bottom=y1
            top=y0
        else:
            bottom=y0
            top=y1
        if left<=self.x:
            if bottom<=self.y:
                if right>=self.x:
                    if top>=self.y:
                        ret=True
        return ret

    def distance(self,(x,y)):
        return math.hypot(self.x-x,self.y-y)

    def edgeDistance(self,(x,y)):
        return math.hypot(self.x-x,self.y-y)-self.radius
    
    def position(self):
        return (self.x,self.y)

    def draw(self,canvas,color=None,fcolor='White',radmult=1.0):
        hashtag=".%i"%self.hash
        if canvas.find_withtag(hashtag):
            print "drawing dupe"
            print (self.position(),self.radius,self.hash)
            fcolor='DarkGreen'
        canvas.drawCircle( self.position(), self.radius*radmult, 
                             outline=color, fill=fcolor, tags=('hole',hashtag),
                             activefill='Green',activeoutline='Green',
                             disabledfill='Orange',disabledoutline='Orange')
        
    @staticmethod
    def computeHash(x,y,r):
        return ( "%2.3f.%2.3f.%2.3f" % (x,y,r) ).__hash__()
