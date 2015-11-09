# File: encoder.py
# Scott M Baker, http://www.smbaker.com/

# Raspberry Pi Driver for the Sparkfun RGB Encoder (COM-10982 or COM-10984)

# Acknowledgements:
#    py-gaugette by Guy Carpenter, https://github.com/guyc/py-gaugette

import math
import threading
import time
import RPi.GPIO as IO

# pin numbers used when "main" is run (demo mode)
# GPIO
#   17 - encoder A via 10k resistor
#   27 - encoder B via 10k resistor
#
#   22 - encoder pin 3 (switch) via 10k resistor
#
#   14 - encoder pin 1 (red) via 270 ohm resistor
#   15 - encoder pin 2 (green) via 150 ohm resistor
#   18 - encoder pin 4 (blue) via 150 ohm resistor

Power
   GND - encoder C
   3.3V - encoder pin 5 (led/switch common)
ENCODER_PIN_A = 17
ENCODER_PIN_B = 27
ENCODER_PIN_SW = 22
ENCODER_PIN_R = 14
ENCODER_PIN_G = 15
ENCODER_PIN_BLU = 18

class BasicEncoder:
    # Just the encoder, no switch, no LEDs

    def __init__(self, a_pin, b_pin):
        self.a_pin = a_pin
        self.b_pin = b_pin

        IO.setmode(IO.BCM)
        IO.setup(self.a_pin, IO.IN, pull_up_down=IO.PUD_UP)
        IO.setup(self.b_pin, IO.IN, pull_up_down=IO.PUD_UP)

        self.last_delta = 0
        self.r_seq = self.rotation_sequence()

        self.steps_per_cycle = 4    # 4 steps between detents
        self.remainder = 0

    def rotation_sequence(self):
        a_state = IO.input(self.a_pin)
        b_state = IO.input(self.b_pin)
        r_seq = (a_state ^ b_state) | b_state << 1
        return r_seq

    # Returns offset values of -2,-1,0,1,2
    def get_delta(self):
        delta = 0
        r_seq = self.rotation_sequence()
        if r_seq != self.r_seq:
            delta = (r_seq - self.r_seq) % 4
            if delta==3:
                delta = -1
            elif delta==2:
                delta = int(math.copysign(delta, self.last_delta))  # same direction as previous, 2 steps

            self.last_delta = delta
            self.r_seq = r_seq

        return delta

    def get_cycles(self):
        self.remainder += self.get_delta()
        cycles = self.remainder // self.steps_per_cycle
        self.remainder %= self.steps_per_cycle # remainder always remains positive
        return cycles

    def get_switchstate(self):
        # BasicEncoder doesn't have a switch
        return 0

class SwitchEncoder(BasicEncoder):
    # Encoder with a switch

    def __init__(self, a_pin, b_pin, sw_pin):
        BasicEncoder.__init__(self, a_pin, b_pin)

        self.sw_pin = sw_pin
        IO.setup(self.sw_pin, IO.IN, pull_up_down=IO.PUD_DOWN)

    def get_switchstate(self):
        return IO.input(self.sw_pin)

class RGBEncoder(SwitchEncoder):
    # Encoder with a switch and LEDs

    COLOR_NAMES = ["red", "green", "blue"]

    def __init__(self, a_pin, b_pin, sw_pin, r_pin, g_pin, blu_pin):
        SwitchEncoder.__init__(self, a_pin, b_pin, sw_pin)

        self.color_pins = [r_pin, g_pin, blu_pin]
        IO.setup(self.color_pins[0], IO.OUT)
        IO.setup(self.color_pins[1], IO.OUT)
        IO.setup(self.color_pins[2], IO.OUT)

        self.color_servos=[]
        for i in range(0,3):
            servo = IO.PWM(self.color_pins[i], 50)
            servo.start(100)
            self.color_servos.append(servo)

    def get_switchstate(self):
        return IO.input(self.sw_pin)

    def set_color(self, color, v):
        self.color_servos[color].ChangeDutyCycle(100-v)

class EncoderWorker(threading.Thread):
    def __init__(self, encoder):
        threading.Thread.__init__(self)
        self.lock = threading.Lock()
        self.stopping = False
        self.encoder = encoder
        self.daemon = True
        self.delta = 0
        self.delay = 0.001
        self.lastSwitchState = False
        self.upEvent = False
        self.downEvent = False

    def run(self):
        self.lastSwitchState = self.encoder.get_switchstate()
        while not self.stopping:
            delta = self.encoder.get_cycles()
            with self.lock:
                self.delta += delta

                self.switchstate = self.encoder.get_switchstate()
                if (not self.lastSwitchState) and (self.switchstate):
                    self.upEvent = True
                if (self.lastSwitchState) and (not self.switchstate):
                    self.downEvent = True
                self.lastSwitchState = self.switchstate
            time.sleep(self.delay)

    # get_delta, get_upEvent, and get_downEvent return events that occurred on
    # the encoder. As a side effect, the corresponding event will be reset.

    def get_delta(self):
        with self.lock:
            delta = self.delta
            self.delta = 0
        return delta

    def get_upEvent(self):
        with self.lock:
            delta = self.upEvent
            self.upEvent = False
        return delta

    def get_downEvent(self):
        with self.lock:
            delta = self.downEvent
            self.downEvent = False
        return delta

    def set_color(self, color, v):
        self.encoder.set_color(color, v)

def switch_demo():
    value = 0

    encoder = EncoderWorker(SwitchEncoder(ENCODER_PIN_A, ENCODER_PIN_B, ENCODER_PIN_SW))
    encoder.start()

    while 1:
        delta = encoder.get_delta()
        if delta!=0:
            value = value + delta
            print "value", value

        if encoder.get_upEvent():
            print "up!"

        if encoder.get_downEvent():
            print "down!"

def rgb_demo():
    A_PIN  = 0
    B_PIN  = 2
    SW_PIN = 3

    value = 0
    toggle = False

    colors = [0,0,0]
    index = 0

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
            print "color", RGBEncoder.COLOR_NAMES[index], "value", colors[index]
            encoder.set_color(index, colors[index])

        if encoder.get_upEvent():
            print "up!"
            index = (index + 1) % 3

        if encoder.get_downEvent():
            print "down!"

if __name__ == "__main__":
    rgb_demo()

