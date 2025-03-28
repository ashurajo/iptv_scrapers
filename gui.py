import json
import logging
import queue
import re
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
import traceback

from config import LOG_CONFIG
from speed_tester import SpeedTester

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
        self.scrapers = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="频道库抓取")

        self.blank_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.blank_tab, text="自定义抓取")

        self.about_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.about_tab, text="关于")

        ttk.Label(self.blank_tab, text="本功能正在开发，旨在实现自定义多个URL库，然后根据搜索词检测其中可用的源。", font=("黑体", 12)).pack(expand=True, pady=50)

        self.create_about_page()
        
        self.create_widgets()
        self.setup_logging()
        self.create_proxy_controls()
        self.progress_label = None
        self.create_progress_label()

        self.root.bind('<<ScrapingDone>>', self.on_scraping_done)
        
    def create_about_page(self):
        """创建关于页面"""
        about_frame = ttk.Frame(self.about_tab, padding=20)
        about_frame.pack(fill='both', expand=True)
        
        # 标题
        title_label = ttk.Label(about_frame, text="IPTV频道抓取工具", font=("黑体", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 版本信息
        version_label = ttk.Label(about_frame, text=f"版本: {self.version}", font=("黑体", 10))
        version_label.pack(pady=2)
        
        # 作者信息
        author_label = ttk.Label(about_frame, text="作者: Skye", font=("黑体", 10))
        author_label.pack(pady=2)
        
        # 编译日期
        build_label = ttk.Label(about_frame, text="编译日期: 2025-03-24", font=("黑体", 10))
        build_label.pack(pady=2)
        
        # 更新内容
        updates_frame = ttk.LabelFrame(about_frame, text="最近更新", padding=10)
        updates_frame.pack(fill='x', pady=10)
        
        updates = [
            "- 新增了IPTV365抓取方式",
            "- 修复了hacks检测源异常的问题",
            "- 修复了性能问题",
            "- 优化了界面"
        ]
        
        for update in updates:
            ttk.Label(updates_frame, text=update, font=("黑体", 9)).pack(anchor='w', pady=1)
        
        
        # 免费软件声明
        disclaimer_frame = ttk.LabelFrame(about_frame, text="免费软件声明", padding=10)
        disclaimer_frame.pack(fill='x', pady=10)
        
        disclaimers = [
            "本软件为免费软件，仅供学习和研究使用。",
            "使用本软件时请遵守当地法律法规。",
            "开发者不对使用本软件产生的任何后果负责。",
            "禁止将本软件用于任何商业用途。"
        ]
        
        for disclaimer in disclaimers:
            ttk.Label(disclaimer_frame, text=disclaimer, font=("黑体", 9)).pack(anchor='w', pady=1)
                # 开源信息
        repo_frame = ttk.Frame(about_frame)
        repo_frame.pack(fill='x', pady=10)
        
        repo_label = ttk.Label(repo_frame, text="开源地址: ", font=("黑体", 10))
        repo_label.pack(side='left')
        
        repo_link = ttk.Label(repo_frame, text="https://github.com/tjqj/iptv_scrapers", 
                             font=("黑体", 10), foreground="blue", cursor="hand2")
        repo_link.pack(side='left')
        repo_link.bind("<Button-1>", lambda e: self.open_url("https://github.com/tjqj/iptv_scrapers"))
        
        # 请求Star
        star_frame = ttk.Frame(about_frame)
        star_frame.pack(fill='x', pady=5)
        
        star_label = ttk.Label(star_frame, 
                              text="如果您觉得这个工具有用，请在 GitHub 上给我一个Star ⭐", 
                              font=("黑体", 10))
        star_label.pack()
        
        # 联系作者
        contact_label = ttk.Label(about_frame, text="联系作者: https://github.com/tjqj/iptv_scrapers/issues", font=("黑体", 10))
        contact_label.pack(pady=5)

        # 开源协议
        license_label = ttk.Label(about_frame, text="开源协议: MIT License", font=("黑体", 10))
        license_label.pack(pady=5)

    
    
    def open_url(self, url):
        """打开URL链接"""
        import webbrowser
        webbrowser.open(url)

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
        log_frame = self.main_tab.grid_slaves(row=2, column=0)[0]
        self.progress_label = ttk.Label(log_frame, text="就绪")
        self.progress_label.pack(anchor="se")  # 固定在右下角
        
    def create_proxy_controls(self):
        input_frame = self.main_tab.grid_slaves(row=0, column=0)[0]
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
            logging.info("已禁用代理")
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
            logging.info(f"代理设置成功: {proxy} ({proxy_type.upper()})")

            if hasattr(self, 'scraper') and self.scraper:
                proxy_url = self.proxies['http'].split('://')[-1]
                proxy_type = 'socks5' if 'socks5' in self.proxies['http'] else 'http'
                self.scraper.set_proxy(proxy_url, proxy_type)
                
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("代理错误", f"无效的代理设置: {str(e)}")
            
    def create_widgets(self):

        input_frame = ttk.Frame(self.main_tab, padding="10")
        input_frame.grid(row=0, column=0, sticky="ew")
        
        # 设置main_tab的列权重，使其可以水平拉伸
        self.main_tab.columnconfigure(0, weight=1)
        self.main_tab.rowconfigure(1, weight=1)

        self.control_frame = ttk.Frame(input_frame)
        self.control_frame.grid(row=1, column=0, columnspan=8, sticky="ew", pady=5)
        
        # 设置input_frame的列权重，使其内部控件可以水平拉伸
        for i in range(8):
            input_frame.columnconfigure(i, weight=1)

        ttk.Label(input_frame, text="频道:").grid(row=0, column=0, sticky="w")
        self.city_entry = ttk.Entry(input_frame, width=20)
        self.city_entry.grid(row=0, column=1, padx=5, sticky="ew")

        ttk.Label(input_frame, text="抓取深度:").grid(row=0, column=2, sticky="w")
        validate_cmd = input_frame.register(self.validate_spinbox_input)
        self.page_spin = ttk.Spinbox(input_frame, from_=1, to=self.max_page, width=5, validate="key",
                                     validatecommand=(validate_cmd, '%P'))
        self.page_spin.set(1)
        self.page_spin.grid(row=0, column=3, padx=5, sticky="ew")

        self.random_mode_var = tk.BooleanVar(value=True)
        self.random_mode_check = ttk.Checkbutton(input_frame, text="随机模式", variable=self.random_mode_var)
        self.random_mode_check.grid(row=0, column=4, padx=5, sticky="ew")

        self.speed_var = tk.BooleanVar()
        self.speed_check = ttk.Checkbutton(input_frame, text="启用测速", variable=self.speed_var)
        self.speed_check.grid(row=0, column=5, padx=5, sticky="ew")

        self.start_btn = ttk.Button(input_frame, text="开始抓取", command=self.start_scraping)
        self.start_btn.grid(row=0, column=6, padx=5, sticky="ew")

        result_frame = ttk.LabelFrame(self.main_tab, padding="10", text="频道列表")
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

        log_frame = ttk.LabelFrame(self.main_tab, padding="10", text="日志信息")
        log_frame.grid(row=2, column=0, sticky="ew")

        self.log_area = scrolledtext.ScrolledText(log_frame, width=80, height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(self.main_tab, padding="10")
        btn_frame.grid(row=3, column=0, sticky="e")

        self.export_txt_btn = ttk.Button(btn_frame, text="导出TXT",
                                      command=self.export_valid_txt,
                                      state=tk.DISABLED)
        self.export_txt_btn.pack(side=tk.RIGHT, padx=5)

        self.export_valid_btn = ttk.Button(btn_frame, text="导出有效节目", command=self.export_valid_results,
                                           state=tk.DISABLED)
        self.export_valid_btn.pack(side=tk.RIGHT, padx=5)

        self.save_btn = ttk.Button(btn_frame, text="导出全部节目", command=self.save_results, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT, padx=5)

        self.main_tab.columnconfigure(0, weight=1)
        self.main_tab.rowconfigure(1, weight=1)

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
        class QueueHandler(logging.Handler):
            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue
        
            def emit(self, record):
                msg = self.format(record)
                self.log_queue.put(msg)

        qh = QueueHandler(self.log_queue)
        qh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        logging.getLogger().addHandler(qh)

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
                # 创建可序列化的结果副本
                serializable_result = self.last_result.copy()
                
                # 转换channels列表中的IPTVChannel对象为字典
                if 'channels' in serializable_result:
                    serializable_result['channels'] = [
                        self.channel_to_dict(channel) for channel in serializable_result['channels']
                    ]
                
                # 转换accessible_channels列表中的IPTVChannel对象为字典(如果存在)
                if 'accessible_channels' in serializable_result:
                    serializable_result['accessible_channels'] = [
                        self.channel_to_dict(channel) for channel in serializable_result['accessible_channels']
                    ]
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(serializable_result, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("保存成功", f"文件已保存至：{filepath}")
            except Exception as e:
                messagebox.showerror("保存失败", f"文件写入错误: {str(e)}")

    def set_scrapers(self, scrapers):
        """设置多个抓取器"""
        self.scrapers = scrapers
        self.current_scraper = None

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

        self.set_scraper()
    
    def set_scraper(self):
        """根据选择切换当前爬虫"""
        selected = self.source_var.get()
        self.current_scraper = self.scrapers[selected]
        self.scraper = self.current_scraper
        
        # 更新界面元素
        if selected == "Tonkiang":
            self.page_spin.config(state="normal")
            self.random_mode_check.config(state="normal")
            self.random_mode_var.set(True)
        elif selected == "Allinone":
            self.page_spin.config(state="normal")
            self.random_mode_check.config(state="normal")
            self.random_mode_var.set(True)
        elif selected == "Hacks":
            self.page_spin.config(state="disabled")
            self.random_mode_check.config(state="disabled")
            self.random_mode_var.set(False)
        elif selected == "IPTV365":
            self.page_spin.config(state="disabled")
            self.random_mode_check.config(state="disabled")
            self.random_mode_var.set(False)
        else:
            self.page_spin.config(state="disabled")
            self.random_mode_var.set(False)

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
            channels = self.scraper.fetch_channels(keyword, page_count, random_mode)
            if not channels:
                self.result_queue.put({"error": "未提取到频道信息"})
                return

            if enable_speed_test:
                # 使用SpeedTester进行测速
                speed_tester = SpeedTester(
                    scraper=self.scraper,
                    progress_callback=lambda status, current, total: self.root.after(0, self._update_progress, status, current, total)
                )
                accessible_channels, stats = speed_tester.test_channels(channels)

                accessible_urls = [self.channel_to_dict(channel) for channel in accessible_channels]
                
                result = {
                    "city": keyword,
                    "channels": channels,
                    "accessible_channels": accessible_channels,
                    "accessible_urls": accessible_urls,
                    "stats": stats
                }
            else:
                logging.info(f"未启用测速，共获取 {len(channels)} 个频道")
                # 添加转换为字典的步骤，以便未测速时也能导出
                channels_dict = [self.channel_to_dict(channel) for channel in channels]
                result = {
                    "city": keyword,
                    "channels": channels,
                    "accessible_urls": channels_dict  # 未测速时，所有频道都视为可访问
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
        """抓取完成后的回调"""
        self.start_btn.config(text="开始抓取", state=tk.NORMAL)
        
        try:
            result = self.result_queue.get_nowait()
            if "error" in result:
                messagebox.showerror("错误", result["error"])
                return
                
            self.last_result = result
            self.show_results(result)
            
            # 启用导出按钮 - 根据不同情况启用不同按钮
            if 'stats' in result and 'accessible_urls' in result:
                # 启用测速的情况下，所有导出按钮都可用
                self.export_valid_btn.config(state=tk.NORMAL)
                self.export_txt_btn.config(state=tk.NORMAL)
                self.save_btn.config(state=tk.NORMAL)
            else:
                # 未启用测速的情况下，只启用导出全部和保存按钮，不启用导出有效节目按钮
                self.export_valid_btn.config(state=tk.DISABLED)
                self.export_txt_btn.config(state=tk.NORMAL)
                self.save_btn.config(state=tk.NORMAL)
                
            # 显示统计信息
            if "stats" in result:
                stats = result["stats"]
                messagebox.showinfo("抓取完成", 
                    f"共抓取 {stats['total']} 个频道，其中 {stats['accessible']} 个可用")
            else:
                # 未测速时显示总数
                total = len(result.get('channels', []))
                messagebox.showinfo("抓取完成", f"共抓取 {total} 个频道")
                
        except queue.Empty:
            messagebox.showerror("错误", "未获取到有效结果")
        finally:
            self.start_btn.config(state=tk.NORMAL)

    def show_results(self, result):
        """显示结果到表格中"""
        self.tree.delete(*self.tree.get_children())
        
        # 优先显示测速后的可访问频道，如果没有测速则显示所有频道
        if 'accessible_channels' in result:
            channels_to_show = result.get('accessible_channels', [])
        else:
            channels_to_show = result.get('channels', [])
        
        for channel in channels_to_show:
            values = (
                getattr(channel, 'channel_name', ''),
                getattr(channel, 'url', ''),
                f"{getattr(channel, 'response_time', 0):.3f}s" if hasattr(channel, 'response_time') and channel.response_time else ''
            )
            
            self.tree.insert('', tk.END, values=values)
