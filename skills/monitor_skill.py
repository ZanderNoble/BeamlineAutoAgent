# skills/monitor_skill.py
from skills.base_skill import BaseSkill
from IOC.pvObjectCreator import PVObjectCreator
from IOC.pv_monitor import SmartPVMonitor
import time

class MonitorSkill(BaseSkill):
    def __init__(self, pv_list,ioc_server):
        super().__init__(self)
        self.pv_list = pv_list
        self.monitor_started = False
        self.name = "MonitorSkill"
        self.period = 0.1
        self.ioc_server = ioc_server
        self.objectCreator = PVObjectCreator(self.pv_list, self.period)
        self.monitor = SmartPVMonitor(self.objectCreator, self.period)

    def init(self):
        print(f"✅ [{self.name}] 初始化完成")

    def start(self):
        self.objectCreator.create_pv_objects()
        self.objectCreator.start_rbv_collect()
        print(f"✅ [{self.name}] 已启动")

    def execute(self):
        """
        周期执行：
        让 PV 缓存保持最新，
        不写业务、不写判断、只做采集！
        """
        if not self.monitor_started:
            self.monitor.start_background()
            self.monitor_started = True

    def stop(self):
        self.monitor.stop_background()
        print(f"🛑 [{self.name}] 已停止")

'''
class MonitorSkill(BaseSkill):
    def __init__(self, pv_service, monitor_pv_list):
        super().__init__(pv_service)
        self.monitor_pv_list = monitor_pv_list
        self.name = "MonitorSkill"

    def init(self):
        print(f"✅ [{self.name}] 初始化完成")

    def start(self):
        print(f"✅ [{self.name}] 已启动")

    def execute(self):
        """
        周期执行：
        让 PV 缓存保持最新，
        不写业务、不写判断、只做采集！
        """
        for monitor in self.monitor_pv_list:
            monitor.update_cache()

    def stop(self):
        print(f"🛑 [{self.name}] 已停止")
'''