from genericpath import isfile
import traitlets
from traitlets.config.configurable import Configurable, HasTraits
from .pca9685 import PCA9685
from .motor import Motor
from typing import Union
import os
from pathlib import Path
import json

class JetBot:
    def __init__(self, bus=1, motor_freq=1600, left_a=0, left_b=1, right_a=2, right_b=3) -> None:
        self.pca = PCA9685(bus=bus)
        self.pca.frequency = motor_freq
        self.left_motor = Motor(self.pca, left_a, left_b)
        self.right_motor = Motor(self.pca, right_a, right_b)
        self.lrab_continuous = ((left_a + 1) == left_b) and ((left_b + 1) == right_a) and ((right_a + 1) == right_b)
        self.conf_path = str(Path.home()) + "/jetbot_conf.json"
        if not os.path.isfile(self.conf_path):
            self.right_motor.alpha = -1
            self.save_conf()
        else:
            self.load_conf()

    def set_motors(self, left_speed:Union[float,int], right_speed:Union[float,int]) -> None:
        if self.lrab_continuous:
            left_pwm = self.left_motor.cal_ab(left_speed)
            right_pwm = self.right_motor.cal_ab(right_speed)
            self.pca[self.left_motor.a:self.right_motor.b+1] = left_pwm + right_pwm
        else:
            self.left_motor.value = left_speed
            self.right_motor.value = right_speed

    def forward(self, speed:Union[float,int]) -> None:
        self.set_motors(speed, speed)

    def backward(self, speed:Union[float,int]) -> None:
        self.set_motors(-speed, -speed)

    def left(self, speed:Union[float,int]) -> None:
        self.set_motors(-speed,speed)

    def right(self, speed:Union[float,int]) -> None:
        self.set_motors(speed,-speed)

    def stop(self) -> None:
        self.set_motors(0,0)

    def release(self):
        self.stop()

    def load_conf(self):
        with open(self.conf_path) as f:
            conf = json.load(f)
            self.left_motor.alpha = conf['left_motor']['alpha']
            self.left_motor.beta = conf['left_motor']['beta']
            self.right_motor.alpha = conf['right_motor']['alpha']
            self.right_motor.beta = conf['right_motor']['beta']

    def save_conf(self):
        conf = {
            'left_motor':{
                'alpha': self.left_motor.alpha,
                'beta': self.left_motor.beta
            },
            'right_motor':{
                'alpha': self.right_motor.alpha,
                'beta': self.right_motor.beta
            }
        }
        with open(self.conf_path, 'w', encoding='utf-8') as f:
            json.dump(conf, f, ensure_ascii=False, indent=4)
