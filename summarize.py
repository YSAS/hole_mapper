#! /usr/bin/env python
import glob
import argv


def write_summary_file(sfile, platefiles):
    tlist=[]
    platerec='{name:<10} {ns:<2}\n'
    setuprec='     {name:<11} {ra:<11} {de:<11} '
             '{epoch:<6} {sidereal_time:<10} {airmass:<4} {n:<3}\n'
    with open(sfile,'w') as fp:
        for f in platefiles:
            try:
                p=Plate(f)
                if p.file_version()=='0.1':
                    raise Exception("Can't process v0.1")
            except Exception, e:
                print 'Platefile Error: {}'.format(e)
                    continue

            fp.write(platerec.format(name=p.name, ns=p.n_setups))

            for sname, setup in p.setups.iteritems():
                fp.setuprec.format(setup.attrib)
                tlist.append(setup.attrib)
    return tlist

def write_target_list(tfile, recs):
    """rec iterable of dicts with 'name' 'ra', 'de', & 'epoch'"""
    with open(tfile,'w') as fp:
        obsfmt='{n:<3} {id:<15} {ra:<11} {de:<11} {eq:<6} {pmRA:<4} {pmDE:<4} '
        '{irot:<3} {rotmode:<4} {gra1:<11} {gde1:<11} {geq:<6} '
        '{gra2:<11} {gde2:<11} {geq2:<6}'
        header=obsfmt.format(n='#',
        id='ID',
        ra='RA',
        de='DE',
        eq='Eq',
        pmRA='pmRA',
        pmDE='pmDE',
        irot='Rot'
        rotmode='Mode',
        gra1='GRA1',
        gde1='GDE1',
        gra2='GRA2',
        gde2='GDE2',
        geq2='GEQ2',
        geq1='GEQ1')
        
        fp.write(header+'\n')
        obsfmt='{n:<3} {id:<15} {ra:<11} {de:<11} {eq:<6} {pmRA:<5.2f} '
        '{pmDE:<5.2f} {irot:<3} {rotmode:<4} {gra1:<11} {gde1:<11} {geq:<6} '
        '{gra2:<11} {gde2:<11} {geq2:<6}'
        for i,r in enumerate(recs):
            s=obsfmt.format(n=i+1,
            id=r['name'].replace(' ', '_'),
            ra=sexiegesmal_fmt(r['ra'],ra=True),
            de=sexiegesmal_fmt(r['de']),
            eq=r['epoch'],
            pmRA=0,
            pmDE=0,
            irot='7.2'
            rotmode='EQU',
            gra1=sexiegesmal_fmt(0),
            gde1=sexiegesmal_fmt(0),
            gra2=sexiegesmal_fmt(0),
            gde2=sexiegesmal_fmt(0),
            geq2=0,
            geq1=0)
            fp.write(s+'\n')



def sexiegesmal_fmt(n, ra=False):
    if type(n)==str:
        if ':' in n:
            return n
        else:
            return ':'.join(n.split())
    if type(n) in [tuple, list]:
        return ':'.join([str(x) for x in n])
    if type(n)==float:
        if ra:
            sec=3600*n/15.0
            hord=int(sec)/3600
            m=int(sec % 3600)/60
            secs=(sec % 3600) % 60
        else:
            hord=int(n)
            m=int((n-hord)*60)
            secs=(n-hord-m*60)*60
        return '{}:{}:{:.1f}'.format(hord,m,secs)
    raise ValueError

if __name__ == '__main__':

    fname=sys.argv[1]
    sfile=fname+'_summ.txt'
    tfile=fname+'_tlist.txt'
    files = glob.glob('*.plate')
    
    trec=write_summary_file(sfile, files)
    write_target_list(tfile, trec)
