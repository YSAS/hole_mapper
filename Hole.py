'''
Created on Dec 12, 2009

@author: J Bailey
'''
import math

SKY_TYPE='S'
OBJECT_TYPE='O'

class Hole(dict):
    def __init__(self, x, y, r, ra=(0,0,0.0), de=(0,0,0.0),
                 id='',color=0.0, mag=0.0, type='',
                 ep=2000.0, mattfib='', extra='', idstr=''):
        self.x=float(x)
        self.y=float(y)
        self.radius=float(r)
        self.idstr=idstr
        self.hash=self.__hash__()
        
        self['RA']=ra
        self['DEC']=de
        self['ID']=id
        self['COLOR']=color
        self['MAGNITUDE']=mag
        self['TYPE']=type
        self['EPOCH']=ep
        self['MATTFIB']=mattfib
        self['EXTRA']=extra
        
    def __eq__(self,other):
        return (self.x == other.x and
                self.y == other.y and
                self.radius == other.radius)
   
    def __hash__(self):
        return ( "%2.3f.%2.3f.%2.3f" % (self.x,self.y,self.radius) ).__hash__()
    
    def __str__(self):
        return self.idstr
    
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

    def isSky(self):
        return self['TYPE']==SKY_TYPE

    def isObject(self):
        return self['TYPE']==OBJECT_TYPE