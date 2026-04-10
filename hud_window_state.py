#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HUD 窗口状态管理
"""


class HUDWindowState:
    """管理完整 HUD 与紧凑计时条之间的切换"""

    def __init__(self, full_size=(700, 360), compact_size=(320, 110), position=(40, 40)):
        self.full_size = full_size
        self.compact_size = compact_size
        self.position = position
        self.mode = "full"
        self.clickthrough = False

    def current_geometry(self):
        width, height = self.full_size if self.mode == "full" else self.compact_size
        x, y = self.position
        return f"{width}x{height}+{x}+{y}"

    def update_full_size(self, width, height):
        self.full_size = (int(width), int(height))

    def update_position(self, x, y):
        self.position = (int(x), int(y))

    def enter_manual_run_mode(self):
        self.mode = "full"
        self.clickthrough = False

    def enter_auto_run_mode(self):
        self.mode = "compact"
        self.clickthrough = True

    def restore_full_mode(self):
        self.mode = "full"
        self.clickthrough = False
