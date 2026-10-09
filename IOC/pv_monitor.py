import os
import threading
import time

class SmartPVMonitor:
    def __init__(self, objectCreator,period):
        self.creator = objectCreator
        self.period = period
        self.running = True
        self.prev_pv_cache = {}

    def clear_screen(self):
        # 清屏兼容Windows/Linux/Mac
        os.system('cls' if os.name == 'nt' else 'clear')

    def start(self):
        print("==== PV调试监控已启动 ====")
        print("提示：仅读取内存缓存，不操作底层EPICS对象\n")
        '''
        for name, typ, obj in self.creator.pv_objects:
            print(f"{name:<22} | {typ:<22} | {obj}")
            if typ != "motor":
                try:
                    value = obj.get()
                    print(f"PV {name} 的值为: {value}")
                except Exception as e:
                    print(f"获取PV {name} 的值时出错: {e}")
        '''
        try:
            while self.running:
                self.clear_screen()
                current_pv_cache = self.creator.pv_cache
                changed_items = {k: v for k, v in current_pv_cache.items() if
                                 k not in self.prev_pv_cache or v != self.prev_pv_cache[k]}
                '''
                if changed_items:
                    print("========== 发生变化的PV ==========")
                    for pv_name, val in changed_items.items():
                        print(f"{pv_name:<22} RBV = {val}")
                    print("====================================")
                '''
                self.prev_pv_cache = current_pv_cache.copy()
                '''
                print("========== 实时电机RBV缓存 ==========")
                for pv_name, val in current_pv_cache.items():
                    print(f"{pv_name:<22} RBV = {val}")
                print("====================================")
                print("完整缓存字典：")
                print(current_pv_cache)
                '''
                time.sleep(self.period)
        except KeyboardInterrupt:
            print("\n🛑 监控收到停止信号")
            self.running = False

    def start_background(self):
        # 后台守护线程启动监控打印
        monitor_thread = threading.Thread(
            target=self.start,
            daemon=True,
            name="PV_Monitor_Print"
        )
        monitor_thread.start()

    def stop_background(self):
        if self.monitor_thread:
            self.running = False
            self.monitor_thread.join()