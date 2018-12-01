#!/usr/bin/env python
import plate
import numpy as np
import matplotlib.pyplot as plt
import dimensions
from matplotlib.patches import Circle
import argparse

def distinct_holes(this_plate, this_fields, other_plate, other_fields,
                   thresh=1e-5, retd=False):

    if type(this_fields) == str:
        this_fields = [this_fields]

    if type(other_fields) == str:
        other_fields = [other_fields]

    this_targ=[]
    for f in this_fields:
        this_targ.extend(plate.get_plate(this_plate).get_field(f).targets)
    other_targ=[]
    for f in other_fields:
        other_targ.extend(plate.get_plate(other_plate).get_field(f).targets)

    other_coord=[(t.ra,t.dec) for t in other_targ]

    mdist = lambda x,X: ((np.array(X)-x)**2).sum(1).min()

    ison_other = lambda t: mdist((t.ra,t.dec), other_coord)<thresh


    this_only=[t for t in this_targ if not ison_other(t)]

    if retd:
        d=np.array([mdist((t.ra,t.dec), other_coord) for t in this_targ])
        return this_only,d
    else:
        return this_only

def draw_fields(pax, plate, tag=True, tag_sky=True):

    colors={'T':'r','G':'g','S':'b','A':'g'}

    plt.sca(pax)
    plt.cla()

    for f in plate.fields:

        pax.add_patch(Circle((0,0),dimensions.PLATE_RADIUS,facecolor='w'))
        for t in f.all_targets:
            pax.add_patch(Circle((-t.hole.x,t.hole.y),t.hole.d/2.0,
                                 color=colors[t.type],fill=False))
            if tag:
                plt.text(-t.hole.x, t.hole.y, t.id)
            elif tag_sky and t.is_sky:
                plt.text(-t.hole.x, t.hole.y, t.id)
        # pax.set_xlim(-dimensions.PLATE_RADIUS,dimensions.PLATE_RADIUS)
        # pax.set_ylim(-dimensions.PLATE_RADIUS,dimensions.PLATE_RADIUS)


def parse_cl():
    parser = argparse.ArgumentParser(description='Plate Difference Tool',
                                     add_help=True,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--this', dest='this_plate', type=str,required=True,
                     help='This Plate')
    parser.add_argument('--other', dest='other_plate', type=str,required=True,
                        help='Other Plate')
    parser.add_argument('--tf', dest='this_fields', type=str,required=True,
                     help='Fields on this plate')
    parser.add_argument('--of', dest='other_fields', type=str,required=True,
                     help='Fields on this plate')
    parser.add_argument('-d', dest='thresh', type=float,default=0.2,
                     help='Same dist thresh in asec')

    return parser.parse_args()

if __name__ =='__main__':

    args=parse_cl()

    this_plate = args.this_plate
    other_plate = args.other_plate
    other_fields = args.other_fields.split()
    this_fields = args.this_fields.split()

    tag_sky=False

    thresh=args.thresh/3600

    fig, pax = plt.subplots()
    draw_fields(pax, plate.get_plate(this_plate), tag_sky=tag_sky)

    dist_this=distinct_holes(this_plate, this_fields,other_plate,other_fields)

    colors={'T':'r','G':'g','S':'b','A':'g'}
    for t in dist_this:
        pax.add_patch(Circle((-t.hole.x,t.hole.y),t.hole.d/2.0,
                             color=colors[t.type], fill=True))
    pax.set_xlim(-dimensions.PLATE_RADIUS,dimensions.PLATE_RADIUS)
    pax.set_ylim(-dimensions.PLATE_RADIUS,dimensions.PLATE_RADIUS)

    plt.show(1)

# this_plate='Ret2J15_Barium'
# this_fields=['ret2_Ba','ret2_Mg']
# other_plate='Ret2_Feb2016'
# other_fields='ret2_4205'
# tag_sky=False
# thresh= 2.7e-5 #.1 as
#
# fig, pax = plt.subplots()
# draw_fields(pax, plate.get_plate(this_plate), tag_sky=tag_sky)
#
#
# dist_this=distinct_holes(this_plate, this_fields,other_plate,other_fields,
#                          thresh=thresh)
#
# colors={'T':'r','G':'g','S':'b','A':'g'}
# for t in dist_this:
#     pax.add_patch(Circle((-t.hole.x,t.hole.y),t.hole.d/2.0,
#                          color=colors[t.type],fill=True))
# pax.set_xlim(-dimensions.PLATE_RADIUS,dimensions.PLATE_RADIUS)
# pax.set_ylim(-dimensions.PLATE_RADIUS,dimensions.PLATE_RADIUS)
#
#
#
# plt.show()

# hole_mapper/plotdistinct.py --this Ret2J15_Barium --other Ret2_Feb2016 --tf 'ret2_Ba ret2_Mg' --of ret2_4205