#!/usr/bin/env python
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons
from matplotlib.patches import Circle
import plate
import dimensions
import numpy as np
import argparse
import ipdb
import os.path

def parse_cl():
    parser = argparse.ArgumentParser(description='Plate Display Tool',
                                     add_help=True,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
                                     
    parser.add_argument('file', metavar='FILE', type=str,
                     help='Plate file to show')
                     
    parser.add_argument('-t', dest='tag', default=False,
                        action='store_true', required=False,
                        help='Print IDs by holes')
    parser.add_argument('--ts', dest='tag_sky', default=False,
                    action='store_true', required=False,
                    help='Print IDs by holes')
    return parser.parse_args()

def draw_field(pax, fname, plate, args):
    
    colors={'T':'r','G':'g','S':'b','A':'g'}
    
    f={f.name:f for f in plate.fields}[fname]
    
    plt.sca(pax)
    plt.cla()
    
    pax.add_patch(Circle((0,0),dimensions.PLATE_RADIUS,facecolor='w'))
    for t in f.all_targets:
        pax.add_patch(Circle((t.hole.x,t.hole.y),t.hole.d/2.0,
                             color=colors[t.type]))
        if args.tag:
            plt.text(t.hole.x, t.hole.y, t.id)
        elif args.tag_sky and t.is_sky:
            plt.text(t.hole.x, t.hole.y, t.id)
    pax.set_xlim(-dimensions.PLATE_RADIUS,dimensions.PLATE_RADIUS)
    pax.set_ylim(-dimensions.PLATE_RADIUS,dimensions.PLATE_RADIUS)
    plt.show()


if __name__ =='__main__':

    args=parse_cl()
    p=plate.load_dotplate(args.file)
    
    
    fieldnames=[f.name for f in p.fields]

    fig, pax = plt.subplots()
    plt.subplots_adjust(left=0.3)

    rax = plt.axes([0.05, 0.7, 0.15, 0.15], axisbg='lightgoldenrodyellow')
    radio = RadioButtons(rax, fieldnames)
    radio.on_clicked(lambda label: draw_field(pax, label, p, args))
    plt.show(1)

