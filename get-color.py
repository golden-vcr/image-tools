import os
import sys

import cv2
import numpy as np
from colorthief import ColorThief

STARTING_TAPE_ID = 1
if len(sys.argv) > 1:
    STARTING_TAPE_ID = int(sys.argv[1])


def get_dominant_color(filename):
    thief = ColorThief(filename)
    return thief.get_color(quality=1)


def make_swatch(rgb, size):
    r, g, b = rgb
    swatch = np.zeros((size, size, 3), dtype=np.uint8)
    swatch[:] = (b, g, r)
    return swatch


def tohex(rgb):
    r, g, b = rgb
    return '#%02x%02x%02x' % (r, g, b)


i = STARTING_TAPE_ID
print('Dominant colors, starting at Tape ID: %d' % i)
while True:
    filename = 'storage/%04d_thumb.jpg' % i
    if not os.path.isfile(filename):
        print('Last Tape ID: %d' % (i - 1))
        break
    print(tohex(get_dominant_color(filename)))
    i += 1
