from genericpath import isfile
import traitlets
from traitlets.config.configurable import Configurable, HasTraits
from .pca9685 import PCA9685
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