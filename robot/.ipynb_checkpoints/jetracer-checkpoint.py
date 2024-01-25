from genericpath import isfile
import traitlets
from traitlets.config.configurable import Configurable, HasTraits
from .pca9685 import PCA9685
from .motor import Servo
from typing import Union
import os
from pathlib import Path
import json

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