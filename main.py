#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOL 打野练习计时器 - 终极美化版
现代化的游戏风格UI设计
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import threading
from auto_backend import AutoMonitorCoordinator
from live_client_timer import LiveClientTimer

# 视觉识别模块（可选）
try:
    from vision_timer import VisionTimer
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False


class GlowButton(tk.Canvas):
    """发光按钮组件"""
    def __init__(self, parent, text, command=None, width=140, height=50,
                 bg_color="#C89B3C", fg_color="#FFFFFF", font_size=12,
                 glow_color=None, **kwargs):
        super().__init__(parent, width=width, height=height,
                        highlightthickness=0, bd=0, **kwargs)

        self.bg_color = bg_color
        self.fg_color = fg_color
        self.glow_color = glow_color or bg_color
        self.command = command
        self.text = text
        self.font_size = font_size
        self.is_pressed = False
        self.is_disabled = False

        self.normal_fill = bg_color
        self.hover_fill = self._mix_color(bg_color, "#FFFFFF", 0.12)
        self.pressed_fill = self._mix_color(bg_color, "#000000", 0.18)
        self.disabled_fill = "#1B2738"
        self.disabled_text = "#5F738D"

        # 阴影和按钮主体
        self.shadow_id = self._create_rounded_rect(
            4, 5, width - 4, height - 2, 12, self._mix_color(bg_color, "#000000", 0.55)
        )
        self.btn_id = self._create_rounded_rect(4, 3, width - 4, height - 4, 12, bg_color)
        self.border_id = self._create_rounded_rect(
            4, 3, width - 4, height - 4, 12, "",
            outline=self._mix_color(bg_color, "#FFFFFF", 0.35), width=1
        )
        self.create_line(
            16, 11, width - 16, 11,
            fill=self._mix_color(bg_color, "#FFFFFF", 0.55), width=1
        )

        # 创建文字
        self.text_id = self.create_text(
            width // 2, height // 2,
            text=text,
            font=("Segoe UI", font_size, "bold"),
            fill=fg_color
        )

        # 绑定事件
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _create_rounded_rect(self, x1, y1, x2, y2, radius, color, outline="", width=0):
        points = [
            x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius, x1, y1+radius, x1, y1
        ]
        return self.create_polygon(
            points, smooth=True, fill=color, outline=outline, width=width
        )

    def _mix_color(self, source, target, ratio):
        r1, g1, b1 = int(source[1:3], 16), int(source[3:5], 16), int(source[5:7], 16)
        r2, g2, b2 = int(target[1:3], 16), int(target[3:5], 16), int(target[5:7], 16)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _on_enter(self, event):
        if not self.is_disabled and not self.is_pressed:
            self.itemconfig(self.btn_id, fill=self.hover_fill)
            self.config(cursor="hand2")

    def _on_leave(self, event):
        if not self.is_disabled:
            self.itemconfig(self.btn_id, fill=self.normal_fill)
            self.is_pressed = False

    def _on_press(self, event):
        if not self.is_disabled:
            self.is_pressed = True
            self.itemconfig(self.btn_id, fill=self.pressed_fill)

    def _on_release(self, event):
        if not self.is_disabled and self.is_pressed:
            self.is_pressed = False
            self.itemconfig(self.btn_id, fill=self.hover_fill)
            if self.command:
                self.command()

    def set_text(self, text):
        self.itemconfig(self.text_id, text=text)

    def set_state(self, state):
        self.is_disabled = (state == "disabled")
        if self.is_disabled:
            self.itemconfig(self.btn_id, fill=self.disabled_fill)
            self.itemconfig(self.border_id, outline=self._mix_color(self.disabled_fill, "#FFFFFF", 0.18))
            self.itemconfig(self.text_id, fill=self.disabled_text)
        else:
            self.itemconfig(self.btn_id, fill=self.normal_fill)
            self.itemconfig(self.border_id, outline=self._mix_color(self.bg_color, "#FFFFFF", 0.35))
            self.itemconfig(self.text_id, fill=self.fg_color)


class CampButton(tk.Canvas):
    """野怪营地按钮 - 电竞信息卡片风格"""

    def __init__(self, parent, camp_data, command=None, **kwargs):
        self.camp = camp_data
        width, height = 132, 96
        super().__init__(parent, width=width, height=height,
                        highlightthickness=0, bd=0, bg="#0B111A", **kwargs)

        self.command = command
        self.is_recorded = False
        self.base_bg = "#182433"
        self.hover_bg = "#24354D"
        self.base_border = "#324B67"

        # 外发光（默认隐藏）
        self.glow = self.create_rounded_rect(2, 2, width - 2, height - 2, 16, "")

        # 卡片背景
        self.bg = self.create_rounded_rect(5, 5, width - 5, height - 5, 14, self.base_bg)

        # 边框
        self.border = self.create_rounded_rect(
            5, 5, width - 5, height - 5, 14, "",
            outline=self.base_border, width=2
        )
        self.highlight = self.create_line(
            20, 13, width - 20, 13, fill="#4A6687", width=1
        )

        # 图标
        self.icon_id = self.create_text(
            width // 2, 37,
            text=camp_data["icon"],
            font=("Segoe UI Emoji", 32)
        )

        # 名称
        self.name_id = self.create_text(
            width // 2, 73,
            text=camp_data["name"],
            font=("Segoe UI", 11, "bold"),
            fill="#EAF4FF"
        )

        # 时间显示（初始隐藏）
        self.time_id = self.create_text(
            width // 2, 73,
            text="",
            font=("Consolas", 12, "bold"),
            fill="#9EE9FF",
            state="hidden"
        )

        # 绑定事件
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def create_rounded_rect(self, x1, y1, x2, y2, radius, fill, outline="", width=0):
        points = [
            x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius, x1, y1+radius, x1, y1
        ]
        return self.create_polygon(points, smooth=True, fill=fill, outline=outline, width=width)

    def mix_color(self, source, target, ratio):
        r1, g1, b1 = int(source[1:3], 16), int(source[3:5], 16), int(source[5:7], 16)
        r2, g2, b2 = int(target[1:3], 16), int(target[3:5], 16), int(target[5:7], 16)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    def on_enter(self, event):
        if not self.is_recorded:
            self.itemconfig(self.bg, fill=self.hover_bg)
            self.itemconfig(self.border, outline="#00CFFF")
            self.itemconfig(self.highlight, fill="#8BE9FF")
            self.config(cursor="hand2")

    def on_leave(self, event):
        if not self.is_recorded:
            self.itemconfig(self.bg, fill=self.base_bg)
            self.itemconfig(self.border, outline=self.base_border)
            self.itemconfig(self.highlight, fill="#4A6687")

    def on_click(self, event):
        if not self.is_recorded and self.command:
            self.command()

    def record(self, time_str):
        """标记为已记录"""
        self.is_recorded = True
        color = self.camp["color"]
        self.itemconfig(self.glow, fill=self.mix_color(color, "#FFFFFF", 0.18))
        self.itemconfig(self.bg, fill=self.mix_color(color, "#0A1018", 0.64))
        self.itemconfig(self.border, outline=self.mix_color(color, "#FFFFFF", 0.1), width=2)
        self.itemconfig(self.highlight, fill=self.mix_color(color, "#FFFFFF", 0.45))
        self.itemconfig(self.name_id, state="hidden")
        self.itemconfig(self.time_id, text=time_str, state="normal")
        self.unbind("<Enter>")
        self.unbind("<Leave>")

    def reset(self):
        """重置状态"""
        self.is_recorded = False
        self.itemconfig(self.glow, fill="")
        self.itemconfig(self.bg, fill=self.base_bg)
        self.itemconfig(self.border, outline=self.base_border, width=2)
        self.itemconfig(self.highlight, fill="#4A6687")
        self.itemconfig(self.name_id, state="normal")
        self.itemconfig(self.time_id, state="hidden")
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)


