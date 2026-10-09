from caproto.server import PVGroup, pvproperty, PvpropertyString
def log_pv(pv_name, value):
    print(f"[PV] {pv_name} = {value}")

def print_all_pvs(ioc):
    print("\n" + "="*60)
    print("✅ 已创建的所有 PV 列表：")
    print("="*60)
    for pv_name in sorted(ioc.pvdb.keys()):
        print(f"📌 {pv_name}")
    print("="*60 + "\n")

class SimpleIOC(PVGroup):
    saveStatus = pvproperty(value=0, dtype=int)
    saveTrig = pvproperty(value=0, dtype=int)
    modeName = pvproperty(value="test", record="stringin", dtype=PvpropertyString)
    exportDir = pvproperty(value="./export", record="stringin", dtype=PvpropertyString)
    exportTrig = pvproperty(value=0, dtype=int)
    exportStatus = pvproperty(value=0, dtype=int)
    actionDir = pvproperty(value="test", record="stringin", dtype=PvpropertyString)
    actionTrig = pvproperty(value=0, dtype=int)
    actionStatus = pvproperty(value=0, dtype=int)
    operationLog = pvproperty(value="System Ready", dtype=str, max_length=1000)

    def __init__(self, prefix, *, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc
