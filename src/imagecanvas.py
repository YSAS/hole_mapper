import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import math

class ImageCanvas():
    def __init__(self, width, height, units_hwidth, units_hheight):
    
        #http://www.pythonware.com/library/pil/handbook/imagedraw.htm for ref
        #create a new image filled black
        self.mult=4
	self.lwid=int(self.mult+3)

        self.default_color='White'
        self.finishedSize=(width,height) 
        self.image=Image.new("RGB", (self.mult*width, self.mult*height))
        self.draw = ImageDraw.Draw(self.image)
        
        self.centerx=self.mult*float(width)/2.0
        self.centery=self.mult*float(height)/2.0

        self.scalex=self.centerx/units_hwidth
        self.scaley=self.centery/units_hheight
        
        
    def save(self, file):
	import ImageFilter
	im=self.image.filter(ImageFilter.SMOOTH)
	im=im.resize(self.finishedSize,Image.ANTIALIAS)
        im.save(file)


    def clear(self):
        pass


    def setupColors(self, outline, fill):
    
        c=[self.default_color, None]
        if outline:
            c[0]=outline
        if fill:
            c[1]=fill
        
        return c

    #assumes that canvas coord scaling is same in both x and y dimensions
    def drawCircle(self, (x,y), r, fill=None, outline=None, width=None):
        
        # Get the coordinates 
        p1=( self.canvasCoordx(x-r),
             self.canvasCoordy(y-r) )
        p2=( self.canvasCoordx(x+r),
             self.canvasCoordy(y+r) )
        if p1[0] > p2[0]:
            l=[p2,p1]
        else:
            l=[p1,p2]
                
        #Sort out coloring
        col=self.setupColors(outline, fill)

        self.draw.ellipse(l, outline=col[0], fill=col[1])


    #x,y are at center len is length of side
    def drawSquare(self, (x,y), len, outline=None, fill=None, width=None):
    
        # Get the coordinates
        x0=self.canvasCoordx(x-len/2.)
        y0=self.canvasCoordy(y-len/2.)
        x1=self.canvasCoordx(x+len/2.)  
        y1=self.canvasCoordy(y+len/2.)
        
        #Sort out coloring
        col=self.setupColors(outline, fill)
        
        self.draw.rectangle((x0,y0,x1,y1), outline=col[0], fill=col[1])
        

    # x0,y0 is one corner, x1,y1 is corner diagonally across
    def drawRectangle(self, (x0,y0,x1,y1), outline=None, fill=None):
    
        # Get the coordinates
        x0c=self.canvasCoordx(x0)
        y0c=self.canvasCoordy(y0)
        x1c=self.canvasCoordx(x1)  
        y1c=self.canvasCoordy(y1)
        
        #Sort out coloring
        col=self.setupColors(outline, fill)
        
        #From docs: Note that the second coordinate pair 
        # defines a point just outside the rectangle, also
        # when the rectangle is not filled.
        # Not sure if this will be an issue
        self.draw.rectangle((x0c,y0c,x1c,y1c), outline=col[0], fill=col[1])

    ##takes either (x0,y0), (x1,y1)  or (x,y), r,theta
    def drawLine(*args, **kw):
        if 'fill' not in kw:
            fill=None
        else:
            fill=kw['fill']
        assert len(args) == 3 or len(args) == 4
        self=args[0]
        
        # Get the coordinates
        pos0 = args[1]
        if len(args) == 3:
            pos1 = args[2]
        else:
            l = args[2]
            th = args[3]
            x2=pos0[0]+l*math.cos(math.radians(th))
            y2=pos0[1]+l*math.sin(math.radians(th))
            pos1=(x2,y2)
            
        x0c=self.canvasCoordx(pos0[0])
        y0c=self.canvasCoordy(pos0[1])
        x1c=self.canvasCoordx(pos1[0])
        y1c=self.canvasCoordy(pos1[1])
        
        #Sort out coloring
        col=self.setupColors(fill, None)
        
        self.draw.line((x0c,y0c,x1c,y1c), fill=col[0],width=self.lwid)


    # x,y is at upper left corner of text unless center is set to 1
    def drawText(self,(x,y), text, color=None,center=0):

        # Get the coordinates
        xc=self.canvasCoordx(x)
        yc=self.canvasCoordy(y)

	thefont=ImageFont.truetype("/Library/Fonts/Arial.ttf", 48)

	if center:
	    tmp=thefont.getsize(text)
	    xc-=tmp[0]/2.0
	    yc-=tmp[0]/2.0

        #Sort out coloring
        col=self.setupColors(color, None)

        self.draw.text((xc,yc), text, fill=col[0], font=thefont)
        
    def getTextSize(self,text):
        wid,ht=self.draw.textsize(text)
        return ( self.inputCoordx(wid)-self.inputCoordx(0), 
                 self.inputCoordy(ht)-self.inputCoordy(0) )

    # go from coordinates with 0,0 at center to 0,0 at upper left
    def canvasCoordx(self, x):
        return round(-self.scalex*x+self.centerx)


    def canvasCoordy(self, y):
        return round(-self.scaley*y + self.centery)

    def inputCoordx(self, x):
        return (self.centerx-x)/self.scalex

    def inputCoordy(self, y):
        return (self.centery-y)/self.scaley

