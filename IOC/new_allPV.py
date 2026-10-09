from caproto.server import PVGroup, ioc_arg_parser, run
import threading,time
from IOC.new_logicalPV import SimpleIOC
from IOC.new_motor import MotorWithError

def print_all_pvs(ioc):
    print("\n" + "="*60)
    print("✅ 已创建的所有 PV 列表：")
    print("="*60)
    for pv_name in sorted(ioc.pvdb.keys()):
        print(f"📌 {pv_name}")
    print("="*60 + "\n")

class IOCMain(PVGroup):
    """An IOC with Logical PV and Motor PV groups created dynamically"""
    system_global = 0
    def __init__(self,  *, groups, **kwargs):
        super().__init__(**kwargs)
        self.groups = groups

class IOCServer:
    def __init__(self,logical_prefix=None,motor_prefix=None,motor_list=None,logical_list=None):
        self.logical_prefix = logical_prefix
        self.motor_prefix = motor_prefix
        self.motor_list = motor_list
        self.logical_list = logical_list
        self.ioc = None
        self.groups = {}
        self.pvdb_lock = threading.Lock()

    def create_ioc(self, **ioc_options):
        self.ioc = IOCMain( groups=self.groups, **ioc_options)
        for g in self.logical_list:
            try:
               #print(f"Creating SimpleIOC with prefix {self.logical_prefix}{g} and ioc {self.ioc}")
                self.groups[g] = SimpleIOC(f"{self.logical_prefix}{g}", ioc=self.ioc)
            except Exception as e:
                print(f"Error creating SimpleIOC for {g}: {e}")
        for g in self.motor_list:
            try:
                #print(f"Creating MotorWithError with prefix {self.motor_prefix}{g} and ioc {self.ioc}")
                self.groups[g] = MotorWithError(f"{self.motor_prefix}{g}", ioc=self.ioc)
            except Exception as e:
                print(f"Error creating MotorWithError for {g}: {e}")
        for group in self.groups.values():
            with self.pvdb_lock:
                self.ioc.pvdb.update(**group.pvdb)
        return self.ioc

    def start(self):
        try:
            ioc_options, run_options = ioc_arg_parser(default_prefix="", desc="Dynamic IOC")
            run_options['log_pv_names'] = True
            #run_options['interfaces'] = '0.0.0.0:5065'
            self.create_ioc(**ioc_options)
            print_all_pvs(self.ioc)
            #print(f"ioc_options: {ioc_options}")
            #print(f"run_options: {run_options}")
            try:
                run(self.ioc.pvdb, **run_options)
            except Exception as e:
                print(f"Error in run: {e}")
        except Exception as e:
            print(f"Error in starting IOC: {e}")

    def start_background(self):
        threading.Thread(target=self.start, daemon=True,name="PV_IOCServer_Thread").start()
        print("✅ IOC 后台启动完成")
'''
if __name__ == "__main__":
    # 1. 启动 IOC
    server = IOCServer(
        logical_prefix="BL_ID:",
        motor_prefix="IOC:",
        logical_list=["logical:"],
        motor_list=["m1", "m2"])
    server.start_background()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
'''