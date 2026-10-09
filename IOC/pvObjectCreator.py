import epics
import logging
import threading
import time
from IOC.new_motor import ModeMotor

logging.basicConfig(level=logging.INFO)

def get_pv_type(pv_name, timeout=1.0):
    """
    探测 PV 的记录类型（通过 .RTYP）
    返回：
        'motor'  - 电机记录
        其他字符串 - 其他记录类型
        None     - 连接失败或不存在
    """
    base = pv_name.split('.')[0]
    pv_type = f"{base}.RTYP"
    try:
        pv_type = epics.caget(pv_type, timeout=timeout, as_string=True)
        return pv_type
    except Exception as e:
        logging.warning(f"探测 {pv_name} 类型时异常: {e}")
        return None

class PVObjectCreator:
    def __init__(self, pv_names, period):
        """
        pv_names: 仅包含 PV 基础名称的列表，例如 ["IOC:m1", "IOC:m2", "BL_ID:temp"]
        """
        self.pv_names = pv_names
        self.pv_objects = []          # 元素格式: (name, typ, obj)
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
        for name in self.pv_names:
            typ = get_pv_type(name)
            try:
                if typ == "motor":
                    obj = ModeMotor(name)
                    logging.info(f"🚗 识别为电机记录: {name}")
                else:
                    obj = epics.PV(name)
                    if not obj.wait_for_connection(timeout=1.0):
                        logging.error(f"❌ 无法连接 PV {name}，跳过")
                        continue
                    obj.add_callback(self._pv_callback)
                    logging.info(f"📊 识别为普通记录 [{typ}]: {name}")
                self.check_connection(name, typ, obj)
                self.pv_objects.append((name, typ, obj))
            except Exception as e:
                logging.error(f"创建 PV {name} 对象时出错: {e}")
        return self.pv_objects

    def _pv_callback(self, pvname, value, **kwargs):
        logging.info(f"✅ 回调更新 | {pvname:<25} = {value}")

    def read_pv_attr(self, pv_name: str, attr: str = "VAL"):
        with self.ca_lock:
            for name, typ, obj in self.pv_objects:
                if name == pv_name:
                    try:
                        return getattr(obj, attr)
                    except Exception as e:
                        logging.error(f"读取 {pv_name}.{attr} 失败: {e}")
                        return None
            logging.error(f"不存在 PV/电机 {pv_name}")
            return None

    def write_pv_attr(self, pv_name: str, attr: str, value):
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
            logging.error(f"不存在 PV/电机 {pv_name}")
            return False

    def rbv_collect_loop(self):
        logging.info("电机 RBV 后台采集线程启动")
        while self.running_collect:
            tmp_cache = {}
            with self.ca_lock:
                for name, typ, obj in self.pv_objects:
                    if typ != "motor":   # 只采集电机
                        continue
                    try:
                        rbv_val = obj.RBV
                        prec = int(obj.PREC) if hasattr(obj, "PREC") else 3
                        tmp_cache[name] = round(float(rbv_val), prec)
                    except Exception as e:
                        tmp_cache[name] = f"读取异常:{str(e)}"
            self.pv_cache = tmp_cache
            time.sleep(self.period)
        logging.info("电机 RBV 采集线程停止")

    def start_rbv_collect(self, interval=None):
        if interval is not None:
            self.period = interval
        if self.running_collect:
            logging.warning("RBV 采集已在运行")
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