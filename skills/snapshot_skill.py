# skills/snapshot_skill.py
from caproto.commandline import monitor

from skills.base_skill import BaseSkill
from IOC.snapshotSkillMapping import SnapshotSkillMapping
class SnapshotSkill(BaseSkill):
    def __init__(self, config,monitor_example):
        super().__init__(config)
        self.name = "SnapshotSkill"
        self.config = config
        self.monitor=monitor_example
        self.snapshot = SnapshotSkillMapping(self.config, self.monitor)

    def init(self):
        print(f"✅ [{self.name}] 初始化完成（数据库已就绪）")

    def start(self):
        print(f"✅ [{self.name}] 已启动")

    def execute(self):
        self.snapshot.execute()


    def stop(self):
        print(f"🛑 [{self.name}] 已停止")