class JungleTimer:
    """打野计时器主类 - 终极美化版"""
    
    # 野怪营地配置
    CAMPS = {
        "red_buff": {"name": "红BUFF", "icon": "🔴", "color": "#FF6B6B"},
        "krugs": {"name": "石头人", "icon": "🪨", "color": "#8B7355"},
        "raptors": {"name": "F6", "icon": "🦅", "color": "#FFB347"},
        "wolves": {"name": "三狼", "icon": "🐺", "color": "#A9A9A9"},
        "blue_buff": {"name": "蓝BUFF", "icon": "🔵", "color": "#4ECDC4"},
        "gromp": {"name": "青蛙", "icon": "🐸", "color": "#50C878"},
        "scuttle_top": {"name": "上河蟹", "icon": "🦀", "color": "#40E0D0"},
        "scuttle_bot": {"name": "下河蟹", "icon": "🦀", "color": "#40E0D0"},
    }
    
    # 预设路线
    ROUTES = {
        "red_full": {
            "name": "红开全清",
            "camps": ["red_buff", "krugs", "raptors", "wolves", "blue_buff", "gromp"]
        },
        "blue_full": {
            "name": "蓝开全清", 
            "camps": ["blue_buff", "gromp", "wolves", "raptors", "krugs", "red_buff"]
        },
        "red_blue": {
            "name": "红→蓝",
            "camps": ["red_buff", "krugs", "raptors", "wolves", "blue_buff"]
        },
        "blue_red": {
            "name": "蓝→红",
            "camps": ["blue_buff", "gromp", "wolves", "raptors", "red_buff"]
        },
        "custom": {
            "name": "自定义",
            "camps": []
        }
    }
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LOL Jungle Timer Pro")
        self.root.geometry("1100x850")
        self.root.minsize(1000, 750)
        self.root.configure(bg="#070C14")

        # 主题色
        self.colors = {
            "bg": "#070C14",
            "card": "#111A28",
            "card_hover": "#1A2738",
            "gold": "#54D2FF",
            "gold_light": "#C7F5FF",
            "blue": "#00CFFF",
            "green": "#3EE89B",
            "red": "#FF5B7B",
            "orange": "#FFB45A",
            "text": "#E7F1FF",
            "text_secondary": "#84A0BE",
            "border": "#2A3D55"
        }

        # 计时器状态
        self.start_time = None
        self.pause_time = None
        self.is_running = False
        self.current_route = "red_full"
        self.route_options = {route["name"]: key for key, route in self.ROUTES.items()}
        self.camp_times = {}
        
        # 历史记录
        self.history_file = os.path.join(os.path.dirname(__file__), "history.json")
        self.history = self.load_history()
        
        # 创建UI
        self.create_styles()
        self.create_widgets()
        self.update_timer()
        self.bind_shortcuts()
        
    def create_styles(self):
        """创建自定义样式"""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # 下拉菜单样式
        self.style.configure("Game.TCombobox",
                           fieldbackground=self.colors["card_hover"],
                           background=self.colors["card_hover"],
                           foreground=self.colors["text"],
                           arrowcolor=self.colors["blue"],
                           bordercolor=self.colors["border"],
                           lightcolor=self.colors["card_hover"],
                           darkcolor=self.colors["card_hover"],
                           relief="flat",
                           padding=5)

        self.style.map("Game.TCombobox",
                      fieldbackground=[("readonly", self.colors["card_hover"])],
                      background=[("readonly", self.colors["card_hover"])],
                      foreground=[("readonly", self.colors["text"])],
                      selectbackground=[("readonly", self.colors["blue"])],
                      selectforeground=[("readonly", self.colors["bg"])])

        # 复选框样式
        self.style.configure("Game.TCheckbutton",
                           background=self.colors["card"],
                           foreground=self.colors["blue"],
                           font=("Segoe UI", 11))

    def create_widgets(self):
        """创建界面组件"""
        # 主容器 - 使用Frame实现层次感
        main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=26, pady=22)

        # ========== 顶部标题区 ==========
        self.create_header(main_frame)

        # ========== 计时器卡片 ==========
        self.create_timer_section(main_frame)

        # ========== 控制按钮区 ==========
        self.create_control_section(main_frame)

        # ========== 野怪营地卡片 ==========
        self.create_camps_section(main_frame)

        # ========== 底部信息区 ==========
        self.create_footer_section(main_frame)

    def create_header(self, parent):
        """创建顶部标题"""
        header = tk.Frame(
            parent,
            bg=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0
        )
        header.pack(fill=tk.X, pady=(0, 16))

        header_inner = tk.Frame(header, bg=self.colors["card"])
        header_inner.pack(fill=tk.X, padx=22, pady=16)

        # 左侧：Logo和标题
        title_frame = tk.Frame(header_inner, bg=self.colors["card"])
        title_frame.pack(side=tk.LEFT)

        # Logo图标
        logo_label = tk.Label(
            title_frame,
            text="⚔️",
            font=("Segoe UI Emoji", 36),
            bg=self.colors["card"],
            fg=self.colors["blue"]
        )
        logo_label.pack(side=tk.LEFT, padx=(0, 15))

        # 标题文字
        text_frame = tk.Frame(title_frame, bg=self.colors["card"])
        text_frame.pack(side=tk.LEFT)

        tk.Label(
            text_frame,
            text="JUNGLE TIMER",
            font=("Segoe UI", 24, "bold"),
            bg=self.colors["card"],
            fg=self.colors["gold_light"]
        ).pack(anchor="w")

        tk.Label(
            text_frame,
            text="League Practice Assistant",
            font=("Segoe UI", 11),
            bg=self.colors["card"],
            fg=self.colors["text_secondary"]
        ).pack(anchor="w")

        # 右侧：路线选择
        route_frame = tk.Frame(
            header_inner,
            bg=self.colors["card_hover"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=12,
            pady=8
        )
        route_frame.pack(side=tk.RIGHT)

        tk.Label(
            route_frame,
            text="打野路线",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["card_hover"],
            fg=self.colors["text_secondary"]
        ).pack(anchor="e")

        self.route_var = tk.StringVar(value=self.ROUTES[self.current_route]["name"])
        route_menu = ttk.Combobox(
            route_frame,
            textvariable=self.route_var,
            values=list(self.route_options.keys()),
            state="readonly",
            width=15,
            font=("Segoe UI", 11),
            style="Game.TCombobox"
        )
        route_menu.pack(pady=(5, 0))
        route_menu.bind("<<ComboboxSelected>>", self.on_route_change)

    def create_timer_section(self, parent):
        """创建计时器区域"""
        timer_card = tk.Frame(
            parent,
            bg=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0
        )
        timer_card.pack(fill=tk.X, pady=12)

        inner = tk.Frame(timer_card, bg=self.colors["card"])
        inner.pack(fill=tk.X, padx=40, pady=24)

        self.route_badge = tk.Label(
            inner,
            text=f"ROUTE   {self.ROUTES[self.current_route]['name']}",
            font=("Consolas", 11, "bold"),
            bg=self.colors["card"],
            fg=self.colors["blue"]
        )
        self.route_badge.pack()

        # 大计时器显示
        self.timer_label = tk.Label(
            inner,
            text="00:00.00",
            font=("Consolas", 74, "bold"),
            bg=self.colors["card"],
            fg=self.colors["gold"]
        )
        self.timer_label.pack(pady=(6, 0))

        # 状态指示器胶囊
        status_frame = tk.Frame(
            inner,
            bg=self.colors["card_hover"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=14,
            pady=8
        )
        status_frame.pack(pady=(12, 0))

        self.status_dot = tk.Canvas(status_frame, width=10, height=10,
                                   bg=self.colors["card_hover"], highlightthickness=0)
        self.status_dot.pack(side=tk.LEFT)
        self.status_dot.create_oval(0, 0, 10, 10, fill=self.colors["border"], outline="")

        self.status_label = tk.Label(
            status_frame,
            text="准备就绪",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["card_hover"],
            fg=self.colors["text_secondary"]
        )
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))

        # 自动监控选项
        self.create_vision_controls(inner)

    def create_vision_controls(self, parent):
        """创建自动监控控制"""
        vision_frame = tk.Frame(
            parent,
            bg=self.colors["card_hover"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            pady=12,
            padx=14
        )
        vision_frame.pack(fill=tk.X, pady=(16, 0))

        # 左侧：开关
        left_frame = tk.Frame(vision_frame, bg=self.colors["card_hover"])
        left_frame.pack(side=tk.LEFT)

        self.vision_enabled = tk.BooleanVar(value=False)
        vision_check = tk.Checkbutton(
            left_frame,
            text="🤖 自动监控",
            variable=self.vision_enabled,
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["card_hover"],
            fg=self.colors["blue"],
            selectcolor=self.colors["bg"],
            activebackground=self.colors["card_hover"],
            activeforeground=self.colors["blue"],
            command=self.toggle_vision
        )
        vision_check.pack(side=tk.LEFT)

        # 自动监控说明
        tk.Label(
            left_frame,
            text="优先 Riot API → 回退视觉识别",
            font=("Segoe UI", 10),
            bg=self.colors["card_hover"],
            fg=self.colors["text_secondary"]
        ).pack(side=tk.LEFT, padx=(10, 0))

        # 状态标签
        self.vision_status = tk.Label(
            left_frame,
            text="[未启用]",
            font=("Segoe UI", 10),
            bg=self.colors["card_hover"],
            fg=self.colors["text_secondary"]
        )
        self.vision_status.pack(side=tk.LEFT, padx=(15, 0))

        # 右侧：分辨率选择
        right_frame = tk.Frame(vision_frame, bg=self.colors["card_hover"])
        right_frame.pack(side=tk.RIGHT)

        tk.Label(
            right_frame,
            text="视觉分辨率:",
            font=("Segoe UI", 10),
            bg=self.colors["card_hover"],
            fg=self.colors["text_secondary"]
        ).pack(side=tk.LEFT)

        self.resolution_var = tk.StringVar(value="1920x1080")
        self.res_menu = ttk.Combobox(
            right_frame,
            textvariable=self.resolution_var,
            values=["1920x1080", "2560x1440", "3840x2160", "其他"],
            state="readonly",
            width=12,
            font=("Segoe UI", 10),
            style="Game.TCombobox"
        )
        self.res_menu.pack(side=tk.LEFT, padx=(5, 0))
        self.res_menu.bind("<<ComboboxSelected>>", self.on_resolution_change)
        if not VISION_AVAILABLE:
            self.res_menu.config(state="disabled")

        # 初始化自动监控
        self.vision_timer = None
        self.live_client_timer = None
        self.auto_monitor = None
        self.active_auto_backend = None
        self.init_live_client_timer()
        self.init_vision_timer()
        self.init_auto_monitor()

    def create_control_section(self, parent):
        """创建控制按钮区域"""
        control_frame = tk.Frame(
            parent,
            bg=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0
        )
        control_frame.pack(fill=tk.X, pady=12)

        inner = tk.Frame(control_frame, bg=self.colors["card"])
        inner.pack(fill=tk.X, padx=22, pady=18)

        tk.Label(
            inner,
            text="CONTROL",
            font=("Consolas", 11, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text_secondary"]
        ).pack(anchor="w")

        # 按钮容器
        btn_container = tk.Frame(inner, bg=self.colors["card"])
        btn_container.pack(pady=(10, 0))

        # 开始按钮
        self.start_btn = GlowButton(
            btn_container,
            text="▶ 开始",
            command=self.start_timer,
            width=150, height=54,
            bg_color=self.colors["green"],
            font_size=14
        )
        self.start_btn.pack(side=tk.LEFT, padx=9)

        # 暂停按钮
        self.pause_btn = GlowButton(
            btn_container,
            text="⏸ 暂停",
            command=self.pause_timer,
            width=130, height=54,
            bg_color=self.colors["orange"],
            font_size=14
        )
        self.pause_btn.pack(side=tk.LEFT, padx=9)
        self.pause_btn.set_state("disabled")

        # 重置按钮
        self.reset_btn = GlowButton(
            btn_container,
            text="⏹ 重置",
            command=self.reset_timer,
            width=130, height=54,
            bg_color=self.colors["red"],
            font_size=14
        )
        self.reset_btn.pack(side=tk.LEFT, padx=9)

        # 完成按钮
        self.complete_btn = GlowButton(
            btn_container,
            text="✓ 完成 (F4)",
            command=self.manual_complete,
            width=148, height=54,
            bg_color="#2A89C8",
            font_size=14
        )
        self.complete_btn.pack(side=tk.LEFT, padx=9)

        # 快捷键提示
        shortcut_frame = tk.Frame(inner, bg=self.colors["card"])
        shortcut_frame.pack(pady=(16, 0))

        shortcuts = [
            ("F1", "开始"),
            ("F2", "暂停"),
            ("F3", "重置"),
            ("F4", "完成")
        ]

        for key, desc in shortcuts:
            frame = tk.Frame(
                shortcut_frame,
                bg=self.colors["card_hover"],
                highlightbackground=self.colors["border"],
                highlightthickness=1,
                padx=10,
                pady=5
            )
            frame.pack(side=tk.LEFT, padx=6)

            tk.Label(frame, text=key, font=("Consolas", 11, "bold"),
                    bg=self.colors["card_hover"], fg=self.colors["blue"]).pack(side=tk.LEFT)
            tk.Label(frame, text=f" {desc}", font=("Segoe UI", 10),
                    bg=self.colors["card_hover"], fg=self.colors["text_secondary"]).pack(side=tk.LEFT)

    def create_camps_section(self, parent):
        """创建野怪营地区域"""
        # 区域标题
        camps_header = tk.Frame(parent, bg=self.colors["bg"])
        camps_header.pack(fill=tk.X, pady=(8, 10))

        tk.Label(
            camps_header,
            text="野怪营地",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["gold_light"]
        ).pack(side=tk.LEFT)

        tk.Label(
            camps_header,
            text="点击记录完成时间",
            font=("Segoe UI", 11),
            bg=self.colors["bg"],
            fg=self.colors["text_secondary"]
        ).pack(side=tk.LEFT, padx=(15, 0))

        # 营地按钮容器
        camps_panel = tk.Frame(
            parent,
            bg=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0
        )
        camps_panel.pack(fill=tk.BOTH, expand=True)

        self.camps_container = tk.Frame(camps_panel, bg=self.colors["card"])
        self.camps_container.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        self.update_camp_buttons()

    def create_footer_section(self, parent):
        """创建底部信息区域"""
        footer_frame = tk.Frame(parent, bg=self.colors["bg"])
        footer_frame.pack(fill=tk.X, pady=(14, 0))

        # 统计面板
        stats_panel = tk.Frame(
            footer_frame,
            bg=self.colors["card"],
            padx=18,
            pady=14,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        stats_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(
            stats_panel,
            text="📊 本次统计",
            font=("Segoe UI", 13, "bold"),
            bg=self.colors["card"],
            fg=self.colors["gold_light"]
        ).pack(anchor="w")

        self.stats_text = tk.Text(
            stats_panel,
            height=6,
            font=("Consolas", 11),
            bg=self.colors["card_hover"],
            fg=self.colors["text"],
            bd=0,
            highlightthickness=0,
            state=tk.DISABLED
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # 快捷操作面板
        menu_panel = tk.Frame(
            footer_frame,
            bg=self.colors["card"],
            padx=18,
            pady=14,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        menu_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))

        tk.Label(
            menu_panel,
            text="⚡ 快捷操作",
            font=("Segoe UI", 13, "bold"),
            bg=self.colors["card"],
            fg=self.colors["gold_light"]
        ).pack(anchor="w")

        menu_items = [
            ("📜 历史记录", self.show_history),
            ("📤 导出数据", self.export_data),
        ]

        if VISION_AVAILABLE:
            menu_items.extend([
                ("👁️ 校准视觉", self.test_vision_calibration),
                ("▶️ 测试识别", self.test_vision_preview),
            ])

        menu_items.append(("❓ 使用帮助", self.show_help))

        for text, cmd in menu_items:
            btn = tk.Label(
                menu_panel,
                text=text,
                font=("Segoe UI", 11),
                bg=self.colors["card"],
                fg=self.colors["blue"],
                cursor="hand2"
            )
            btn.pack(anchor="w", pady=6)
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=self.colors["gold_light"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(fg=self.colors["blue"]))
            btn.bind("<Button-1>", lambda e, c=cmd: c())

        # 自动结束开关
        auto_frame = tk.Frame(menu_panel, bg=self.colors["card"], pady=10)
        auto_frame.pack(fill=tk.X)

        self.auto_complete = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(
            auto_frame,
            text="自动结束",
            variable=self.auto_complete,
            font=("Segoe UI", 10),
            bg=self.colors["card"],
            fg=self.colors["text_secondary"],
            selectcolor=self.colors["bg"],
            activebackground=self.colors["card"],
            activeforeground=self.colors["text"]
        )
        auto_check.pack(anchor="w")

    def update_camp_buttons(self):
        """更新营地按钮"""
        for widget in self.camps_container.winfo_children():
            widget.destroy()

        self.camp_buttons = {}

        route = self.ROUTES[self.current_route]
        camps = route["camps"]

        if not camps:
            tk.Label(
                self.camps_container,
                text="自定义模式",
                font=("Segoe UI", 14),
                bg=self.colors["card"],
                fg=self.colors["text_secondary"]
            ).pack(pady=50)
            return

        # 创建按钮网格
        row_frame = None
        for i, camp_key in enumerate(camps):
            if i % 4 == 0:
                row_frame = tk.Frame(self.camps_container, bg=self.colors["card"])
                row_frame.pack(fill=tk.X, pady=8)

            camp_data = self.CAMPS[camp_key]
            btn = CampButton(
                row_frame,
                camp_data,
                command=lambda k=camp_key: self.record_camp(k)
            )
            btn.pack(side=tk.LEFT, padx=10, pady=2, expand=True)
            self.camp_buttons[camp_key] = btn

    # ===== 计时器核心功能 =====
    
    def on_route_change(self, event=None):
        """路线改变回调"""
        selected = self.route_var.get()
        self.current_route = self.route_options.get(selected, self.current_route)
        if hasattr(self, "route_badge"):
            self.route_badge.config(text=f"ROUTE   {selected}")
        self.reset_timer()
        self.update_camp_buttons()
                
    def start_timer(self):
        """开始计时"""
        if not self.is_running:
            if self.start_time is None:
                self.start_time = time.time()
            else:
                paused_duration = time.time() - self.pause_time
                self.start_time += paused_duration
                
            self.is_running = True
            self.start_btn.set_state("disabled")
            self.pause_btn.set_state("normal")
            
            self.status_label.config(text="计时中...", fg=self.colors["green"])
            self.status_dot.itemconfig(1, fill=self.colors["green"])
            
    def pause_timer(self):
        """暂停计时"""
        if self.is_running:
            self.is_running = False
            self.pause_time = time.time()
            self.start_btn.set_state("normal")
            self.start_btn.set_text("▶ 继续")
            self.pause_btn.set_state("disabled")
            
            self.status_label.config(text="已暂停", fg=self.colors["orange"])
            self.status_dot.itemconfig(1, fill=self.colors["orange"])
            
    def reset_timer(self):
        """重置计时器"""
        self.is_running = False
        self.start_time = None
        self.pause_time = None
        self.camp_times = {}
        
        self.timer_label.config(text="00:00.00", fg=self.colors["gold"])
        self.status_label.config(text="准备就绪", fg=self.colors["text_secondary"])
        self.status_dot.itemconfig(1, fill=self.colors["border"])
        if hasattr(self, "route_badge"):
            self.route_badge.config(text=f"ROUTE   {self.ROUTES[self.current_route]['name']}")
        
        self.start_btn.set_state("normal")
        self.start_btn.set_text("▶ 开始")
        self.pause_btn.set_state("disabled")
        
        for btn in self.camp_buttons.values():
            btn.reset()
            
        self.update_stats()
        
    def update_timer(self):
        """更新计时器显示"""
        if self.is_running and self.start_time:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            milliseconds = int((elapsed % 1) * 100)
            
            # 超过3分钟变红色
            if elapsed > 180:
                color = self.colors["red"]
            elif elapsed > 150:
                color = self.colors["orange"]
            else:
                color = self.colors["gold"]
                
            self.timer_label.config(
                text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}",
                fg=color
            )
            
        self.root.after(50, self.update_timer)
        
    def record_camp(self, camp_key: str):
        """记录营地完成时间"""
        if not self.is_running:
            if self.start_time is None:
                self.start_timer()
            else:
                self.start_timer()
                
        if camp_key in self.camp_times:
            return
            
        elapsed = time.time() - self.start_time
        self.camp_times[camp_key] = elapsed
        
        btn = self.camp_buttons.get(camp_key)
        if btn:
            btn.record(self.format_time(elapsed, short=True))
            
        self.update_stats()
        
        if self.auto_complete.get():
            route_camps = self.ROUTES[self.current_route]["camps"]
            if all(c in self.camp_times for c in route_camps):
                self.complete_run()
                
    def update_stats(self):
        """更新统计信息显示"""
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        
        if not self.camp_times:
            self.stats_text.insert(tk.END, "点击上方营地按钮记录时间...", ("hint",))
            self.stats_text.tag_config("hint", foreground=self.colors["text_secondary"])
        else:
            prev_time = 0
            route_camps = self.ROUTES[self.current_route]["camps"]
            for camp_key in route_camps:
                if camp_key in self.camp_times:
                    camp = self.CAMPS[camp_key]
                    total_time = self.camp_times[camp_key]
                    segment_time = total_time - prev_time
                    prev_time = total_time
                    
                    line = f"{camp['icon']} {camp['name']:<6}  {self.format_time(total_time):<10}  +{self.format_time(segment_time)}\n"
                    self.stats_text.insert(tk.END, line)
                    
        self.stats_text.config(state=tk.DISABLED)
        
    def format_time(self, seconds: float, short=False) -> str:
        """格式化时间显示"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 100)
        if short and mins == 0:
            return f"{secs}.{ms:02d}s"
        return f"{mins:02d}:{secs:02d}.{ms:02d}"
        
    def manual_complete(self):
        """手动标记完成"""
        if not self.is_running:
            messagebox.showwarning("提示", "计时未开始", parent=self.root)
            return
        if messagebox.askyesno("确认", "结束本轮计时？", parent=self.root):
            self.complete_run()
            
    def complete_run(self):
        """完成一轮打野"""
        if self.is_running:
            total_time = time.time() - self.start_time
            self.is_running = False
            
            self.play_completion_sound()
            
            record = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "route": self.ROUTES[self.current_route]["name"],
                "total_time": total_time,
                "camp_times": self.camp_times.copy()
            }
            self.history.append(record)
            self.save_history()
            
            self.show_completion_dialog(record, total_time)
            
            self.start_btn.set_state("normal")
            self.start_btn.set_text("▶ 开始")
            self.pause_btn.set_state("disabled")
            self.status_label.config(text="已完成", fg=self.colors["gold"])
            
    def play_completion_sound(self):
        """播放完成提示音"""
        try:
            if os.name == 'nt':
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                print('\a')
        except:
            pass
            
    def show_completion_dialog(self, record: dict, total_time: float):
        """显示完成弹窗"""
        dialog = tk.Toplevel(self.root)
        dialog.title("完成！")
        dialog.geometry("380x280")
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(
            dialog,
            text="🏆",
            font=("Segoe UI Emoji", 48),
            bg=self.colors["bg"]
        ).pack(pady=(20, 10))
        
        tk.Label(
            dialog,
            text="恭喜完成！",
            font=("Microsoft YaHei", 18, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["gold_light"]
        ).pack()
        
        info_frame = tk.Frame(dialog, bg=self.colors["card"], padx=25, pady=15)
        info_frame.pack(pady=20, padx=30, fill=tk.X)
        
        tk.Label(
            info_frame,
            text=f"路线: {record['route']}",
            font=("Microsoft YaHei", 11),
            bg=self.colors["card"],
            fg=self.colors["text"]
        ).pack(anchor="w")
        
        tk.Label(
            info_frame,
            text=f"总用时: {self.format_time(total_time)}",
            font=("Consolas", 22, "bold"),
            bg=self.colors["card"],
            fg=self.colors["green"]
        ).pack(anchor="w", pady=(10, 0))
        
        GlowButton(
            dialog,
            text="确定",
            command=dialog.destroy,
            width=120,
            height=40,
            bg_color=self.colors["gold"]
        ).pack(pady=10)
        
    # ===== 历史记录功能 =====
        
    def load_history(self) -> List[dict]:
        """加载历史记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
        
    def save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存失败: {e}")
            
    def show_history(self):
        """显示历史记录窗口"""
        history_window = tk.Toplevel(self.root)
        history_window.title("历史记录")
        history_window.geometry("850x550")
        history_window.configure(bg=self.colors["bg"])
        history_window.transient(self.root)
        
        header = tk.Frame(history_window, bg=self.colors["bg"], padx=30, pady=20)
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text="📊 历史记录",
            font=("Microsoft YaHei", 20, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["gold_light"]
        ).pack(side=tk.LEFT)
        
        if self.history:
            total_runs = len(self.history)
            best_time = min(r['total_time'] for r in self.history)
            avg_time = sum(r['total_time'] for r in self.history) / len(self.history)
            
            stats_frame = tk.Frame(header, bg=self.colors["card"], padx=20, pady=10)
            stats_frame.pack(side=tk.RIGHT)
            
            stats_text = f"总{total_runs}次 | 最佳{self.format_time(best_time)} | 平均{self.format_time(avg_time)}"
            tk.Label(
                stats_frame,
                text=stats_text,
                font=("Consolas", 11),
                bg=self.colors["card"],
                fg=self.colors["green"]
            ).pack()
        
        # 列表
        list_container = tk.Frame(history_window, bg=self.colors["bg"], padx=30)
        list_container.pack(fill=tk.BOTH, expand=True, pady=10)
        
        headers_frame = tk.Frame(list_container, bg=self.colors["card"])
        headers_frame.pack(fill=tk.X, pady=(0, 5))
        
        headers = [("#", 6), ("日期", 18), ("路线", 12), ("用时", 12), ("", 8)]
        for text, width in headers:
            tk.Label(
                headers_frame,
                text=text,
                font=("Microsoft YaHei", 11, "bold"),
                bg=self.colors["card"],
                fg=self.colors["gold"],
                width=width
            ).pack(side=tk.LEFT, padx=5, pady=10)
        
        # 数据
        canvas = tk.Canvas(list_container, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors["bg"])
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=790)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        if not self.history:
            tk.Label(
                scroll_frame,
                text="暂无记录",
                font=("Microsoft YaHei", 14),
                bg=self.colors["bg"],
                fg=self.colors["text_secondary"]
            ).pack(pady=50)
        else:
            for idx, record in enumerate(reversed(self.history[-50:]), 1):
                row_frame = tk.Frame(
                    scroll_frame, 
                    bg=self.colors["card"] if idx % 2 == 0 else self.colors["bg"]
                )
                row_frame.pack(fill=tk.X, pady=2)
                
                tk.Label(row_frame, text=str(idx), font=("Consolas", 10),
                        bg=row_frame.cget("bg"), fg=self.colors["text"], 
                        width=6).pack(side=tk.LEFT, padx=5, pady=12)
                tk.Label(row_frame, text=record['date'], font=("Microsoft YaHei", 10),
                        bg=row_frame.cget("bg"), fg=self.colors["text"], 
                        width=18).pack(side=tk.LEFT, padx=5)
                tk.Label(row_frame, text=record['route'], font=("Microsoft YaHei", 10),
                        bg=row_frame.cget("bg"), fg=self.colors["text"], 
                        width=12).pack(side=tk.LEFT, padx=5)
                tk.Label(row_frame, text=self.format_time(record['total_time']), 
                        font=("Consolas", 11, "bold"),
                        bg=row_frame.cget("bg"), fg=self.colors["gold"], 
                        width=12).pack(side=tk.LEFT, padx=5)
                
                detail_btn = tk.Label(row_frame, text="详情", 
                                     font=("Microsoft YaHei", 10),
                                     bg=row_frame.cget("bg"), 
                                     fg=self.colors["blue"], cursor="hand2")
                detail_btn.pack(side=tk.LEFT, padx=5)
                detail_btn.bind("<Button-1>", lambda e, r=record: self.show_record_detail(r))
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def show_record_detail(self, record: dict):
        """显示记录详情"""
        detail_window = tk.Toplevel(self.root)
        detail_window.title("记录详情")
        detail_window.geometry("380x400")
        detail_window.configure(bg=self.colors["bg"])
        detail_window.transient(self.root)
        
        header = tk.Frame(detail_window, bg=self.colors["card"], padx=25, pady=20)
        header.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(header, text=record['route'], 
                font=("Microsoft YaHei", 16, "bold"),
                bg=self.colors["card"], fg=self.colors["gold_light"]).pack(anchor="w")
        tk.Label(header, text=f"总用时: {self.format_time(record['total_time'])}", 
                font=("Consolas", 24, "bold"),
                bg=self.colors["card"], fg=self.colors["green"]).pack(anchor="w", pady=(10, 0))
        
        content = tk.Frame(detail_window, bg=self.colors["bg"], padx=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(content, text="营地详情", 
                font=("Microsoft YaHei", 12, "bold"),
                bg=self.colors["bg"], fg=self.colors["gold"]).pack(anchor="w", pady=(0, 10))
        
        detail_text = tk.Text(
            content,
            font=("Consolas", 11),
            bg=self.colors["card"],
            fg=self.colors["text"],
            bd=0,
            highlightthickness=0,
            height=12
        )
        detail_text.pack(fill=tk.BOTH, expand=True)
        
        prev_time = 0
        for camp_key, camp_time in record['camp_times'].items():
            camp = self.CAMPS.get(camp_key, {"name": camp_key, "icon": "❓"})
            segment = camp_time - prev_time
            prev_time = camp_time
            detail_text.insert(tk.END, f"{camp['icon']} {camp['name']:<10}")
            detail_text.insert(tk.END, f" {self.format_time(camp_time):<10}")
            detail_text.insert(tk.END, f" +{self.format_time(segment)}\n")
            
        detail_text.config(state=tk.DISABLED)
        
        GlowButton(
            detail_window,
            text="关闭",
            command=detail_window.destroy,
            width=120,
            height=40,
            bg_color=self.colors["gold"]
        ).pack(pady=20)
        
    def export_data(self):
        """导出数据"""
        if not self.history:
            messagebox.showwarning("提示", "没有数据可导出", parent=self.root)
            return
            
        export_file = os.path.join(
            os.path.dirname(__file__), 
            f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"已导出到:\n{export_file}", parent=self.root)
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}", parent=self.root)

            
    def show_help(self):
        """显示帮助"""
        help_window = tk.Toplevel(self.root)
        help_window.title("使用帮助")
        help_window.geometry("480x450")
        help_window.configure(bg=self.colors["bg"])
        help_window.transient(self.root)
        
        tk.Label(help_window, text="❓ 使用帮助", 
                font=("Microsoft YaHei", 18, "bold"),
                bg=self.colors["bg"], fg=self.colors["gold_light"]).pack(pady=20)
        
        content = tk.Frame(help_window, bg=self.colors["card"], padx=25, pady=25)
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        help_text = """【快捷键】
F1 - 开始/继续计时
F2 - 暂停计时  
F3 - 重置计时
F4 - 手动完成

【使用方法】
1. 选择打野路线
2. 点击"开始计时"或按 F1
3. 每清理完一个营地，点击对应按钮
4. 结束：打完路线自动完成，或按F4

【自动监控】
• 勾选"🤖 自动监控"启用
• 优先使用 Riot 本地 API
• API 不可用时自动回退视觉识别
• 0:55 自动开始，4级自动结束

【路线说明】
• 红开全清: 红→石→F6→狼→蓝→蛙
• 蓝开全清: 蓝→蛙→狼→F6→石→红

祝你打野越来越快！💪"""
        
        text_widget = tk.Text(
            content,
            font=("Microsoft YaHei", 11),
            bg=self.colors["card"],
            fg=self.colors["text"],
            bd=0,
            highlightthickness=0,
            wrap=tk.WORD
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(1.0, help_text)
        text_widget.config(state=tk.DISABLED)
        
        GlowButton(
            help_window,
            text="知道了",
            command=help_window.destroy,
            width=120,
            height=40,
            bg_color=self.colors["gold"]
        ).pack(pady=20)
        
    # ===== 自动监控相关方法 =====

    def init_live_client_timer(self):
        """初始化 Riot 本地 API 计时器"""
        def on_start_trigger():
            self.root.after(0, self.on_auto_start_detected)

        def on_end_trigger():
            self.root.after(0, self.on_auto_end_detected)

        self.live_client_timer = LiveClientTimer(
            start_callback=on_start_trigger,
            end_callback=on_end_trigger
        )

    def init_vision_timer(self):
        """初始化视觉识别计时器"""
        if not VISION_AVAILABLE:
            return

        def on_start_trigger():
            self.root.after(0, self.on_auto_start_detected)

        def on_end_trigger():
            self.root.after(0, self.on_auto_end_detected)

        self.vision_timer = VisionTimer(
            start_callback=on_start_trigger,
            end_callback=on_end_trigger
        )
        self.vision_timer.target_time = "0:55"

    def init_auto_monitor(self):
        """初始化自动监控协调器"""
        self.auto_monitor = AutoMonitorCoordinator(
            live_client_timer=self.live_client_timer,
            vision_timer=self.vision_timer,
        )

    def get_auto_backend_label(self):
        """获取当前自动监控后端名称"""
        labels = {
            "riot_api": "Riot API",
            "vision": "视觉识别",
        }
        return labels.get(self.active_auto_backend, "自动监控")

    def format_auto_backend_reason(self, reason: Optional[str]) -> str:
        """格式化后端失败原因"""
        mapping = {
            "connection_failed": "Riot API 未连接到游戏客户端",
            "ssl_error": "Riot API 证书握手失败",
            "invalid_data": "Riot API 返回了不完整的对局数据",
            "startup_timeout": "Riot API 在启动窗口内没有提供可用对局数据",
        }
        return mapping.get(reason, "自动监控启动失败")

    def on_auto_start_detected(self):
        """自动监控-开始触发"""
        if not self.is_running and self.start_time is None:
            print(f"[{self.get_auto_backend_label()}] 检测到0:55，自动开始！")
            self.start_timer()
            self.vision_status.config(
                text=f"[{self.get_auto_backend_label()} 已开始 - 监控4级...]",
                fg=self.colors["orange"]
            )

    def on_auto_end_detected(self):
        """自动监控-结束触发"""
        if self.is_running:
            print(f"[{self.get_auto_backend_label()}] 检测到4级，自动结束！")
            self.complete_run()
            self.vision_status.config(
                text=f"[{self.get_auto_backend_label()} 已完成 - 到达4级]",
                fg=self.colors["green"]
            )

    def stop_auto_monitoring(self):
        """停止自动监控"""
        if self.auto_monitor is None:
            return
        self.auto_monitor.stop()
        self.active_auto_backend = None

    def toggle_vision(self):
        """切换自动监控开关"""
        if self.auto_monitor is None:
            return

        enabled = self.vision_enabled.get()

        if enabled:
            if VISION_AVAILABLE and self.vision_timer is not None:
                self.apply_resolution()

            result = self.auto_monitor.start()
            self.active_auto_backend = None if result.backend == "unavailable" else result.backend

            if result.backend == "unavailable":
                self.vision_enabled.set(False)
                self.vision_status.config(text=result.status_text, fg=self.colors["red"])
                if not self.is_running:
                    self.status_label.config(text="准备就绪", fg=self.colors["text_secondary"])
                    self.status_dot.itemconfig(1, fill=self.colors["border"])

                messagebox.showwarning(
                    "自动监控不可用",
                    self.format_auto_backend_reason(result.fallback_reason),
                    parent=self.root
                )
                return

            status_color = "blue" if result.backend == "riot_api" else "orange"
            self.vision_status.config(text=result.status_text, fg=self.colors[status_color])
            self.status_label.config(
                text=f"{self.get_auto_backend_label()}监控中...",
                fg=self.colors["blue"]
            )
            self.status_dot.itemconfig(1, fill=self.colors["blue"])
        else:
            self.stop_auto_monitoring()
            self.vision_status.config(text="[未启用]", fg=self.colors["text_secondary"])
            if not self.is_running:
                self.status_label.config(text="准备就绪", fg=self.colors["text_secondary"])
                self.status_dot.itemconfig(1, fill=self.colors["border"])
                
    def apply_resolution(self):
        """应用分辨率设置"""
        if self.vision_timer is None:
            return
            
        res = self.resolution_var.get()
        if res == "1920x1080":
            self.vision_timer.set_resolution(1920, 1080)
        elif res == "2560x1440":
            self.vision_timer.set_resolution(2560, 1440)
        elif res == "3840x2160":
            self.vision_timer.set_resolution(3840, 2160)
        elif res == "其他":
            self.ask_custom_resolution()
            
    def ask_custom_resolution(self):
        """询问自定义分辨率"""
        dialog = tk.Toplevel(self.root)
        dialog.title("自定义分辨率")
        dialog.geometry("300x150")
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="输入屏幕分辨率:", 
                font=("Microsoft YaHei", 12),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(pady=10)
        
        input_frame = tk.Frame(dialog, bg=self.colors["bg"])
        input_frame.pack()
        
        width_var = tk.StringVar(value="1920")
        height_var = tk.StringVar(value="1080")
        
        tk.Entry(input_frame, textvariable=width_var, width=8,
                font=("Consolas", 12)).pack(side=tk.LEFT, padx=5)
        tk.Label(input_frame, text="x", font=("Microsoft YaHei", 12),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(side=tk.LEFT)
        tk.Entry(input_frame, textvariable=height_var, width=8,
                font=("Consolas", 12)).pack(side=tk.LEFT, padx=5)
        
        def confirm():
            try:
                w = int(width_var.get())
                h = int(height_var.get())
                self.vision_timer.set_resolution(w, h)
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字", parent=dialog)
                
        GlowButton(
            dialog, text="确定", command=confirm,
            width=100, height=35, bg_color=self.colors["gold"]
        ).pack(pady=15)
        
    def on_resolution_change(self, event=None):
        """分辨率改变"""
        if self.vision_enabled.get() and self.active_auto_backend == "vision":
            self.toggle_vision()
            self.toggle_vision()
            
    def test_vision_calibration(self):
        """测试视觉识别校准"""
        if not VISION_AVAILABLE or self.vision_timer is None:
            messagebox.showwarning("提示", "视觉识别模块未加载")
            return
            
        self.apply_resolution()
        debug_file = self.vision_timer.calibrate()
        
        if debug_file and os.path.exists(debug_file):
            import platform
            base_dir = os.path.dirname(__file__)
            if platform.system() == "Windows":
                os.startfile(os.path.join(base_dir, "debug_time_region.png"))
                os.startfile(os.path.join(base_dir, "debug_level_region.png"))
            elif platform.system() == "Darwin":
                os.system(f"open '{base_dir}/debug_time_region.png'")
            else:
                os.system(f"xdg-open '{base_dir}/debug_time_region.png'")
                
            messagebox.showinfo(
                "校准截图",
                f"已保存校准截图:\n"
                f"• time_region.png (时间区域)\n"
                f"• level_region.png (等级区域)\n\n"
                "请确认截图中包含对应的游戏UI",
                parent=self.root
            )
        else:
            messagebox.showerror("错误", "校准失败", parent=self.root)
        
    def test_vision_preview(self):
        """实时预览识别效果"""
        if not VISION_AVAILABLE or self.vision_timer is None:
            messagebox.showwarning("提示", "视觉识别模块未加载")
            return
            
        self.apply_resolution()
        
        preview_window = tk.Toplevel(self.root)
        preview_window.title("视觉识别预览")
        preview_window.geometry("400x350")
        preview_window.configure(bg=self.colors["bg"])
        preview_window.transient(self.root)
        
        tk.Label(
            preview_window,
            text="👁️ 实时识别预览",
            font=("Microsoft YaHei", 16, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["gold"]
        ).pack(pady=15)
        
        # 时间检测
        time_frame = tk.Frame(preview_window, bg=self.colors["card"], padx=15, pady=12)
        time_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(time_frame, text="⏱️ 游戏时间:",
                font=("Microsoft YaHei", 11),
                bg=self.colors["card"], fg=self.colors["text_secondary"]).pack(anchor="w")
        
        time_label = tk.Label(time_frame, text="--:--",
                font=("Consolas", 28, "bold"),
                bg=self.colors["card"], fg=self.colors["gold"])
        time_label.pack()
        
        time_status = tk.Label(time_frame, text="",
                font=("Microsoft YaHei", 10),
                bg=self.colors["card"], fg=self.colors["text_secondary"])
        time_status.pack()
        
        # 等级检测
        level_frame = tk.Frame(preview_window, bg=self.colors["card"], padx=15, pady=12)
        level_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(level_frame, text="🎮 英雄等级:",
                font=("Microsoft YaHei", 11),
                bg=self.colors["card"], fg=self.colors["text_secondary"]).pack(anchor="w")
        
        level_label = tk.Label(level_frame, text="-",
                font=("Consolas", 32, "bold"),
                bg=self.colors["card"], fg=self.colors["blue"])
        level_label.pack()
        
        level_status = tk.Label(level_frame, text="",
                font=("Microsoft YaHei", 10),
                bg=self.colors["card"], fg=self.colors["text_secondary"])
        level_status.pack()
        
        # 停止按钮
        preview_active = True
        
        def stop_preview():
            nonlocal preview_active
            preview_active = False
            preview_window.destroy()
            
        GlowButton(
            preview_window,
            text="停止预览",
            command=stop_preview,
            width=120,
            height=40,
            bg_color=self.colors["red"]
        ).pack(pady=15)
        
        def update_preview():
            if not preview_active or not preview_window.winfo_exists():
                return
                
            try:
                # 识别时间
                time_img = self.vision_timer.capture_screen()
                is_match, detected_time = self.vision_timer.check_time(time_img)
                
                if detected_time:
                    time_label.config(text=detected_time, 
                                    fg=self.colors["green"] if is_match else self.colors["gold"])
                    if is_match:
                        time_status.config(text="✓ 将自动开始", fg=self.colors["green"])
                    else:
                        time_status.config(text="等待0:55...", fg=self.colors["text_secondary"])
                else:
                    time_label.config(text="--:--", fg="#666666")
                    time_status.config(text="未检测到时间", fg=self.colors["red"])
                
                # 识别等级
                detected_level = self.vision_timer.recognize_level(
                    self.vision_timer.capture_level_region()
                )
                
                if detected_level > 0:
                    level_label.config(text=str(detected_level), fg=self.colors["blue"])
                    if detected_level >= 4:
                        level_status.config(text="✓ 将自动结束", fg=self.colors["green"])
                    else:
                        level_status.config(text=f"还需 {4 - detected_level} 级", 
                                          fg=self.colors["text_secondary"])
                else:
                    level_label.config(text="-", fg="#666666")
                    level_status.config(text="未检测到等级", fg=self.colors["red"])
                    
            except Exception as e:
                time_label.config(text="错误", fg=self.colors["red"])
                
            if preview_active:
                preview_window.after(200, update_preview)
                
        update_preview()
        
    def bind_shortcuts(self):
        """绑定快捷键"""
        self.root.bind('<F1>', lambda e: self.start_timer())
        self.root.bind('<F2>', lambda e: self.pause_timer())
        self.root.bind('<F3>', lambda e: self.reset_timer())
        self.root.bind('<F4>', lambda e: self.manual_complete())
        
    def run(self):
        """运行应用"""
        self.root.mainloop()


if __name__ == "__main__":
    app = JungleTimer()
    app.run()
