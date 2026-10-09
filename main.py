from pip._internal.commands import check

from driver.pv_service import PVService
from skills.monitor_skill import MonitorSkill
from skills.snapshot_skill import SnapshotSkill
from scheduler.skill_manager import SkillManager
from IOC.new_allPV import IOCServer
from IOC.pv_monitor import SmartPVMonitor
from IOC.snapshotSkillMapping import SnapshotSkillMapping
import time
from IOC.pvObjectCreator import PVObjectCreator
PV_CONFIG = [("IOC:m1", "motor"), ("IOC:m2", "motor"),("IOC:m3", "motor"),("IOC:m4", "ai")]

if __name__ == "__main__":
    # 1. 启动 IOC
    server = IOCServer(
        logical_prefix="BL_ID:",
        motor_prefix="IOC:",
        logical_list=["logical1:",'logical2:'],
        motor_list=["m1", "m2"])
    server.start_background()


    Snapshot_Config = {
        "Logical1_DB": {
            "DB_Name": "pv_snapshots.db",
            "Table_Name": "Logical1",
            "DB_Dir": "./export"
        },
        "Logical1_PVs": {
            "modeName": "BL_ID:logical:modeName",
            "saveTrig": "BL_ID:logical:saveTrig",
            "saveStatus": "BL_ID:logical:saveStatus",
            "exportDir": "BL_ID:logical:exportDir",
            "exportTrig": "BL_ID:logical:exportTrig",
            "exportStatus": "BL_ID:logical:exportStatus",
            "actionDir": "BL_ID:logical:actionDir",
            "actionStatus": "BL_ID:logical:actionStatus",
            "actionTrig": "BL_ID:logical:actionTrig"
        },
        "Logical1_Control_PVs": {
            "IOC:m1", "IOC:m2"
        },
        "Logical1_Action":{
            "operation": [
                ["IOC:m4", "check", 1],
                ["IOC:m1", "fwdLim", True],
                ["IOC:m2", "revLim", True],
                ["IOC:m1", "pos", False],
                ["IOC:m2", 5, True],
                ["IOC:m2", "pos", False]
            ]
        },
        "Logical2_DB": {
            "DB_Name": "pv_snapshots.db",
            "Table_Name": "Logical2",
            "DB_Dir": "./export"
        },
        "Logical2_PVs": {
            "modeName": "BL_ID:logical2:modeName",
            "saveTrig": "BL_ID:logical2:saveTrig",
            "saveStatus": "BL_ID:logical2:saveStatus",
            "exportDir": "BL_ID:logical2:exportDir",
            "exportTrig": "BL_ID:logical2:exportTrig",
            "exportStatus": "BL_ID:logical2:exportStatus",
            "actionDir": "BL_ID:logical2:actionDir",
            "actionStatus": "BL_ID:logical2:actionStatus",
            "actionTrig": "BL_ID:logical2:actionTrig"
        },
        "Logical2_Control_PVs": {
            "IOC:m1", "IOC:m3"
        }
    }
    manager = SkillManager(period=0.1)

    skill=MonitorSkill(PV_CONFIG,server)
    manager.add_skill(skill)

    skill1 = SnapshotSkill(Snapshot_Config,skill.monitor)
    manager.add_skill(skill1)

    manager.run_forever()
