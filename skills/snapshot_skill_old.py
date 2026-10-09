# skills/snapshot_skill.py
from .base_skill import BaseSkill
import sqlite3
import time
import os
from datetime import datetime

class SnapshotSkill(BaseSkill):
    def __init__(self, config):
        super().__init__(config)
        self.name = "SnapshotSkill"
        self.db_file = "pv_snapshots.db"
        self.default_dir = "./export"
        os.makedirs(self.default_dir, exist_ok=True)

        # PV 句柄（在 execute 中读取）
        self.pv_modeName = "BL_ID:logical:modeName"
        self.pv_saveTrig = "BL_ID:logical:saveTrig"
        self.pv_saveStatus = "BL_ID:logical:saveStatus"
        self.pv_exportDir = "BL_ID:logical:exportDir"
        self.pv_exportTrig = "BL_ID:logical:exportTrig"
        self.pv_actionDir = "BL_ID:logical:actionDir"
        self.pv_actionStatus = "BL_ID:logical:actionStatus"
        self.pv_actionTrig = "BL_ID:logical:actionTrig"

    def init(self):
        self._init_db()
        print(f"✅ [{self.name}] 初始化完成（数据库已就绪）")

    def start(self):
        print(f"✅ [{self.name}] 已启动")

    def execute(self):
        save_trig = self.pv_service.get(self.pv_saveTrig)
        if save_trig == 1:
            self._handle_save()

        export_trig = self.pv_service.get(self.pv_exportTrig)
        if export_trig == 1:
            self._handle_export()

        action_trig = self.pv_service.get(self.pv_actionTrig)
        if action_trig == 1:
            self._handle_action()

    def _init_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        all_pvs = self.pv_service.get_all()
        table_columns = ["name TEXT PRIMARY KEY", "timestamp TEXT NOT NULL"]

        for i in range(1, len(all_pvs) + 1):
            table_columns.append(f"PV{i}_name TEXT")
            table_columns.append(f"PV{i}_value REAL")

        create_sql = f'''
        CREATE TABLE IF NOT EXISTS pv_table (
            {", ".join(table_columns)}
        );
        '''
        c.execute(create_sql)
        conn.commit()
        conn.close()

    def _handle_save(self):
        key = self.pv_service.get(self.pv_modeName)
        data = self.pv_service.get_all()

        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        fields = ["name", "timestamp"]
        for i in range(1, len(data) + 1):
            fields += [f"PV{i}_name", f"PV{i}_value"]

        values = [key, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        for k, v in data.items():
            values += [k, v]

        sql = f"REPLACE INTO pv_table ({','.join(fields)}) VALUES ({','.join(['?'] * len(fields))})"
        c.execute(sql, values)
        conn.commit()
        conn.close()

        self.pv_service.put(self.pv_saveStatus, 1)
        self.pv_service.put(self.pv_saveTrig, 0)
        print(f"✅ [{self.name}] 已保存快照: {key}")

    def _handle_export(self):
        export_dir = self.pv_service.get(self.pv_exportDir) or self.default_dir
        os.makedirs(export_dir, exist_ok=True)
        time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(export_dir, f"snapshot_{time_str}.txt")

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pv_table")
        rows = cursor.fetchall()
        conn.close()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"PV快照导出 | {datetime.now()}\n\n")
            for row in rows:
                key = row[0]
                ts = row[1]
                f.write(f"[{key}] {ts}\n")
                idx = 2
                while idx < len(row):
                    pv_name = row[idx]
                    pv_val = row[idx+1]
                    f.write(f"  {pv_name:<30} = {pv_val}\n")
                    idx += 2
                f.write("-"*50 + "\n")

        self.pv_service.put(self.pv_exportTrig, 0)
        print(f"✅ [{self.name}] 导出成功: {filepath}")

    def _handle_action(self):
        target_key = self.pv_service.get(self.pv_actionDir)
        if not target_key:
            self.pv_service.put(self.pv_actionTrig, 0)
            return

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pv_table WHERE name=?", (target_key,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            self.pv_service.put(self.pv_actionStatus, -1)
            self.pv_service.put(self.pv_actionTrig, 0)
            return

        idx = 2
        while idx < len(row):
            pv_name = row[idx]
            pv_val = row[idx+1]
            if pv_name:
                self.pv_service.put(pv_name, pv_val)
            idx += 2

        self.pv_service.put(self.pv_actionStatus, 1)
        self.pv_service.put(self.pv_actionTrig, 0)
        print(f"✅ [{self.name}] 已恢复快照: {target_key}")

    def stop(self):
        print(f"🛑 [{self.name}] 已停止")
