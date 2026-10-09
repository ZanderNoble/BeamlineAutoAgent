# scheduler/skill_manager.py
import time

class SkillManager:
    def __init__(self, period=0.1):
        self.skills = []
        self.period = period
        self.running = True

    def add_skill(self, skill):
        self.skills.append(skill)

    def run_forever(self):
        for skill in self.skills:
            print(f"skillManager={skill}")
            skill.init()
            skill.start()

        while self.running:
            for skill in self.skills:
                skill.execute()
            time.sleep(self.period)