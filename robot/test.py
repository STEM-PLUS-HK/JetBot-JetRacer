from genericpath import isfile
import traitlets
from traitlets.config.configurable import Configurable, HasTraits
from typing import Union
import os
from pathlib import Path
import json
import time
from jetcard.menu import Menu, FloatVariable, IntVariable, BoolVariable, Function, reset_menu
from typing import Union
from .jetbot import JetBot
from .jetracer import JetRacer

jetbot = JetBot()
jetracer = JetRacer()

# JetBot test case
def test_jetbot_motor(func_obj: Function) -> Union[bool, None]:
    func_obj.callback_print("test motor after 5 sec")
    func_obj.callback_print("make sure wheels")
    func_obj.callback_print("not touching anything")
    time.sleep(5)
    func_obj.callback_print("going forward...")
    jetbot.forward(0.5)
    time.sleep(1)
    func_obj.callback_print("going backward...")
    jetbot.backward(0.5)
    time.sleep(1)
    func_obj.callback_print("going leftward...")
    jetbot.left(0.5)
    time.sleep(1)
    func_obj.callback_print("going rightward...")
    jetbot.right(0.5)
    time.sleep(1)
    jetbot.forward(0)
    return True

def test_jetbot(func_obj: Function) -> Union[bool, None]:
    func_obj.callback_print("factory test start")
    test_jetbot_motor(func_obj)
    func_obj.callback_print("factory test done")
    return False

# JetRacer test case
def test_jetracer_servo(func_obj: Function) -> Union[bool, None]:
    func_obj.callback_print("steer left now...")
    jetracer.steering = -1.0
    time.sleep(1)
    func_obj.callback_print("steer right now...")
    jetracer.steering = 1.0
    time.sleep(1)
    func_obj.callback_print("steer mid now...")
    jetracer.steering = 0.0
    time.sleep(1)
    return True

def test_jetracer_motor(func_obj: Function) -> Union[bool, None]:
    func_obj.callback_print("test throttle after 5 sec")
    func_obj.callback_print("make sure wheels")
    func_obj.callback_print("not touching anything")
    time.sleep(5)
    func_obj.callback_print("going forward now...")
    jetracer.throttle = 0.2
    time.sleep(5)
    jetracer.throttle = 0.0
    time.sleep(1)
    func_obj.callback_print("going backward now...")
    jetracer.throttle = -0.5
    time.sleep(5)
    func_obj.callback_print("stop now...")
    jetracer.throttle = 0.0
    time.sleep(1)
    return True

def test_jetracer(func_obj: Function) -> Union[bool, None]:
    func_obj.callback_print("factory test start")
    test_jetracer_servo(func_obj)
    test_jetracer_motor(func_obj)
    func_obj.callback_print("factory test done")
    return False

if __name__ == '__main__':
    factory_test_menu = Menu(description="factory test")
    factory_jetbot_menu = Menu(description="JetBot", root=factory_test_menu)
    factory_jetbot_test = Function(callback_func=test_jetbot, root=factory_jetbot_menu, description="Test JetBot")
    factory_jetracer_menu = Menu(description="JetRacer", root=factory_test_menu)
    factory_jetracer_test = Function(callback_func=test_jetracer, root=factory_jetracer_menu, description="Test JetRacer")
    while True:
        time.sleep(100)