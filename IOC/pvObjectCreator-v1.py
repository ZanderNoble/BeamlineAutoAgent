import epics
import logging
import threading
import time
from IOC.new_motor import ModeMotor

logging.basicConfig(level=logging.INFO)

class PVObjectCreator:
    def __init__(self, pv_config,period):
        self.pv_config = pv_config
        self.pv_objects = []
        self.ca_lock = threading.Lock()
        self.period = period
        self.running_collect = False
        self.collect_thread = None
        self.pv_cache = {}

    def check_connection(self, name, typ, obj, timeout=1.0):
        connected = False
        if typ == "motor":
            try:
                with self.ca_lock:
                    val = obj.VAL
                connected = True
            except AttributeError as e:
                logging.error(f"检查电机 {name} 连接时出错: {e}")
                raise
        else:
            try:
                obj.wait_for_connection(timeout=timeout)
                connected = obj.connected
            except Exception as e:
                logging.error(f"检查普通 PV {name} 连接时出错: {e}")
                raise
        return connected

    def create_pv_objects(self):
        for name, typ in self.pv_config:
            try:
                if typ == "motor":
                    obj = ModeMotor(name)
                    self.check_connection(name, typ, obj)
                else:
                    obj = epics.PV(name)
                    self.check_connection(name, typ, obj)
                    obj.add_callback(self._pv_callback)
                self.pv_objects.append((name, typ, obj))
            except Exception as e:
                logging.error(f"创建 PV {name} 时出错: {e}")
                raise
        return self.pv_objects

    def _pv_callback(self, pvname, value, **kwargs):
        logging.info(f"✅ 回调更新 | {pvname:<25} = {value}")

    def read_pv_attr(self, pv_name: str, attr: str = "VAL"):
        """根据设备名+属性读取数值，线程安全"""
        with self.ca_lock:
            for name, typ, obj in self.pv_objects:
                if name == pv_name:
                    try:
                        val = getattr(obj, attr)
                        return val
                    except Exception as e:
                        logging.error(f"读取 {pv_name}.{attr} 失败: {e}")
                        return None
            logging.error(f"不存在PV/电机 {pv_name}")
            return None

    def write_pv_attr(self, pv_name: str, attr: str, value):
        """根据设备名+属性写入数值，线程安全"""
        with self.ca_lock:
            for name, typ, obj in self.pv_objects:
                if name == pv_name:
                    try:
                        setattr(obj, attr, value)
                        logging.info(f"写入 {pv_name}.{attr} = {value}")
                        return True
                    except Exception as e:
                        logging.error(f"写入 {pv_name}.{attr} 失败: {e}")
                        return False
            logging.error(f"不存在PV/电机 {pv_name}")
            return False

    def rbv_collect_loop(self):
        logging.info("电机RBV后台采集线程启动")
        while self.running_collect:
            tmp_cache = {}
            with self.ca_lock:
                for name, typ, obj in self.pv_objects:
                    if typ != "motor":
                        continue
                    try:
                        rbv_val = obj.RBV
                        prec = int(obj.PREC) if hasattr(obj, "PREC") and obj.PREC > 0 else 3
                        tmp_cache[name] = round(float(rbv_val), prec)
                    except Exception as e:
                        tmp_cache[name] = f"读取异常:{str(e)}"
            self.pv_cache = tmp_cache
            #time.sleep(self.period)
        logging.info("电机RBV采集线程停止")

    def start_rbv_collect(self, interval=0.2):
        if self.running_collect:
            logging.warning("RBV采集已在运行")
            return
        self.running_collect = True
        self.collect_thread = threading.Thread(
            target=self.rbv_collect_loop,
            daemon=True,
            name="PV_ObjectCreator_Thread"
        )
        self.collect_thread.start()

    def stop_rbv_collect(self):
        self.running_collect = False
        if self.collect_thread and self.collect_thread.is_alive():
            self.collect_thread.join(timeout=1)