from genericpath import isfile
import traitlets
from traitlets.config.configurable import Configurable
from pca9685 import PCA9685
from typing import Union
import os
import json

class Motor(Configurable):
    value = traitlets.Float()

    # config
    alpha = traitlets.Float(default_value=1.0).tag(config=True)
    beta = traitlets.Float(default_value=0.0).tag(config=True)

    def __init__(self, pca:PCA9685, a:int, b:int):
        self.pca = pca
        self.a = a
        self.b = b
        self.ab_continuous = ((b-a) == 1)

    def cal_ab(self, speed:Union[float,int]) -> list:
        value = min(max(speed*self.alpha+self.beta, -1.0), 1.0)
        if value > 0:
            return [0.0, value]
        else:
            return [-value, 0.0]
        
    @traitlets.observe('value')
    def _observe_value(self, change):
        pwm_value = self.cal_ab(change['new'])
        if self.ab_continuous:
            self.pca[self.a:self.b+1] = pwm_value
        else:
            self.pca[self.a, self.b] = pwm_value

class JetBot:
    def __init__(self, bus=1, motor_freq=1600, left_a=0, left_b=1, right_a=2, right_b=3) -> None:
        self.pca = PCA9685(bus=bus)
        self.pca.frequency = motor_freq
        self.left_motor = Motor(self.pca, left_a, left_b)
        self.right_motor = Motor(self.pca, right_a, right_b)
        self.lrab_continuous = ((left_a + 1) == left_b) and ((left_b + 1) == right_a) and ((right_a + 1) == right_b)
        if not os.path.isfile("./jetbot_conf.json"):
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
        self.set_motors(speed,-speed)

    def right(self, speed:Union[float,int]) -> None:
        self.set_motors(-speed,speed)

    def stop(self) -> None:
        self.set_motors(0,0)

    def release(self):
        self.stop()

    def load_conf(self):
        with open("./jetbot_conf.json") as f:
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
        with open("./jetbot_conf.json", 'w', encoding='utf-8') as f:
            json.dump(conf, f, ensure_ascii=False, indent=4)

class JetRacer:
    def __init__(self, bus=1, signal_freq=50) -> None:
        self.pca = PCA9685(bus=bus)
        self.pca.frequency = signal_freq