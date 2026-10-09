# skills/base_skill.py
class BaseSkill:
    def __init__(self, pv_service):
        self.pv_service = pv_service
        self.name = self.__class__.__name__

    def init(self):
        pass

    def start(self):
        pass

    def execute(self):
        # 周期执行
        pass

    def stop(self):
        pass