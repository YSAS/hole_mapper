def write_drill(name, plate_holes, fields, dir='./'):

    file_fmt_str='{}{}_All_Holes_{}.txt'
    
    dicts=[d for f in fields for d in f.drillable_dictlist()]+plate_holes
    diams=set(d['d'] for d in dicts)
    
    for diam in diams:
        dicts_for_file=[d for d in dicts if d['d']==diam]
        with open(file_fmt_str.format(dir, name, diam),'w') as fp:

            recs=_dictlist_to_records(dicts_for_file, DRILLFILE_REQUIRED_COLS,
                                      required_only=True)
            for r in recs[1:]:
                fp.write(r)