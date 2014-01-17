from coordinate import RA,Dec

SH_TYPE='C'
STANDARD_TYPE='Z'
GUIDE_TYPE='G'
ACQUISITION_TYPE='A'
TARGET_TYPE='T'
SKY_TYPE='S'
GUIDEREF_TYPE='R'

class Target(object):
    def __init__(self, **kwargs):
        """ 
        hole should be a single hole or a list of holes with the primary hole first
        """
        self.ra=RA(kwargs.pop('ra',0.0))
        self.dec=Dec(kwargs.pop('dec',0.0))
        self.epoch=float(kwargs.pop('epoch',2000.0))
        self.pm_ra=kwargs.pop('pm_ra',0.0)
        self.pm_dec=kwargs.pop('pm_dec',0.0)
        self.id=kwargs.pop('id','')
        self.priority=float(kwargs.pop('priority',0.0))
        self.type=kwargs.pop('type','')
        self.field=kwargs.pop('field',None)

        hole=kwargs.pop('hole',None)
        if type(hole)==list:
            self.hole=hole[0]
            self.additional_holes=hole[1:]
        else:
            self.hole=hole
            self.additional_holes=[]
        
        self.user=kwargs.pop('user',{})
    
        self.conflicting=None
    
        if not self.is_sh:
            for h in self.holes():
                h.target=self
    
    def __str__(self):
        return '{} ({}, {}) type={}'.format(self.id,self.ra.sexstr,
                                         self.dec.sexstr,self.type)
    
    def holes(self):
        if self.hole:
            return [self.hole]+self.additional_holes
        else:
            return self.additional_holes

    @property
    def conflicting_ids(self):
        if not self.conflicting:
            return ''
        if type(self.conflicting)==type(self):
            return self.conflicting.id
        else:
            ret=[]
            for ct in self.conflicting:
                if ct.field:
                    ret.append('{}:{}'.format(ct.field.name, ct.id))
                else:
                    ret.append(ct.id)
            return ', '.join(ret)

    @property
    def info(self):
        """Does not include hole info"""
        ret={'id':self.id,
             'ra':self.ra.sexstr,
             'dec':self.dec.sexstr,
             'epoch':'{:6.1f}'.format(self.epoch),
             'priority':'{:.2f}'.format(self.priority),
             'type':self.type}
        if self.field:
            ret['field']=self.field.name
        if self.conflicting:
            ret['conflicts']=self.conflicting_ids

        ret.update(self.user)

        return ret

    @property
    def is_standard(self):
        return self.type==STANDARD_TYPE

    @property
    def is_sky(self):
        return self.type==SKY_TYPE

    @property
    def is_sh(self):
        return self.type==SH_TYPE

    @property
    def is_guide(self):
        return self.type==GUIDE_TYPE

    @property
    def is_target(self):
        return self.type==TARGET_TYPE

    @property
    def is_acquisition(self):
        return self.type==ACQUISITION_TYPE

