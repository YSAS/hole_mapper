'''
Created on Dec 12, 2009

@author: J Bailey
'''
import math
import Cassette
import operator
SKY_TYPE='S'
OBJECT_TYPE='O'

class Hole(dict):
    def __init__(self, x, y, z, r, ra=('0','0','0.0'), de=('0','0','0.0'),
                 type='', slit=180, ep=2000.0, mattfib='', idstr='',
                 fiber='', cassette=None, fiberno=0, **extra):
        
        #cassette 0 not specified, 1-8
        #fiber num 0 not specified 1-16
        #channel R or B
        #fiber R-channel-fiberno
        self.x=float(x)
        self.y=float(y)
        self.z=float(z)
        self.radius=float(r)
        self.idstr=idstr #this is the string that defines the hole in the asc file
        self.cassette_distances={c:self.distance(Cassette.cassette_positions[c])
                                 for c in Cassette.cassette_positions}
        self.hash=self.__hash__()
        
        assert slit in (180, 125, 95, 75, 58, 45)

        #ID processing
        if type=='S':
            id='sky'+extra.pop('ID','')
        else:
            id=extra.pop('ID',':'.join(ra)+'_'+':'.join(de))
        
        #oops
        from __builtin__ import type as python_type
        #ra & dec processing
        if python_type(ra)==str:
            ra=tuple([x for x in ra.split()])
        if python_type(de)==str:
            de=tuple([x for x in de.split()])

        color=extra.pop('COLOR',0.0)
        mag=extra.pop('MAGNITUDE',0.0)
        priority=extra.pop('priority',0)
        
        self['USER_ASSIGNED']= fiber!=''
        self['RA']=ra
        self['DEC']=de
        self['ID']=id
        self['COLOR']=color
        self['MAGNITUDE']=mag
        self['TYPE']=str(type)
        self['EPOCH']=float(ep)
        self['MATTFIB']=str(mattfib)
        self['SLIT']=int(slit)
        self['PRIORITY']=int(priority)
        self['FIBER']=str(fiber)
        if fiber:
            cassette,_,fiberno=fiber.partition('-')
            fiberno=int(fiberno)
            if fiberno >8:
                cassette+='h'
            else:
                cassette+='l'
        self['ASSIGNMENT']={'CASSETTE':cassette, #cassette or list of viable cassettes e.g. R1, B8
                            'FIBERNO':fiberno}
        self['CUSTOM']=extra #keys and values should be strings!
        for k,v in extra.iteritems():
            if k not in self:
                self[k]=v
            else:
                raise ValueError('Key {} is reserved'.format(k))
        
    
    def __eq__(self,other):
        return (self.x == other.x and
                self.y == other.y and
                self.radius == other.radius)
   
    def __hash__(self):
        return ( "%2.6f.%2.6f.%2.6f" % (self.x,self.y,self.radius) ).__hash__()
    
    def __str__(self):
        return self.idstr
    
    def getInfo(self):
        return ("%.6f %.6f %.6f"%(self.x,self.y,self.radius),"RA DEC",self.idstr)

    def maprecord(self):
        return ''.join([self['FIBER'],'  ',self.idstr])

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
    
    def assign(self, assignment):
        """
        assignemnt={'CASSETTE':'','FIBERNO':0} 
        removes the h or l from cassette
        """
        self['FIBER']=(assignment['CASSETTE'][0:2]+
                       '-{:02}'.format(assignment['FIBERNO']))
        self['ASSIGNMENT']=assignment

    def unassign(self):
        """assignemnt={'CASSETTE':'','FIBERNO':0}"""
        if self['USER_ASSIGNED']==True:
            raise Exception('User assignments are irrevocable')
        self['FIBER']=''
        self['ASSIGNMENT']={'CASSETTE':None,'FIBERNO':0}
        
    def assigned_cassette(self):
        """Return name of assigned cassette or ''"""
        if type(self['ASSIGNMENT']['CASSETTE'])==str:
            return self['ASSIGNMENT']['CASSETTE']
        else:
            return ''

    def assign_possible_cassette(self, cassettes,
                                 update_with_intersection=False):
        """
        Add cassettes to the list of possible cassettes usable with hole.
        If update_with_intersection is set, intersection of cassettes 
        cand previously set possible cassettes is used as the set of 
        possibles
        """
        if type(cassettes)!=list:
            raise TypeError('casssettes must be a list of cassette names')
        if self['FIBER']!='':
            raise Exception('Fiber already assigned')
        if type(self['ASSIGNMENT']['CASSETTE'])==str:
            raise Exception('Cassette already assigned')
#        if self.__hash__()==190951225552046123:
#            if not hasattr(self, 'foobar'):
#                self.foobar=[(cassettes,self['ASSIGNMENT']['CASSETTE'])]
#            if self.foobar[-1]!=cassettes:
#                self.foobar.append((cassettes,self['ASSIGNMENT']['CASSETTE']))
#            if len(cassettes)==0:
#                import pdb;pdb.set_trace()
        #If no possibles have ever been set, set and finish
        if self['ASSIGNMENT']['CASSETTE']==None:
            self['ASSIGNMENT']['CASSETTE']=cassettes
            return

        #Otherwise update the list of possibles
        current=self['ASSIGNMENT']['CASSETTE']
        if update_with_intersection:
            new=list(set(current).intersection(cassettes))
        else:
            new=list(set(current).union(cassettes))

        self['ASSIGNMENT']['CASSETTE']=new

    def assign_cassette(self, cassette):
        """
        Set the cassette (e.g. 'R3') which can be used for fiber selection
        """
        if self['FIBER']!='':
            raise Exception('Fiber already assigned')
        if type(cassette)!=str:
            raise TypeError('casssette must be a sting')
        self['ASSIGNMENT']['CASSETTE']=cassette

    def nearest_usable_cassette(self):
        """Return nearest usable cassette"""
        if type(self['ASSIGNMENT']['CASSETTE'])==str:
            return self['ASSIGNMENT']['CASSETTE']
        
        usable=[(c,self.cassette_distances[c])
                 for c in self['ASSIGNMENT']['CASSETTE']]
        
        return min(usable, key=operator.itemgetter(1))[0]
    
    def plug_priority(self):
        """
        Return number indicating if hole should be assigned a fiber sooner
        or later (lower)
        """
        if type(self['ASSIGNMENT']['CASSETTE'])==str:
            return 0.0 #Don't care, we've already been assigned to a cassette
        else:
            return sum([self.cassette_distances[c]
                        for c in self['ASSIGNMENT']['CASSETTE']])

    def isAssignable(self, cassette=None):
        """
        True iff hole can be (re)assigned, optionally to sppecified cassette
        """
        ret=self['USER_ASSIGNED']==False
        if cassette:
            ret&=cassette.slit==self['SLIT']
        return ret
    
    def isAssigned(self):
        return self['FIBER']!=''

    def ra_string(self):
        return '{} {} {}'.format(*self['RA'])

    def de_string(self):
        return '{} {} {}'.format(*self['DEC'])

    def assigned_color(self):
        """ Return color of assigned cassette else None """
        if type(self['ASSIGNMENT']['CASSETTE'])==str:
            if 'R' in self['ASSIGNMENT']['CASSETTE']:
                return 'red'
            else:
                return 'blue'
        else:
            return None

    def isSky(self):
        return self['TYPE']==SKY_TYPE

    def isObject(self):
        return self['TYPE']==OBJECT_TYPE

