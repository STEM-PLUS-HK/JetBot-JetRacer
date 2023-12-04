from genericpath import isfile
import traitlets
from traitlets.config.configurable import Configurable, HasTraits
from pca9685 import PCA9685
from typing import Union
import os
from pathlib import Path
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

class Servo(HasTraits):
    value = traitlets.Float()

    def __init__(self, pca:PCA9685, channel:int, min_width:int=750, center_width:int=1500, max_width:int=2250):
        # min_width and max_width unit in microsecond
        self.pca = pca
        self.channel = channel
        self._cal_alpha_beta(pca.frequency, min_width, center_width, max_width)

    def cal_duty_cycle(self, pos:Union[float,int]) -> float:
        if pos > 0:
            return min(max(pos*self.alpha0+self.beta, self.min_duty_cycle), self.max_duty_cycle)
        else:
            return min(max(pos*self.alpha1+self.beta, self.min_duty_cycle), self.max_duty_cycle)
    
    def reverse_output(self):
        temp = self.alpha0
        self.alpha0 = -self.alpha1
        self.alpha1 = -temp
        
    @traitlets.observe('value')
    def _observe_value(self, change):
        self.pca[self.channel] = self.cal_duty_cycle(change['new'])

    def _cal_alpha_beta(self, freq:int, min_width:int, center_width:int, max_width:int):
        # Get the period in microsecond from freq
        period = 1000000 / freq
        self.min_duty_cycle = min_width / period
        self.center_duty_cycle = center_width / period
        self.max_duty_cycle = max_width / period
        self.alpha0 = self.max_duty_cycle - self.center_duty_cycle
        self.alpha1 = self.center_duty_cycle - self.min_duty_cycle
        self.beta = self.center_duty_cycle

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
        self.set_motors(speed,-speed)

    def right(self, speed:Union[float,int]) -> None:
        self.set_motors(-speed,speed)

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

class JetRacer(HasTraits):
    steering = traitlets.Float()
    throttle = traitlets.Float()

    def __init__(self, bus=1, signal_freq=50, servo_channel=0, motor_channel=1) -> None:
        self.pca = PCA9685(bus=bus)
        self.pca.frequency = signal_freq
        self.servo = Servo(self.pca, servo_channel)
        self.motor = Servo(self.pca, motor_channel)
        self.conf_path = str(Path.home()) + "/jetracer_conf.json"
        if not os.path.isfile(self.conf_path):
            self.save_conf()
        else:
            self.load_conf()

    @traitlets.observe('steering')
    def _observe_steering(self, change):
        self.servo.value = change['new']

    @traitlets.observe('throttle')
    def _observe_throttle(self, change):
        self.motor.value = change['new']
    
    def stop(self) -> None:
        self.servo.value = 0
        self.motor.value = 0

    def load_conf(self):
        with open(self.conf_path) as f:
            conf = json.load(f)
            self.servo.alpha0 = conf['servo']['alpha0']
            self.servo.alpha1 = conf['servo']['alpha1']
            self.servo.beta = conf['servo']['beta']
            self.servo.min_duty_cycle = conf['servo']['min_duty']
            self.servo.max_duty_cycle = conf['servo']['max_duty']
            self.motor.alpha0 = conf['motor']['alpha0']
            self.servo.alpha1 = conf['servo']['alpha1']
            self.motor.beta = conf['motor']['beta']
            self.motor.min_duty_cycle = conf['motor']['min_duty']
            self.motor.max_duty_cycle = conf['motor']['max_duty']

    def save_conf(self):
        conf = {
            'servo':{
                'alpha0': self.servo.alpha0,
                'alpha1': self.servo.alpha1,
                'beta': self.servo.beta,
                'min_duty': self.servo.min_duty_cycle,
                'max_duty': self.servo.max_duty_cycle
            },
            'motor':{
                'alpha0': self.motor.alpha0,
                'alpha1': self.motor.alpha1,
                'beta': self.motor.beta,
                'min_duty': self.motor.min_duty_cycle,
                'max_duty': self.motor.max_duty_cycle
            }
        }
        with open(self.conf_path, 'w', encoding='utf-8') as f:
            json.dump(conf, f, ensure_ascii=False, indent=4)