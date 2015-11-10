import spidev
import sys
import time

from vfd import *
from encoder import *

def color_str(i, cursor):
    COLOR_NAMES = ["red", "grn", "blu"]
    if (i==cursor):
        return COLOR_NAMES[i].upper()
    else:
        return COLOR_NAMES[i].lower()

def vfd_update(vfd, index, colors):
            vfd.setPosition(0,0)
            vfd.writeStr("%s:%3d %s:%3d" %
                         (color_str(0,index), colors[0],
                          color_str(1,index), colors[1]))
            vfd.setPosition(0,1)
            vfd.writeStr("%s:%3d" %
                          (color_str(2,index), colors[2]))

def main():
    vfd = VFD(0,0)
    vfd.cls()

    toggle = False

    colors = [0,0,0]
    index = 0

    vfd_update(vfd, index, colors)

    encoder = EncoderWorker(RGBEncoder(ENCODER_PIN_A,
                                       ENCODER_PIN_B,
                                       ENCODER_PIN_SW,
                                       ENCODER_PIN_R,
                                       ENCODER_PIN_G,
                                       ENCODER_PIN_BLU))
    encoder.start()

    while 1:
        delta = encoder.get_delta()
        if delta!=0:
            colors[index] = min(100, max(0, colors[index] + delta))

            vfd_update(vfd, index, colors)

            print "color", RGBEncoder.COLOR_NAMES[index], "value", colors[index]
            encoder.set_color(index, colors[index])

        if encoder.get_upEvent():
            print "up!"
            index = (index + 1) % 3

            vfd_update(vfd, index, colors)

        if encoder.get_downEvent():
            print "down!"


if __name__ == "__main__":
    main()
