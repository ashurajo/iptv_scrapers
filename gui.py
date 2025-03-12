import json
import logging
import queue
import random
import re
import threading
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import ttk, scrolledtext, messagebox, filedialog

import requests
from bs4 import BeautifulSoup

from base_scraper import IPTVChannel  # 修改为相对导入
import traceback

from config import LOG_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_CONFIG['filename'], encoding='utf-8'),

    ]
)

class IPTVScraperGUI:
    def __init__(self, root, version="1.3.0", max_page=5):
        self.root = root
        self.root.title("频道工具")
        self.version = version
        self.max_page = max_page
        self.session = requests.Session()
        self.log_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.running = False
        self.last_result = None
        self.proxy_enabled = False
        self.proxies = None
        # 添加scrapers属性初始化
        self.scrapers = {}
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        self.create_widgets()
        self.setup_logging()
        self.create_proxy_controls()
        self.progress_label = None
        self.create_progress_label()
        
        # 绑定事件
        self.root.bind('<<ScrapingDone>>', self.on_scraping_done)

    def export_valid_txt(self):
        if not self.last_result or 'accessible_urls' not in self.last_result:
            messagebox.showwarning("警告", "没有可导出的有效节目数据")
            return

        filename = f"{self.last_result['city']}_valid_channels.txt"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=filename,
            filetypes=[(f"{self.last_result['city']}", "*.txt")]
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    for item in self.last_result['accessible_urls']:
                        channel = item.get('channel_name', '未知频道').strip()
                        url = item.get('url', '').strip()
                        f.write(f"{channel},{url}\n")
                messagebox.showinfo("保存成功", f"文件已保存至：{filepath}")
            except Exception as e:
                messagebox.showerror("保存失败", f"文件写入错误: {str(e)}")

    def _update_progress(self, status, current, total):
        """ 更新进度标签（线程安全） """
        if self.progress_label:
            self.progress_label.configure(
                text=f"{status}: {current}/{total}",
                foreground="#666" if status == "就绪" else "#2ecc71"
            )

    def create_progress_label(self):
        # 在日志区域底部添加进度标签
        log_frame = self.root.grid_slaves(row=2, column=0)[0]
        self.progress_label = ttk.Label(log_frame, text="就绪")
        self.progress_label.pack(anchor="se")  # 固定在右下角
        
    def create_proxy_controls(self):
        # 在输入区域添加代理按钮
        input_frame = self.root.grid_slaves(row=0, column=0)[0]
        self.proxy_btn = ttk.Button(input_frame, text="设置代理", command=self.show_proxy_dialog)
        self.proxy_btn.grid(row=0, column=7, padx=5)

    def show_proxy_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("代理设置")
        dialog.geometry("300x150")

        ttk.Label(dialog, text="代理地址（例如：127.0.0.1:8080）:").pack(pady=5)
        self.proxy_entry = ttk.Entry(dialog, width=25)
        self.proxy_entry.pack(pady=5)

        self.proxy_type = tk.StringVar(value="http")
        ttk.Radiobutton(dialog, text="HTTP", variable=self.proxy_type, value="http").pack()
        ttk.Radiobutton(dialog, text="SOCKS5", variable=self.proxy_type, value="socks5").pack()

        ttk.Button(dialog, text="确定", command=lambda: self.save_proxy(dialog)).pack(pady=5)

    def save_proxy(self, dialog):
        """保存代理设置"""
        proxy = self.proxy_entry.get().strip()
        if not proxy:
            self.proxy_enabled = False
            self.proxies = None
            logging.info("已禁用代理")  # 添加日志
            dialog.destroy()
            return
    
        try:
            if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$", proxy):
                raise ValueError("无效的代理格式")
    
            proxy_type = self.proxy_type.get()
            if proxy_type == "socks5":
                self.proxies = {
                    "http": f"socks5://{proxy}",
                    "https": f"socks5://{proxy}"
                }
            else:
                self.proxies = {
                    "http": f"http://{proxy}",
                    "https": f"http://{proxy}"
                }
    
            self.proxy_enabled = True
            logging.info(f"代理设置成功: {proxy} ({proxy_type.upper()})")  # 添加日志
            
            # 如果已经设置了爬虫，更新爬虫的代理设置
            if hasattr(self, 'scraper') and self.scraper:
                proxy_url = self.proxies['http'].split('://')[-1]
                proxy_type = 'socks5' if 'socks5' in self.proxies['http'] else 'http'
                self.scraper.set_proxy(proxy_url, proxy_type)
                
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("代理错误", f"无效的代理设置: {str(e)}")
            
    def create_widgets(self):
        # 输入区域
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.grid(row=0, column=0, sticky="ew")

        self.control_frame = ttk.Frame(input_frame)
        self.control_frame.grid(row=1, column=0, columnspan=8, sticky="ew", pady=5)

        ttk.Label(input_frame, text="频道:").grid(row=0, column=0, sticky="w")
        self.city_entry = ttk.Entry(input_frame, width=20)
        self.city_entry.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="抓取深度:").grid(row=0, column=2, sticky="w")
        validate_cmd = input_frame.register(self.validate_spinbox_input)
        self.page_spin = ttk.Spinbox(input_frame, from_=1, to=self.max_page, width=5, validate="key",
                                     validatecommand=(validate_cmd, '%P'))
        self.page_spin.set(1)
        self.page_spin.grid(row=0, column=3, padx=5)

        # 随机模式选择框移到抓取深度后面
        self.random_mode_var = tk.BooleanVar(value=True)
        self.random_mode_check = ttk.Checkbutton(input_frame, text="随机模式", variable=self.random_mode_var)
        self.random_mode_check.grid(row=0, column=4, padx=5)

        self.speed_var = tk.BooleanVar()
        self.speed_check = ttk.Checkbutton(input_frame, text="启用测速", variable=self.speed_var)
        self.speed_check.grid(row=0, column=5, padx=5)

        self.start_btn = ttk.Button(input_frame, text="开始抓取", command=self.start_scraping)
        self.start_btn.grid(row=0, column=6, padx=5)

        # 结果展示区域
        result_frame = ttk.Frame(self.root, padding="10")
        result_frame.grid(row=1, column=0, sticky="nsew")

        self.tree = ttk.Treeview(result_frame, columns=('channel', 'url', 'response'), show='headings')
        self.tree.heading('channel', text='频道名称')
        self.tree.heading('url', text='URL')
        self.tree.heading('response', text='响应时间')
        self.tree.column('channel', width=150)
        self.tree.column('url', width=400)
        self.tree.column('response', width=100)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 日志区域
        log_frame = ttk.Frame(self.root, padding="10")
        log_frame.grid(row=2, column=0, sticky="ew")

        self.log_area = scrolledtext.ScrolledText(log_frame, width=80, height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # 底部按钮
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.grid(row=3, column=0, sticky="e")
        # 在现有按钮旁边添加新按钮
        self.export_txt_btn = ttk.Button(btn_frame, text="导出TXT",
                                      command=self.export_valid_txt,
                                      state=tk.DISABLED)
        self.export_txt_btn.pack(side=tk.RIGHT, padx=5)

        self.export_valid_btn = ttk.Button(btn_frame, text="导出有效节目", command=self.export_valid_results,
                                           state=tk.DISABLED)
        self.export_valid_btn.pack(side=tk.RIGHT, padx=5)

        self.save_btn = ttk.Button(btn_frame, text="导出全部节目", command=self.save_results, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT, padx=5)

        self.about_btn = ttk.Button(btn_frame, text="关于", command=self.show_about)
        self.about_btn.pack(side=tk.RIGHT, padx=5)

        # 配置网格布局权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="复制URL", command=self.copy_url)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def validate_spinbox_input(self, value):
        try:
            num = int(value)
            return 1 <= num <= self.max_page
        except ValueError:
            return len(value) == 0 or value == ""

    def show_context_menu(self, event):
        # 获取点击的item
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def copy_url(self):
        selected_item = self.tree.selection()
        if selected_item:
            url = self.tree.item(selected_item[0])['values'][1]
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            logging.info(f"已复制URL：{url}")

    def show_about(self):
        about_text = f"""频道工具

版本: {self.version}
作者: Skye
编译日期: 2025-03-09
更新:
1.新增了随机抓取功能
2.自动检测总页数
3.检测深度开放到5
4.修复了抓取实际只能抓一页的BUG

免责声明:
本工具仅供学习和研究使用，请勿用于任何商业用途。
使用本工具所产生的一切法律责任由使用者自行承担。
作者不对使用本工具导致的任何损失负责。"""
        messagebox.showinfo("关于", about_text)

    def export_valid_results(self):
        if not self.last_result or 'accessible_urls' not in self.last_result:
            messagebox.showwarning("警告", "没有可导出的有效节目数据")
            return

        filename = f"{self.last_result['city']}_valid_channels.json"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=filename,
            filetypes=[("JSON文件", "*.json")]
        )
        if filepath:
            try:
                valid_data = {
                    "city": self.last_result['city'],
                    "accessible_urls": self.last_result['accessible_urls']
                }
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(valid_data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("保存成功", f"文件已保存至：{filepath}")
            except Exception as e:
                messagebox.showerror("保存失败", f"文件写入错误: {str(e)}")

    def setup_logging(self):
        # 配置日志处理器
        class QueueHandler(logging.Handler):
            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue
        
            def emit(self, record):
                msg = self.format(record)
                self.log_queue.put(msg)
        
        # 创建并配置队列处理器
        qh = QueueHandler(self.log_queue)
        qh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # 直接添加到根日志记录器，与旧项目保持一致
        logging.getLogger().addHandler(qh)
        
        # 启动日志轮询
        self.poll_log_queue()
    
    def poll_log_queue(self):
        """轮询日志队列并更新GUI"""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.log_area.configure(state='normal')
                self.log_area.insert(tk.END, msg + '\n')
                self.log_area.configure(state='disabled')
                self.log_area.see(tk.END)
            except queue.Empty:
                break
        self.root.after(100, self.poll_log_queue)

    def save_results(self):
        if not self.last_result:
            messagebox.showwarning("警告", "没有可保存的结果")
            return

        filename = f"{self.last_result['city']}_result.json"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=filename,
            filetypes=[("JSON文件", "*.json")]
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.last_result, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("保存成功", f"文件已保存至：{filepath}")
            except Exception as e:
                messagebox.showerror("保存失败", f"文件写入错误: {str(e)}")

    def set_scrapers(self, scrapers):
        """设置多个抓取器"""
        self.scrapers = scrapers
        self.current_scraper = None
        
        # 添加源选择下拉框
        self.source_frame = ttk.LabelFrame(self.control_frame, text="数据源")
        self.source_frame.pack(fill="x", padx=5, pady=5)
        
        self.source_var = tk.StringVar(value="Tonkiang")
        self.source_dropdown = ttk.Combobox(
            self.source_frame, 
            textvariable=self.source_var,
            values=list(self.scrapers.keys()),
            state="readonly"
        )
        self.source_dropdown.pack(fill="x", padx=5, pady=5)
        self.source_dropdown.bind("<<ComboboxSelected>>", lambda e: self.set_scraper())
        
        # 初始化默认抓取器
        self.set_scraper()
    
    def set_scraper(self):
        """根据选择切换当前爬虫"""
        selected = self.source_var.get()
        self.current_scraper = self.scrapers[selected]
        # 设置self.scraper为当前选择的爬虫实例
        self.scraper = self.current_scraper
        
        # 更新界面元素
        if selected == "Tonkiang":
            self.page_spin.config(state="normal")
            self.random_mode_var.set(True)
        else:
            # Allinone的特定设置
            self.page_spin.config(state="disabled")
            self.random_mode_var.set(False)
        
        # 如果启用了代理,需要为新选择的爬虫设置代理
        if self.proxy_enabled and self.proxies:
            proxy_url = self.proxies['http'].split('://')[-1]
            proxy_type = 'socks5' if 'socks5' in self.proxies['http'] else 'http'
            self.current_scraper.set_proxy(proxy_url, proxy_type)

    def start_scraping(self):
        if self.running:
            messagebox.showwarning("警告", "已有任务正在运行")
            return

        if not self.scraper:
            messagebox.showerror("错误", "未设置爬虫实例")
            return

        keyword = self.city_entry.get()
        if not keyword:
            messagebox.showerror("错误", "请输入频道关键词")
            return

        try:
            page_count = int(self.page_spin.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的页数")
            return

        enable_speed_test = self.speed_var.get()
        random_mode = self.random_mode_var.get()
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())

        threading.Thread(
            target=self.run_scraping,
            args=(keyword, page_count, random_mode, enable_speed_test),
            daemon=True
        ).start()

    def run_scraping(self, keyword, page_count, random_mode, enable_speed_test):
        try:
            # 获取频道列表
            channels = self.scraper.fetch_channels(keyword, page_count, random_mode)
            if not channels:
                self.result_queue.put({"error": "未提取到频道信息"})
                return

            if enable_speed_test:
                # 检查频道可用性
                self.root.after(0, self._update_progress, "开始测速", 0, len(channels))
                logging.info("开始测速检查频道可用性")  # 添加日志
                accessible_channels = []
                total = len(channels)
                completed = 0

                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = {executor.submit(self.check_channel, channel): channel for channel in channels}
                    for future in as_completed(futures):
                        completed += 1
                        try:
                            channel, is_accessible = future.result(timeout=5)
                            if is_accessible:
                                accessible_channels.append(channel)
                                # 修改这里，使用 channel_name 而不是 name
                                logging.debug(f"频道可用: {channel.channel_name} - {channel.url}")
                        except Exception as e:
                            logging.warning(f"测速任务异常: {str(e)}")
                        finally:
                            self.root.after(0, self._update_progress, "测速中", completed, total)

                # 按响应时间排序
                accessible_channels.sort(key=lambda x: x.response_time)
                logging.info(f"测速完成，共 {len(accessible_channels)}/{total} 个频道可用")  # 添加日志

                result = {
                    "city": keyword,
                    "channels": channels,
                    "accessible_channels": accessible_channels
                }
            else:
                logging.info(f"未启用测速，共获取 {len(channels)} 个频道")  # 添加日志
                result = {
                    "city": keyword,
                    "channels": channels
                }

            self.result_queue.put(result)
            self.root.event_generate('<<ScrapingDone>>')

        except Exception as e:
            self.result_queue.put({"error": f"脚本执行失败: {str(e)}\n{traceback.format_exc()}"})
            self.root.event_generate('<<ScrapingDone>>')
        finally:
            self.running = False

    def channel_to_dict(self, channel):
        """将IPTVChannel对象转换为字典"""
        return {
            'channel_name': channel.channel_name,
            'url': channel.url,
            'date': channel.date,
            'location': channel.location,
            'resolution': channel.resolution,
            'response_time': channel.response_time
        }

    def check_channel(self, channel):
        """检查频道可用性"""
        is_accessible = self.scraper.check_channel_availability(channel)
        return channel, is_accessible

    def on_scraping_done(self, event):
        try:
            result = self.result_queue.get_nowait()  # 改为非阻塞获取
            if "error" in result:
                messagebox.showerror("错误", result["error"])
            else:
                self.last_result = result  # 存储结果到实例变量
                self.show_results(result)
                self.save_btn.config(state=tk.NORMAL)
                # 如果有可访问的URL，启用导出有效节目按钮
                if 'accessible_urls' in result and result['accessible_urls']:
                    self.export_valid_btn.config(state=tk.NORMAL)
                    self.export_txt_btn.config(state=tk.NORMAL)
                else:
                    self.export_valid_btn.config(state=tk.DISABLED)
                    self.export_txt_btn.config(state=tk.DISABLED)
        except queue.Empty:
            messagebox.showerror("错误", "未获取到有效结果")
        finally:
            self.start_btn.config(state=tk.NORMAL)

    def show_results(self, result):
        """显示结果到表格中"""
        # 清空现有结果
        self.tree.delete(*self.tree.get_children())
        
        # 获取要显示的频道列表
        channels_to_show = result.get('accessible_channels', result.get('channels', []))
        
        for channel in channels_to_show:
            values = (
                getattr(channel, 'channel_name', ''),
                getattr(channel, 'url', ''),
                f"{getattr(channel, 'response_time', 0):.3f}s" if hasattr(channel, 'response_time') else ''
            )
            
            self.tree.insert('', tk.END, values=values)