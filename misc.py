'''
Created on Dec 12, 2009

@author: one
'''
from Hole import *
import ImageCanvas
from plateHoleInfo import plateHoleInfo
import operator
import Cassette
import os.path

def distribute(x, min_x, max_x, min_sep):
    """
    Adjust x such that all x are min_space apart,
    near original positions, and within min_x & max_x
    """
    import numpy as np
    return np.linspace(min_x, max_x, len(x))



def nanfloat(s):
    """Convert string to float or nan if can't"""
    try:
        return float(s)
    except Exception:
        return float('nan')

        def rangify(data):
    from itertools import groupby
    from operator import itemgetter
    str_list = []
    for k, g in groupby(enumerate(data), lambda (i,x):i-x):
        ilist = map(itemgetter(1), g)
        if len(ilist) > 1:
            str_list.append('%d-%d' % (ilist[0], ilist[-1]))
        else:
            str_list.append('%d' % ilist[0])
    return ', '.join(str_list)


def hyphen_range(s):
    """ yield each integer from a complex range string like "1-9,12, 15-20,23"
    
    >>> list(hyphen_range('1-9,12, 15-20,23'))
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 15, 16, 17, 18, 19, 20, 23]
    
    >>> list(hyphen_range('1-9,12, 15-20,2-3-4'))
    Traceback (most recent call last):
    ...
    ValueError: format error in 2-3-4
    """
    for x in s.split(','):
        elem = x.split('-')
        if len(elem) == 1: # a number
            yield int(elem[0])
        elif len(elem) == 2: # a range inclusive
            start, end = map(int, elem)
            for i in xrange(start, end+1):
                yield i
        else: # more than one hyphen
            raise ValueError('format error in %s' % x)
