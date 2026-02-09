#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git 代理管理工具
版本号定义位置：修改下方的 __version__ 变量
"""

# ============================================
# 版本号定义 - 修改此处即可更新版本
# 格式：主版本.次版本.修订号
# ============================================
__version__ = "1.1.0"

import tkinter as tk
from tkinter import messagebox
import configparser
import subprocess
import sys
import threading
from pathlib import Path


class ProxyGUI:
    def __init__(self, root):
        print(f"\n{'='*50}")
        print(f"[调试 init] 启动 Git 代理管理工具 v{__version__}")
        print(f"{'='*50}")

        self.root = root
        self.root.title(f"Git 代理管理工具 v{__version__}")
        self.root.geometry("400x420")
        self.root.resizable(False, False)

        # 线程锁，防止重复点击
        self.busy = False
        print(f"[调试 init] busy 初始化为: {self.busy}")

        # 绑定窗口关闭事件，自动保存配置
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 检测 Git
        print("[调试 init] 检测 Git 环境...")
        if not self.check_git():
            messagebox.showerror(
                "未检测到 Git",
                "本工具需要 Git 环境才能正常工作。\n\n"
                "请先安装 Git:\nhttps://git-scm.com/downloads\n\n"
                "安装后重新运行本工具。"
            )
            sys.exit(1)
        print("[调试 init] Git 检测通过")

        # 创建界面元素
        print("[调试 init] 创建界面...")
        self.create_widgets()
        print("[调试 init] 界面创建完成")

        # 加载配置
        print("[调试 init] 加载配置...")
        self.load_config()

        # 启动时查询一次状态
        self.query_proxy()

    def check_git(self):
        """检测 Git 是否安装"""
        try:
            subprocess.run(['git', '--version'],
                          capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def create_widgets(self):
        """创建界面控件"""
        # 标题
        title = tk.Label(self.root, text="Git 代理管理工具",
                        font=("微软雅黑", 14, "bold"))
        title.pack(pady=10)

        # 代理设置框架
        settings_frame = tk.LabelFrame(self.root, text="代理服务器设置",
                                      font=("微软雅黑", 10))
        settings_frame.pack(padx=20, pady=10, fill="x")

        # IP地址
        tk.Label(settings_frame, text="IP地址:", font=("微软雅黑", 10)).grid(
            row=0, column=0, padx=5, pady=5, sticky="e")
        self.host_entry = tk.Entry(settings_frame, width=20, font=("微软雅黑", 10))
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)
        self.host_entry.insert(0, "127.0.0.1")

        # 端口
        tk.Label(settings_frame, text="端口:", font=("微软雅黑", 10)).grid(
            row=1, column=0, padx=5, pady=5, sticky="e")
        self.port_entry = tk.Entry(settings_frame, width=20, font=("微软雅黑", 10))
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)
        self.port_entry.insert(0, "7890")

        # 当前状态框架
        status_frame = tk.LabelFrame(self.root, text="当前状态",
                                    font=("微软雅黑", 10))
        status_frame.pack(padx=20, pady=10, fill="x")

        self.http_status = tk.Label(status_frame, text="HTTP代理: 未设置",
                                   font=("微软雅黑", 9), fg="gray")
        self.http_status.pack(anchor="w", padx=10, pady=2)

        self.https_status = tk.Label(status_frame, text="HTTPS代理: 未设置",
                                    font=("微软雅黑", 9), fg="gray")
        self.https_status.pack(anchor="w", padx=10, pady=2)

        # 操作按钮框架
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)

        self.btn_query = tk.Button(btn_frame, text="查询状态",
                                   command=self.query_proxy,
                                   width=12, font=("微软雅黑", 10))
        self.btn_query.grid(row=0, column=0, padx=5, pady=5)

        self.btn_set = tk.Button(btn_frame, text="设置代理",
                                 command=self.set_proxy,
                                 width=12, font=("微软雅黑", 10))
        self.btn_set.grid(row=0, column=1, padx=5, pady=5)

        self.btn_unset = tk.Button(btn_frame, text="取消代理",
                                   command=self.unset_proxy,
                                   width=12, font=("微软雅黑", 10))
        self.btn_unset.grid(row=1, column=0, padx=5, pady=5)

        self.btn_save = tk.Button(btn_frame, text="保存配置",
                                  command=self.save_config,
                                  width=12, font=("微软雅黑", 10))
        self.btn_save.grid(row=1, column=1, padx=5, pady=5)

        # 提示信息
        self.message_label = tk.Label(self.root, text="就绪",
                                     font=("微软雅黑", 9), fg="green")
        self.message_label.pack(pady=5)

    def set_buttons_state(self, state):
        """设置按钮启用/禁用状态"""
        for btn in [self.btn_query, self.btn_set, self.btn_unset, self.btn_save]:
            btn.config(state=state)

    def run_git_command(self, args):
        """执行 git 命令（线程安全）"""
        try:
            result = subprocess.run(
                ['git'] + args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=10  # 10秒超时，防止卡死
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "命令超时"
        except Exception as e:
            return False, str(e)

    def update_status_thread_safe(self, func, *args, **kwargs):
        """线程安全地更新 UI"""
        self.root.after(0, func, *args, **kwargs)

    def get_config_path(self):
        """获取配置文件路径（兼容 PyInstaller 打包）"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent / "proxy.ini"
        else:
            return Path(__file__).parent / "proxy.ini"

    def load_config(self):
        """加载或创建配置文件"""
        print("[调试 load] 开始加载配置...")
        config_file = self.get_config_path()
        print(f"[调试 load] 配置文件路径: {config_file}")
        config = configparser.ConfigParser()

        if not config_file.exists():
            print("[调试 load] 配置文件不存在，创建默认配置")
            config['proxy'] = {
                'host': '127.0.0.1',
                'port': '7890'
            }
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                self.update_status("已创建默认配置文件", True)
                print("[调试 load] 默认配置创建成功")
            except Exception as e:
                print(f"[调试 load] 创建配置文件失败: {e}")
                self.update_status(f"创建配置文件失败: {e}", False)
        else:
            print("[调试 load] 配置文件存在，读取配置")
            try:
                config.read(config_file, encoding='utf-8')
                host = config.get('proxy', 'host', fallback='127.0.0.1')
                port = config.get('proxy', 'port', fallback='7890')
                print(f"[调试 load] 读取到配置: host={host}, port={port}")

                self.host_entry.delete(0, tk.END)
                self.host_entry.insert(0, host)
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, port)
                print("[调试 load] 界面已更新")
            except Exception as e:
                print(f"[调试 load] 读取配置文件失败: {e}")
                self.update_status(f"读取配置文件失败: {e}", False)

    def save_config(self):
        """保存配置到文件"""
        print(f"[调试 save] 用户点击保存配置")
        config_file = self.get_config_path()
        print(f"[调试 save] 配置文件路径: {config_file}")
        config = configparser.ConfigParser()

        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        print(f"[调试 save] 准备保存: host={host}, port={port}")

        config['proxy'] = {
            'host': host,
            'port': port
        }

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            self.update_status("配置已保存", True)
            print("[调试 save] 配置保存成功")
        except Exception as e:
            print(f"[调试 save] 配置保存失败: {e}")
            self.update_status(f"保存配置失败: {e}", False)

    def _do_query_proxy(self):
        """执行查询操作（后台线程）"""
        print("[调试 query] 开始执行查询操作...")

        success, http_proxy = self.run_git_command(['config', '--global', 'http.proxy'])
        print(f"[调试 query] HTTP 查询结果: success={success}, proxy='{http_proxy}'")
        http_result = (success, http_proxy)

        success, https_proxy = self.run_git_command(['config', '--global', 'https.proxy'])
        print(f"[调试 query] HTTPS 查询结果: success={success}, proxy='{https_proxy}'")
        https_result = (success, https_proxy)

        # 更新 UI
        def update_ui():
            print("[调试 query] 更新 UI...")
            if http_result[0] and http_result[1]:
                self.http_status.config(text=f"HTTP代理: {http_result[1]}", fg="green")
            else:
                self.http_status.config(text="HTTP代理: 未设置", fg="gray")

            if https_result[0] and https_result[1]:
                self.https_status.config(text=f"HTTPS代理: {https_result[1]}", fg="green")
            else:
                self.https_status.config(text="HTTPS代理: 未设置", fg="gray")

            self.update_status("状态已更新", True)
            self.set_buttons_state("normal")
            self.busy = False  # 重要：重置忙碌状态
            print("[调试 query] 查询完成，busy 已重置")

        self.update_status_thread_safe(update_ui)

    def query_proxy(self):
        """查询代理状态（使用线程）"""
        print(f"[调试 query] 用户点击查询按钮, busy={self.busy}")
        if self.busy:
            print("[调试 query] 忙碌状态，跳过")
            return

        self.busy = True
        self.set_buttons_state("disabled")
        self.update_status("查询中...", True)
        print("[调试 query] 启动查询线程")

        threading.Thread(target=self._do_query_proxy, daemon=True).start()

    def _do_set_proxy(self, proxy_url):
        """执行设置操作（后台线程）"""
        print(f"[调试] 开始设置代理: {proxy_url}")
        http_ok = False
        https_ok = False

        # 设置 HTTP
        print("[调试] 设置 HTTP 代理...")
        success, output = self.run_git_command(['config', '--global', 'http.proxy', proxy_url])
        print(f"[调试] HTTP set 结果: success={success}")
        if success:
            http_ok = True

        # 设置 HTTPS
        print("[调试] 设置 HTTPS 代理...")
        success, output = self.run_git_command(['config', '--global', 'https.proxy', proxy_url])
        print(f"[调试] HTTPS set 结果: success={success}")
        if success:
            https_ok = True

        # 查询当前状态并更新 UI
        print("[调试] 查询设置后的代理状态...")
        success, http_proxy = self.run_git_command(['config', '--global', 'http.proxy'])
        success2, https_proxy = self.run_git_command(['config', '--global', 'https.proxy'])
        print(f"[调试] 查询结果: http='{http_proxy}', https='{https_proxy}'")

        def update_ui():
            print("[调试] 更新设置后的 UI...")
            if http_proxy:
                self.http_status.config(text=f"HTTP代理: {http_proxy}", fg="green")
            else:
                self.http_status.config(text="HTTP代理: 未设置", fg="gray")

            if https_proxy:
                self.https_status.config(text=f"HTTPS代理: {https_proxy}", fg="green")
            else:
                self.https_status.config(text="HTTPS代理: 未设置", fg="gray")

            if http_ok and https_ok:
                self.update_status(f"代理已设置: {proxy_url}", True)
            elif http_ok:
                self.update_status("HTTPS代理设置失败", False)
            elif https_ok:
                self.update_status("HTTP代理设置失败", False)
            else:
                self.update_status("代理设置失败", False)

            self.set_buttons_state("normal")
            self.busy = False
            print("[调试] 设置完成，按钮已恢复")

        self.update_status_thread_safe(update_ui)

    def set_proxy(self):
        """设置代理（使用线程）"""
        print(f"[调试 set] 用户点击设置代理按钮, busy={self.busy}")
        if self.busy:
            print("[调试 set] 忙碌状态，跳过")
            return

        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        print(f"[调试 set] 准备设置代理: {host}:{port}")

        if not host or not port:
            print("[调试 set] IP或端口为空，拒绝操作")
            self.update_status("请填写完整的 IP 和端口", False)
            return

        proxy_url = f"{host}:{port}"

        self.busy = True
        self.set_buttons_state("disabled")
        self.update_status("设置中...", True)
        print("[调试 set] 启动设置代理线程")

        threading.Thread(target=self._do_set_proxy, args=(proxy_url,), daemon=True).start()

    def _do_unset_proxy(self):
        """执行取消操作（后台线程）"""
        print("[调试] 开始取消代理...")

        # 取消 HTTP
        print("[调试] 取消 HTTP 代理...")
        success, output = self.run_git_command(['config', '--global', '--unset', 'http.proxy'])
        print(f"[调试] HTTP unset 结果: success={success}, output='{output}'")

        # 取消 HTTPS
        print("[调试] 取消 HTTPS 代理...")
        success, output = self.run_git_command(['config', '--global', '--unset', 'https.proxy'])
        print(f"[调试] HTTPS unset 结果: success={success}, output='{output}'")

        # 查询并显示当前状态
        print("[调试] 查询当前代理状态...")
        success, http_proxy = self.run_git_command(['config', '--global', 'http.proxy'])
        success2, https_proxy = self.run_git_command(['config', '--global', 'https.proxy'])
        print(f"[调试] 查询结果: http='{http_proxy}', https='{https_proxy}'")

        # 更新 UI
        def update_ui():
            print("[调试] 更新 UI...")
            if http_proxy:
                self.http_status.config(text=f"HTTP代理: {http_proxy}", fg="green")
            else:
                self.http_status.config(text="HTTP代理: 未设置", fg="gray")

            if https_proxy:
                self.https_status.config(text=f"HTTPS代理: {https_proxy}", fg="green")
            else:
                self.https_status.config(text="HTTPS代理: 未设置", fg="gray")

            self.update_status("代理已取消", True)
            self.set_buttons_state("normal")
            self.busy = False
            print("[调试] 操作完成，按钮已恢复")

        self.update_status_thread_safe(update_ui)

    def unset_proxy(self):
        """取消代理（使用线程）"""
        print("[调试] 用户点击取消代理按钮")
        if self.busy:
            print("[调试] 忙碌状态，跳过")
            return

        self.busy = True
        self.set_buttons_state("disabled")
        self.update_status("取消中...", True)
        print("[调试] 启动取消代理线程")

        threading.Thread(target=self._do_unset_proxy, daemon=True).start()

    def update_status(self, message, success=True):
        """更新状态标签"""
        self.message_label.config(text=message,
                                 fg="green" if success else "red")

    def on_closing(self):
        """窗口关闭时自动保存配置"""
        print("\n[调试 close] 用户关闭窗口...")
        try:
            self.save_config()
        except Exception as e:
            print(f"[调试 close] 保存配置时出错: {e}")
        finally:
            print("[调试 close] 程序退出\n")
            self.root.destroy()


def main():
    root = tk.Tk()
    app = ProxyGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
