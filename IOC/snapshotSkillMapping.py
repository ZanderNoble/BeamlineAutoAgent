from epics.compat import epicsPV
import math
import epics
from IOC.snapshotSkillDatabase import SnapshotSkillDB
class SnapshotSkillMapping(SnapshotSkillDB):
    def __init__(self, config,monitor_example):
        super().__init__(config)
        self.monitor_example = monitor_example
        for table_name, config in self.grouped_configs.items():
            self.pv_mapping(config)

    def pv_mapping(self,config):
        self.pv_mappings = config.get('PVs', {})
        #print(f"config={config},pv_mappings={self.pv_mappings}")
        self.pv_modeName = epics.PV(self.pv_mappings.get('modeName'))
        self.pv_saveTrig = epics.PV(self.pv_mappings.get('saveTrig'))
        self.pv_saveStatus = epics.PV(self.pv_mappings.get('saveStatus'))
        self.pv_exportDir = epics.PV(self.pv_mappings.get('exportDir'))
        self.pv_exportTrig = epics.PV(self.pv_mappings.get('exportTrig'))
        self.pv_exportStatus = epics.PV(self.pv_mappings.get('exportStatus'))
        self.pv_actionDir = epics.PV(self.pv_mappings.get('actionDir'))
        self.pv_actionStatus = epics.PV(self.pv_mappings.get('actionStatus'))
        self.pv_actionTrig = epics.PV(self.pv_mappings.get('actionTrig'))

    def execute(self):
        for table_name, config in self.grouped_configs.items():
            #print(f'    Table: {table_name},config: {config}')
            self._handle_table_save(table_name,config)
            self._handle_table_export(table_name,config)
            self._handle_table_action(table_name,config)

    def _handle_table_save(self, table_name, config):
        #print(f'pv_modeName={pv_modeName},pv_saveTrig={pv_saveTrig},pv_saveStatus={pv_saveStatus}')
        #print(f'grouped_configs={self.grouped_configs[table_name]}\ndata={data}\nsave_data={save_data}\n')
        if self.pv_saveTrig.value == 1:
            mode_name = self.pv_modeName.value
            print(f"self.pv_modeName={self.pv_modeName},key={mode_name}")
            data = {key: self.monitor_example.creator.pv_cache[key] for key in
                    self.grouped_configs[table_name]['Control_PVs'] if key in self.monitor_example.creator.pv_cache}
            print(f'grouped_configs={self.grouped_configs[table_name]},data={data}')
            save_data = {
                'table_name': table_name,
                'mode_name': mode_name
            }
            save_data.update(data)
            print(f'grouped_configs={self.grouped_configs[table_name]},data={data},save_data={save_data}')
            write_result = super().write_data(save_data)
            self.pv_saveTrig.put(0)
            if write_result:
                self.pv_saveStatus.put(1)
                print(f"✅ 对于表 {table_name},已保存快照:{save_data}")
            else:
                self.pv_saveStatus.put(2)
                print(f"❌ 对于表 {table_name},保存快照失败")

    def _handle_table_export(self, table_name, config):
        if self.pv_exportTrig.value == 1:
            export_dir = self.pv_exportDir.value or None
            export_data = {
                'table_name': table_name,
                'export_dir': export_dir
            }
            export_result = super().export_data(export_data)
            print(f'export_result={export_result}')
            if export_result:
                self.pv_exportStatus.put(1)
                print(f"✅ 已导出表 {table_name}在目录{export_dir}")
            else:
                self.pv_exportStatus.put(2)
                print(f"❌ 对于表 {table_name},导出失败")
            self.pv_exportTrig.put(0)

    def _handle_table_action(self, table_name, config):
        #print(f"/***********SnapshotSkillMapping  pv_actionTrig.value={self.pv_actionTrig.value}**********/")
        if self.pv_actionTrig.value == 0:
            target_key = self.pv_actionDir.value
            if not target_key:
                self.pv_actionTrig.put(0)
                return
            query_data = {
                'table_name': table_name,
                'mode_name': target_key
            }
            result = super().query_data(query_data)
            if not result:
                print(f"快照查询无结果: table={table_name}, mode={target_key}")
                self.pv_actionTrig.put(0)
                return
            transform_value = {key: value for key, value in result.items() if not key.startswith('pv')}
            for key in result.keys():
                if key.startswith('pv') and '_name' in key:
                    num_str = key.split('_')[0][2:]
                    val_key = f'pv{num_str}_value'
                    if val_key in result:
                        pv_name = result[key]
                        transform_value[pv_name] = result[val_key]

            print(f'transform_value={transform_value}')
            action_config = self.grouped_configs[table_name].get('operationAction')
            if not action_config:
                print(f"No operationAction config found，无待执行指令")
                return
            pv_map = {name: (typ, obj) for name, typ, obj in self.monitor_example.creator.pv_objects}
            print(f"pv_map={pv_map}")
            for index, (pv, operation, param) in enumerate(action_config, 1):
                print(f"===== 待执行指令{index} =====")
                print(f"  pv={pv}, operation={operation}, param={param}")
                if isinstance(operation, str) and operation == "check":
                    expect_val = param
                    print(f"  [预览] check: {pv} 预期值={expect_val}")
                elif isinstance(operation, str) and operation.endswith('Lim'):
                    print(f"  [预览] 设置限位: {pv} 动作={operation}, wait={param}")
                elif isinstance(operation, str) and operation == "pos":
                    pos_value = transform_value.get(pv)
                    print(f"  [预览] pos恢复: {pv} → 快照值={pos_value}")
                else:
                    pos_value = operation
                    print(f"  [预览] 设置PV: {pv} → {pos_value}, wait={param}")
            self.pv_actionTrig.put(0)

    #def exec_check(pv_obj, expected_value, record_type=None, timeout=2.0):

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
            "operation": [
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
skill_db = SnapshotSkillMapping(Snapshot_Config)
#skill_db.print_grouped_configs()
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