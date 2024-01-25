from smbus import SMBus
from typing import Union
import time

class PCA9685:
    # register address
    MODE1         = 0x00
    MODE2         = 0x01
    SUBADR1       = 0x02
    SUBADR2       = 0x03
    SUBADR3       = 0x04
    ALLCALLADR    = 0x05
    LED0_ON_L     = 0x06
    LED0_ON_H     = 0x07
    LED0_OFF_L    = 0x08
    LED0_OFF_H    = 0x09
    ALL_LED_ON_L  = 0xFA
    ALL_LED_ON_H  = 0xFB
    ALL_LED_OFF_L = 0xFC
    ALL_LED_OFF_H = 0xFD
    PRESCALE      = 0xFE
    TESTMODE      = 0xFF
    # register MODE1 mask
    MODE1_RESTART_MASK = 0x80
    MODE1_EXTCLK_MASK  = 0x40
    MODE1_AI_MASK      = 0x20
    MODE1_SLEEP_MASK   = 0x10
    MODE1_SUB1_MASK    = 0x08
    MODE1_SUB2_MASK    = 0x04
    MODE1_SUB3_MASK    = 0x02
    MODE1_ALLCALL_MASK = 0x01
    # register MODE2 mask
    MODE2_INVRT_MASK  = 0x10
    MODE2_OCH_MASK    = 0x08
    MODE2_OUTDRV_MASK = 0x04
    MODE2_OUTNE_MASK  = 0x03
    # register LEDn_ON_H LEDn_OFF_H mask
    LEDn_H_FULL_MASK  = 0x10
    LEDn_H_COUNT_MASK = 0x0F
    
    def __init__(self, bus=1, i2c_addr=0x40, ref_freq=25000000) -> None:
        self.bus = SMBus(bus)
        self.address = i2c_addr
        self.ref_freq = ref_freq
        self.write_buf = []
        self._frequency = 0
        self.reset()
        
    def reset(self) -> None:
        self._write_reg(self.MODE1, [0x00])

    def set_duty_cycle(self, channel, duty_cycle) -> None:
        channel_reg = self._get_channel_reg_addr(channel)
        reg_value = self._cal_on_off_value(duty_cycle)
        self._write_reg(channel_reg, reg_value)

    def get_duty_cycle(self, channel) -> float:
        channel_reg = self._get_channel_reg_addr(channel)
        reg_value = self._read_reg(channel_reg, 4)
        if reg_value[1] & self.LEDn_H_FULL_MASK:
            return 1.0
        elif reg_value[3] & self.LEDn_H_FULL_MASK:
            return 0.0
        else:
            on = reg_value[0] | (reg_value[1] << 8)
            off = reg_value[2] | (reg_value[3] << 8)
            return (off-on)/4096.0
        
    @property
    def frequency(self) -> int:
        return self._frequency

    @frequency.setter
    def frequency(self, value) -> None:
        ps = int(self.ref_freq / 4096.0 / value + 0.5)
        old_mode = self._read_reg(self.MODE1, 1)[0]
        self._write_reg(self.MODE1, [(old_mode & (~self.MODE1_RESTART_MASK)) | self.MODE1_SLEEP_MASK])  # Sleep
        self._write_reg(self.PRESCALE, [ps]) # Set prescale
        self._write_reg(self.MODE1, [old_mode]) # put it alive
        self._write_reg(self.MODE1, [old_mode|self.MODE1_AI_MASK]) # turn on auto increment
        self._frequency = value

    def __setitem__(self, key, value) -> None:
        if isinstance(key, slice):
            channel_reg = self._get_channel_reg_addr(key.start)
            reg_value = []
            if isinstance(value, float) or isinstance(value, int):
                for i in range(key.start, key.stop):
                    reg_value += self._cal_on_off_value(value)
            elif isinstance(value, list) or isinstance(value, tuple):
                for i in range(key.start, key.stop):
                    reg_value += self._cal_on_off_value(value[i])
            else:
                raise TypeError("{c} not supported to set duty cycle".format(c=type(value)))
            self._write_reg(channel_reg, reg_value)
        elif isinstance(key, tuple):
            if isinstance(value, float) or isinstance(value, int):
                for k in key:
                    self.set_duty_cycle(k, value)
            elif isinstance(value, list) or isinstance(value, tuple):
                for kv in zip(key, value):
                    self.set_duty_cycle(kv[0], kv[1])
            else:
                raise TypeError("{c} not supported to set duty cycle".format(c=type(value)))
        elif isinstance(key, int):
            if isinstance(value, float) or isinstance(value, int):
                self.set_duty_cycle(key, value)
            else:
                raise TypeError("{c} not supported to set duty cycle".format(c=type(value)))
        else:
            raise TypeError("key of " + str(type(key)) + " not supported")

    def __getitem__(self, key) -> Union[list,float]:
        if isinstance(key, slice):
            res = []
            for i in range(key.start, key.stop):
                res.append(self.get_duty_cycle(i))
        elif isinstance(key, tuple):
            res = []
            for k in key:
                res.append(self.get_duty_cycle(k))
        elif isinstance(key, int):
            res = self.get_duty_cycle(key)
        else:
            raise TypeError("key of " + str(type(key)) + " not supported")
        return res

    def _write_reg(self, reg, data) -> None:
        self.bus.write_i2c_block_data(self.address, reg, data)
        
    def _read_reg(self, reg, length) -> list:
        return self.bus.read_i2c_block_data(self.address, reg, length) 
    
    def _get_channel_reg_addr(self, channel) -> int:
        # Return LEDx_ON_L reg addr
        if channel > 15:
            raise RuntimeError(f"PCA9685 had only 16 channel, can't access channel {channel}")
        return self.LED0_ON_L + channel * 4
    
    def _cal_on_off_value(self, duty_cycle) -> list:
        int_cycle = int(duty_cycle*4096)
        if not(0 <= duty_cycle <= 4096):
            raise ValueError(f"Duty cycle value {duty_cycle} out of range, should be within 0.0 to 1.0")
        elif int_cycle == 0:
            return [0x00, 0x00, 0x00, self.LEDn_H_FULL_MASK]    # full off
        elif int_cycle == 4096:
            # return [0x00, self.LEDn_H_FULL_MASK, 0x00, 0x00]    # some problem with stemplus firmware, cant use full on mask
            return [0x00, 0x00, 0xFF, 0x0F]    # full on
        else:
            return [0x00, 0x00, int_cycle&0xFF, (int_cycle>>8)&0xF]
