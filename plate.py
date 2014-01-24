
class Plate(object):
    def __init__(self, info_dict, plate_holes, fields):
        
        self.name=info_dict.pop('name')
        self.user=info_dict.copy()
        self.plate_holes=plate_holes
        self.fields={f.name:f for f in fields}





