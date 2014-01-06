import Plate
import glob
if __name__==__main__:
    files=glob.glob('*.asc')
    p=Plate.Plate()
    for f in files:
        p.load(f)
        for s in p.setups.keys():
            p.regionify(setup_number=s.split()[1])
        p.write_platefile()