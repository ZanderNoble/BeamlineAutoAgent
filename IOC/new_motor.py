from _testcapi import error
from caproto.server import PVGroup, pvproperty, run
from caproto.server.records import MotorFields
from epics import Motor as BaseEpicsMotor
import threading
import time

class MotorWithError(PVGroup):
    error = pvproperty(value=0, dtype=int, name='.error', doc="0=OK 1=ERROR")

    def __init__(self, prefix, *, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc

class ModeMotor(BaseEpicsMotor):
    _extras = {
        "disabled": "_able.VAL",
        "error": ".error"  # <-- 直接加在这里
    }
    def __init__(self, name=None,timeout=3.0):
        super().__init__(name, timeout=timeout)
        self.set_callback(attr="error", callback=self._on_error)

    def _on_error(self, value, **kwargs):
        if value == 1 and self.get('MOVN') == 1:
            print(f"[错误] 电机 {self._prefix}.error = 1")
            print(f"[停止] 已自动停机")
            self.stop()
    def check_hard_limits(self):
        """ check motor limits:
        returns None if no limits are violated
        raises expection if a limit is violated"""
        for field, msg in (('HLS',  'High hard limit violation'),
                           ('LLS',  'Low  hard limit violation')):
            if self.get(field) != 0:
                raise super().MotorLimitException(msg)
        return

    def is_move_complete(self):
        """ 判断电机是否运动完成，同时处理超时情况，考虑软闭环机制 """
        time.sleep(0.1)
        pre_moving_status = self.get('MOVN')
        print(f'is_moving_complete={pre_moving_status}')
        if pre_moving_status == 1:
            while True:
                moving_status = self.get('MOVN')
                if self.get('URIP') == 1:
                    # 获取闭环死区、当前次数和最大次数
                    deadband = self.get("RDBD")
                    retry_count = self.get('RCNT')
                    retry_max_count = self.get('RTRY')
                    if abs(self.get('RBV') - self.get('VAL')) <= deadband:
                        return True
                    else:
                        if retry_count > retry_max_count+1:
                            return True
                elif moving_status==0:
                    return True
                time.sleep(0.1)
        else:
            return True

    def tweak_limit(self, direction='forward', wait=False, timeout=300.0):
        """ move the motor by the tweak_val until hard limit is violated
        takes optional args:
         direction    direction of motion (forward/reverse)  [forward]
                         must start with'rev' or 'back' for a reverse tweak.
         wait         wait for move to complete before returning (T/F) [F]
         timeout      max time for move to complete (in seconds) [300]
        """
        start_time = time.time()
        ifield = 'TWF'
        if direction.startswith('rev') or direction.startswith('back'):
            ifield = 'TWR'
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError("Operation timed out before reaching the limit")
            stat = self.put(ifield, 1, wait=wait, timeout=timeout)
            if wait:
                self.is_move_complete()
            ret = stat
            if stat == 1:
                ret = 0
            if stat == -2:
                ret = -1
            try:
                #self.check_hard_limits()
                self.check_limits()
                break
            except super().MotorLimitException:
                continue
        try:
            self.check_limits()
        except super().MotorLimitException:
            ret = -1
        return ret

    def home(self, direction='forward', wait=False, timeout=300.0):
        """ Move the motor to the home position based on the direction.
        takes optional args:
         direction    direction of motion (forward/reverse)  [forward]
                         must start with'rev' or 'back' for a reverse home.
         wait         wait for move to complete before returning (T/F) [F]
         timeout      max time for move to complete (in seconds) [300]
        """
        ifield = 'HOMF'
        if direction.startswith('rev') or direction.startswith('back'):
            ifield = 'HOMR'
        stat = self.put(ifield, 1, wait=wait, timeout=timeout)
        ret = stat
        if stat == 1:
            ret = 0
        if stat == -2:
            ret = -1
        return ret
'''
class ModeMotor(BaseEpicsMotor):
    _extras = {
        "disabled": "_able.VAL",
        "error": ".error"
    }
    def __init__(self, name=None, timeout=3.0):
        super().__init__(name, timeout=timeout)
        self.set_callback(attr="error", callback=self._on_error)
        self._rules = []
        self._stop_monitor = threading.Event()
        

    def _on_error(self, value, **kwargs):
        if value == 1:
            print(f"[错误] 电机 {self._prefix}.error = 1 → 自动停止")
            self.stop()

    def rule(self, func):
        self._rules.append(func)
        return func

    def check_all_rules(self):
        for rule_func in self._rules:
            try:
                rule_func()
            except Exception as e:
                print(f"\n[规则违反] {e}")
                print(f"[紧急停止] {self.name}\n")
                self.stop()
                raise

    def _monitor_loop(self):
        while not self._stop_monitor.is_set() and self.moving:
            self.check_all_rules()
            time.sleep(0.02)

    def move(self, position, wait=False, **kwargs):
        print(f"\n[{self.name}] 移动 → {position}（自带规则检查）")
        self._stop_monitor.clear()
        monitor = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor.start()
        try:
            return super().move(position, wait=wait, **kwargs)
        finally:
            self._stop_monitor.set()
            monitor.join()
'''