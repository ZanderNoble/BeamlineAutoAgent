import sqlite3
import os
import json
from datetime import datetime
from typing import List

from epics.autosave.save_restore import pv_value

'''
DataBase设计,传递参数为DB
表global_mode_table_mapping：id(主键),数据库名字，数据库存储地址，表的名字，模式的名字，对应的pv列表，创造时间，更新时间。
表2：
'''
class SnapshotSkillDB:
    def __init__(self, config):
        self.config = config
        self.grouped_configs = self._group_configs()
        self.master_table_name = 'global_tableName_mapping_modeName'
        self.create_database_and_master_table()

    def _group_configs(self):
        grouped = {}
        for key, value in self.config.items():
            if key.endswith('_DB'):
                db_name = value['DB_Name']
                table_name = value['Table_Name']
                db_dir = value['DB_Dir']
                grouped[table_name] = {
                    'DB': {
                        'DB_Name': db_name,
                        'DB_Dir': db_dir
                    }
                }
            elif table_name is not None and key.startswith(table_name):
                parts = key.split('_')
                if parts[-1] == 'PVs' and parts[-2] == table_name:
                    if 'PVs' not in grouped[table_name]:
                        grouped[table_name]['PVs'] = {}
                    #print(f"{table_name}即将更新的 PVs 数据: {value}")
                    grouped[table_name]['PVs'].update(value)
                    print(f"{table_name}已经更新的 PVs 数据: {grouped[table_name]['PVs']}")
                if parts[-1] == 'PVs' and parts[-2] == 'Control' and parts[-3] == table_name:
                    if 'Control_PVs' not in grouped[table_name]:
                        grouped[table_name]['Control_PVs'] = []
                    #print(f"{table_name}即将更新的 Control_PVs 数据: {value}")
                    if isinstance(value, set):
                        value = sorted(list(value))
                    if isinstance(value, list):
                        grouped[table_name]['Control_PVs'].extend(value)
                    elif isinstance(value, dict):
                        for v in value.values():
                            if isinstance(v, list):
                                grouped[table_name]['Control_PVs'].extend(v)
                            else:
                                grouped[table_name]['Control_PVs'].append(v)
                    else:
                        grouped[table_name]['Control_PVs'].append(value)
                    print(f"{table_name}已经更新的 Control_PVs 数据: {grouped[table_name]['Control_PVs']}")
                if parts[-1] == 'Action':
                    print(f"value={value}")
                    if 'operationAction' not in grouped[table_name]:
                        grouped[table_name]['operationAction'] = []
                    action_list = value.get('operation')
                    if isinstance(action_list, list):
                        for sublist in action_list:
                            if isinstance(sublist, list) and len(sublist) == 3:
                                pv, operation, wait = sublist
                                grouped[table_name]['operationAction'].append((pv, operation, wait))
                            else:
                                print(f"Warning: Element in action is not a list of length 3: {sublist}")
                    else:
                        print(f"Warning: action is not a list: {action_list}")
                    print(f"{table_name}已经更新的 operationAction 数据: {grouped[table_name]['operationAction']}")

        return grouped

    def create_master_table(self, db_file):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.master_table_name}'")
            table_exists = cursor.fetchone()
            if not table_exists:
                create_master_table_sql = f'''
                CREATE TABLE IF NOT EXISTS {self.master_table_name} (
                    table_name TEXT,
                    mode_name TEXT,
                    db_name TEXT,
                    db_dir TEXT,
                    create_time TEXT,
                    modify_time TEXT,
                    operation TEXT,
                    PRIMARY KEY (table_name, mode_name)
                )
                '''
                cursor.execute(create_master_table_sql)
                print(f"主映射表 {self.master_table_name} 创建成功")
            else:
                print(f"主映射表 {self.master_table_name} 已存在")
            conn.close()
        except sqlite3.Error as e:
            print(f"创建主映射表 {self.master_table_name} 时出错: {e}")

    def create_business_table(self, db_file, table_name):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            table_exists = cursor.fetchone()
            if not table_exists:
                control_pvs = self.grouped_configs[table_name].get('Control_PVs', [])
                column_parts = []
                for i, pv in enumerate(control_pvs, 1):
                    column_name = f'pv{i}_name TEXT'
                    column_value = f'pv{i}_value TEXT'
                    column_parts.append(column_name)
                    column_parts.append(column_value)
                columns_sql = ', '.join(column_parts)
                create_table_sql = f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    table_name TEXT,
                    mode_name TEXT,
                    {columns_sql},
                    time TEXT,
                    operation TEXT,
                    PRIMARY KEY (mode_name)
                )
                '''
                cursor.execute(create_table_sql)
                print(f"业务表 {table_name} 创建成功")
            else:
                print(f"业务表 {table_name} 已存在")
            conn.close()
        except sqlite3.Error as e:
            print(f"创建业务表 {table_name} 时出错: {e}")

    def create_database_and_master_table(self):
        for table_name, config in self.grouped_configs.items():
            db_name = config['DB']['DB_Name']
            db_dir = config['DB']['DB_Dir']
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir)
                except OSError as e:
                    print(f"创建目录 {db_dir} 失败: {e}")
                    continue
            db_file = os.path.join(db_dir, db_name)
            try:
                conn = sqlite3.connect(db_file)
                print(f"数据库 {db_name} 创建成功")
                self.create_master_table(db_file)
                self.create_business_table(db_file, table_name)
                conn.close()
            except sqlite3.Error as e:
                if "unable to open database file" in str(e):
                    print(f"创建数据库 {db_name} 时可能存在权限问题，路径: {db_file}")
                else:
                    print(f"创建数据库 {db_name} 时出错: {e}")

    def write_data(self, data):
        print(f"write_data={data}")
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for table_name, config in self.grouped_configs.items():
            db_name = config['DB']['DB_Name']
            db_dir = config['DB']['DB_Dir']
        db_file = os.path.join(db_dir, db_name)
        table_name = data.get('table_name')
        mode_name = data.get('mode_name')
        if not table_name or not mode_name:
            print("传入数据缺少 table_name 或 mode_name")
            return False
        control_pvs = self.grouped_configs[table_name].get('Control_PVs', [])
        if not control_pvs:
            print(f"业务表 {table_name} 无 Control_PVs 配置")
            return False

        incoming_pv = {k: v for k,v in data.items() if k not in ['table_name', 'mode_name']}
        control_pvs = self.grouped_configs[table_name].get('Control_PVs', [])
        if set(incoming_pv.keys()) != set(control_pvs):
            print(f"传入PV与业务表 {table_name} 的Control_PVs不匹配！")
            return False

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        try:
            conn.execute('BEGIN')
            cursor.execute(f"SELECT * FROM {self.master_table_name} WHERE table_name =? AND mode_name =?",
                           (table_name, mode_name))
            existing_record = cursor.fetchone()
            print(f"existing_record={existing_record}")
            if existing_record:
                cursor.execute(f"UPDATE {self.master_table_name} SET modify_time=?,operation=? WHERE table_name=? and mode_name =?",
                               (current_time,'modify',table_name,mode_name))
                update_table_columns = ', '.join([f"pv{i}_value =?" for i, pv in enumerate(control_pvs, 1)])
                table_pv_values=()
                for pv in control_pvs:
                    table_pv_values += (incoming_pv[pv],)
                update_table_values = tuple(table_pv_values) +(current_time,'modify') +(mode_name,)
                cursor.execute(f"UPDATE {table_name} SET {update_table_columns},time=?,operation=? WHERE mode_name =?", update_table_values)
            else:
                master_insert_sql = (f"INSERT INTO {self.master_table_name} "
                                     f"(table_name, mode_name, db_name, db_dir, create_time, modify_time, operation) VALUES (?,?,?,?,?,?,?)")
                master_values = (table_name, mode_name,db_name,db_dir,current_time,current_time,"create")
                cursor.execute(master_insert_sql, master_values)
                table_parts = []
                for i, pv in enumerate(control_pvs, 1):
                    column_name = f'pv{i}_name'
                    column_value = f'pv{i}_value'
                    table_parts.append(column_name)
                    table_parts.append(column_value)
                table_sql = ', '.join(table_parts)
                placeholders = ', '.join(['?'] * len(table_parts))
                table_insert_sql = f"INSERT INTO {table_name} (table_name, mode_name, {table_sql}, time,operation) VALUES (?, ?, {placeholders}, ?, ?)"
                table_values = (table_name, mode_name)
                for pv in control_pvs:
                    table_values += (pv, incoming_pv[pv])
                table_values +=(current_time,'create')
                cursor.execute(table_insert_sql, table_values)
            conn.execute('COMMIT')
            return True
        except sqlite3.Error as e:
            conn.execute('ROLLBACK')
            print(f"写入数据时出错: {e}")
            return False
        finally:
            conn.close()

    def delete_data(self, data):
        for table_name, config in self.grouped_configs.items():
            db_name = config['DB']['DB_Name']
            db_dir = config['DB']['DB_Dir']
        db_file = os.path.join(db_dir, db_name)
        table_name = data.get('table_name')
        mode_name = data.get('mode_name')
        if not table_name or not mode_name:
            print("传入数据缺少 table_name 或 mode_name")
            return False
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        try:
            conn.execute('BEGIN')
            cursor.execute(f"DELETE FROM {self.master_table_name} WHERE table_name =? AND mode_name =?",
                           (table_name, mode_name))
            cursor.execute(f"DELETE FROM {table_name} WHERE mode_name =?", (mode_name,))
            conn.execute('COMMIT')
            return True
        except sqlite3.Error as e:
            conn.execute('ROLLBACK')
            print(f"删除数据时出错: {e}")
            return False
        finally:
            conn.close()

    def query_data(self, data):
        table_name=data['table_name']
        mode_name=data['mode_name']
        if not table_name or not mode_name:
            print("缺少table_name或mode_name参数")
            return None
        db_file = os.path.join(self.grouped_configs[table_name]['DB']['DB_Dir'], self.grouped_configs[table_name]['DB']['DB_Name'])
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT * FROM {table_name} WHERE table_name =? AND mode_name =?",
                (table_name, mode_name)
            )
            result = cursor.fetchone()
            if not result:
                print(f"业务表 {table_name} 中无 {mode_name} 对应的记录")
                return None
            columns = [desc[0] for desc in cursor.description]
            data_dict = dict(zip(columns, result))
            return data_dict
        except sqlite3.Error as e:
            print(f"查询数据时出错: {e}")
            return None
        finally:
            conn.close()

    def export_data(self, data):
        table_name = data.get('table_name')
        export_dir = data.get('export_dir')
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except OSError as e:
                print(f"创建目录 {export_dir} 失败: {e}")
                return False
        export_name = data.get('export_name', f"{table_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
        if not table_name or not export_dir:
            print("缺少必要参数 table_name 或 export_dir")
            return False
        db_name = self.grouped_configs[table_name]['DB']['DB_Name']
        db_dir = self.grouped_configs[table_name]['DB']['DB_Dir']
        db_file = os.path.join(db_dir, db_name)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            max_widths = [len(col) for col in columns]
            for row in rows:
                for i, value in enumerate(row):
                    max_widths[i] = max(max_widths[i], len(str(value)))
            file_path = os.path.join(export_dir, export_name)
            with open(file_path, 'w', encoding='utf - 8') as f:
                for i, col in enumerate(columns):
                    f.write(f"{col:^{max_widths[i]}} ")
                f.write('\n')

                for row in rows:
                    for i, value in enumerate(row):
                        f.write(f"{str(value):^{max_widths[i]}} ")
                    f.write('\n')
            print(f"成功导出表 {table_name} 到 {file_path}")
            return True
        except sqlite3.Error as e:
            print(f"导出表 {table_name} 时出错: {e}")
            return False
        finally:
            conn.close()

    def print_grouped_configs(self):
        for table_name, config in self.grouped_configs.items():
            print(f"Table Name: {table_name}")
            print("  Database Config:")
            db_config = config.get('DB')
            if db_config:
                print(f"    DB_Name: {db_config['DB_Name']}")
                print(f"    DB_Dir: {db_config['DB_Dir']}")
            pvs_config = config.get('PVs')
            if pvs_config:
                print("  PVs Config:")
                for pv_key, pv_value in pvs_config.items():
                    print(f"    {pv_key}: {pv_value}")
            control_pvs_config = config.get('Control_PVs')
            if control_pvs_config:
                print("  Control PVs Config:")
                for index, pv in enumerate(control_pvs_config, 1):
                    print(f"    PV{index}: {pv}")
            check_config = config.get('check')
            if check_config:
                print("  Check Config:")
                for pv, value in check_config.items():
                    print(f"    {pv}: {value}")
            action_config = config.get('operationAction')
            if action_config:
                print("  Action Config:")
                for index, (pv, operation, wait) in enumerate(action_config, 1):
                    print(f"    Action{index}: PV: {pv}, Operation: {operation}, Wait: {wait}")

            print()

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
        "actionDir": "BL_ID:logical:actionDir",
        "actionStatus": "BL_ID:logical:actionStatus",
        "actionTrig": "BL_ID:logical:actionTrig"
    },
    "Logical1_Control_PVs": {
        "IOC:m1", "IOC:m2"
    },
    "Logical1_Action":{
            "check":{"IOC:m4":1},
            "action": [
                ["IOC:m1", "fwd", True],
                ["IOC:m2", "rev", True],
                ["IOC:m1", "pos", False],
                ["IOC:m2", "5", True],
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
        "actionDir": "BL_ID:logical2:actionDir",
        "actionStatus": "BL_ID:logical2:actionStatus",
        "actionTrig": "BL_ID:logical2:actionTrig"
    },
    "Logical2_Control_PVs": {
        "IOC:m1", "IOC:m3"
    }
}
'''
skill_db = SnapshotSkillDB(Snapshot_Config)
skill_db.print_grouped_configs()
data_to_write = {
        'table_name': 'Logical1',
       'mode_name': 'BL_ID:logical:modeName',
        'IOC:m2': '15',
        'IOC:m1': '25'
    }
data1_to_write = {
        'table_name': 'Logical1',
       'mode_name': 'modeName1',
        'IOC:m2': '10',
        'IOC:m1': '20'
    }
data_to_delete = {
        'table_name': 'Logical1',
       'mode_name': 'modeName1',
    }
export_data={
    'table_name': 'Logical1',
    'export_dir':'././export',
}
skill_db.write_data(data_to_write)
skill_db.write_data(data1_to_write)
skill_db.query_data(data_to_delete)
skill_db.execute()
'''





