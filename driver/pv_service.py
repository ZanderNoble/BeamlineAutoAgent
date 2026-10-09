# driver/pv_service.py
import epics
from IOC.new_motor import ModeMotor

class PVService:
    def __init__(self, monitor):
        self.monitor = monitor

    def get(self, pv_name):
        return self.monitor.pv_values.get(pv_name)

    def put(self, pv_name, value, wait=False):
        epics.caput(pv_name, value, wait=wait)

    def get_all(self):
        return self.monitor.pv_values.copy()