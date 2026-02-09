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
__version__ = "1.0.0"

import tkinter as tk
from tkinter import messagebox
import configparser
import subprocess
import sys
from pathlib import Path

class ProxyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Git 代理管理工具 v{__version__}")
        self.root.geometry("400x400")
        self.root.resizable(False, False)
        
        # 绑定窗口关闭事件，自动保存配置
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 检测 Git
        if not self.check_git():
            messagebox.showerror(
                "未检测到 Git",
                "本工具需要 Git 环境才能正常工作。\n\n"
                "请先安装 Git:\nhttps://git-scm.com/downloads\n\n"
                "安装后重新运行本工具。"
            )
            sys.exit(1)
        
        # 创建界面元素
        self.create_widgets()
        
        # 加载配置
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
        
        tk.Button(btn_frame, text="查询状态", command=self.query_proxy,
                 width=12, font=("微软雅黑", 10)).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="设置代理", command=self.set_proxy,
                 width=12, font=("微软雅黑", 10)).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="取消代理", command=self.unset_proxy,
                 width=12, font=("微软雅黑", 10)).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="保存配置", command=self.save_config,
                 width=12, font=("微软雅黑", 10)).grid(row=1, column=1, padx=5, pady=5)
        
        # 提示信息
        self.message_label = tk.Label(self.root, text="就绪", 
                                     font=("微软雅黑", 9), fg="green")
        self.message_label.pack(pady=5)
    
    def get_config_path(self):
        """获取配置文件路径（兼容 PyInstaller 打包）"""
        # PyInstaller 打包后 __file__ 指向临时目录
        # 使用 sys.executable 获取 exe 所在目录
        if getattr(sys, 'frozen', False):
            # 打包后的程序
            return Path(sys.executable).parent / "proxy.ini"
        else:
            # 原始 Python 脚本
            return Path(__file__).parent / "proxy.ini"
    
    def load_config(self):
        """加载或创建配置文件"""
        config_file = self.get_config_path()
        config = configparser.ConfigParser()
        
        if not config_file.exists():
            # 创建默认配置
            config['proxy'] = {
                'host': '127.0.0.1',
                'port': '7890'
            }
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                self.update_status("已创建默认配置文件", True)
            except Exception as e:
                self.update_status(f"创建配置文件失败: {e}", False)
        else:
            try:
                config.read(config_file, encoding='utf-8')
                host = config.get('proxy', 'host', fallback='127.0.0.1')
                port = config.get('proxy', 'port', fallback='7890')
                
                # 更新界面
                self.host_entry.delete(0, tk.END)
                self.host_entry.insert(0, host)
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, port)
            except Exception as e:
                self.update_status(f"读取配置文件失败: {e}", False)
    
    def save_config(self):
        """保存配置到文件"""
        config_file = self.get_config_path()
        config = configparser.ConfigParser()
        
        config['proxy'] = {
            'host': self.host_entry.get().strip(),
            'port': self.port_entry.get().strip()
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            self.update_status("配置已保存", True)
        except Exception as e:
            self.update_status(f"保存配置失败: {e}", False)
    
    def run_git_command(self, args):
        """执行 git 命令"""
        try:
            result = subprocess.run(
                ['git'] + args,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            return result.returncode == 0, result.stdout.strip()
        except Exception as e:
            return False, str(e)
    
    def query_proxy(self):
        """查询代理状态"""
        # 查询 HTTP
        success, http_proxy = self.run_git_command(['config', '--global', 'http.proxy'])
        if success and http_proxy:
            self.http_status.config(text=f"HTTP代理: {http_proxy}", fg="green")
        else:
            self.http_status.config(text="HTTP代理: 未设置", fg="gray")
        
        # 查询 HTTPS
        success, https_proxy = self.run_git_command(['config', '--global', 'https.proxy'])
        if success and https_proxy:
            self.https_status.config(text=f"HTTPS代理: {https_proxy}", fg="green")
        else:
            self.https_status.config(text="HTTPS代理: 未设置", fg="gray")
        
        self.update_status("状态已更新", True)
    
    def set_proxy(self):
        """设置代理"""
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        proxy_url = f"{host}:{port}"
        
        # 设置 HTTP
        success, _ = self.run_git_command(['config', '--global', 'http.proxy', proxy_url])
        if not success:
            self.update_status("HTTP代理设置失败", False)
            return
        
        # 设置 HTTPS
        success, _ = self.run_git_command(['config', '--global', 'https.proxy', proxy_url])
        if not success:
            self.update_status("HTTPS代理设置失败", False)
            return
        
        self.update_status(f"代理已设置: {proxy_url}", True)
        self.query_proxy()  # 刷新状态显示
    
    def unset_proxy(self):
        """取消代理"""
        # 取消 HTTP
        self.run_git_command(['config', '--global', '--unset', 'http.proxy'])
        
        # 取消 HTTPS
        self.run_git_command(['config', '--global', '--unset', 'https.proxy'])
        
        self.update_status("代理已取消", True)
        self.query_proxy()  # 刷新状态显示
    
    def update_status(self, message, success=True):
        """更新状态标签"""
        self.message_label.config(text=message,
                                 fg="green" if success else "red")

    def on_closing(self):
        """窗口关闭时自动保存配置"""
        try:
            self.save_config()
        except:
            pass  # 静默处理，不打扰用户
        finally:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = ProxyGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
