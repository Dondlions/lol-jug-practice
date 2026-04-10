#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows HUD 窗口扩展样式
"""

import platform


def set_clickthrough(root, enabled: bool):
    """在 Windows 上切换点击穿透，其它平台静默跳过"""
    if platform.system() != "Windows":
        return

    import ctypes

    hwnd = root.winfo_id()
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020

    user32 = ctypes.windll.user32
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex_style |= WS_EX_LAYERED

    if enabled:
        ex_style |= WS_EX_TRANSPARENT
    else:
        ex_style &= ~WS_EX_TRANSPARENT

    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
