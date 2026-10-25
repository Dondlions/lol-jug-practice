#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows HUD 窗口扩展样式
"""

import platform


def set_clickthrough(root, enabled: bool):
    """在 Windows 上切换点击穿透，其它平台静默跳过

    注意：必须把 WS_EX_LAYERED 设在顶层窗口上，并同时调用
    SetLayeredWindowAttributes。只给 Tk 客户区 HWND 加 WS_EX_LAYERED
    而不设置透明度属性，客户区会完全不绘制（表现为整窗白屏）。
    """
    if platform.system() != "Windows":
        return

    import ctypes

    user32 = ctypes.windll.user32

    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    LWA_COLORKEY = 0x00000001
    LWA_ALPHA = 0x00000002

    child = root.winfo_id()
    # winfo_id() 给的是 Tk 客户区 HWND，样式要打在它的父级（顶层 wrapper）上
    hwnd = user32.GetParent(child) or child

    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_LAYERED
    if enabled:
        ex_style |= WS_EX_TRANSPARENT
    else:
        ex_style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

    # 补上分层窗口的不透明度，否则设置了 WS_EX_LAYERED 的窗口不会绘制内容
    try:
        alpha = float(root.attributes("-alpha"))
    except Exception:
        alpha = 1.0
    alpha = min(1.0, max(0.0, alpha))

    # 若窗口设了 -transparentcolor（紧凑 HUD 的色键背景），这里必须一并保留，
    # 否则 SetLayeredWindowAttributes 会把色键清掉，背景又变回实心板。
    flags = LWA_ALPHA
    key = 0
    try:
        key_color = root.attributes("-transparentcolor")
    except Exception:
        key_color = None
    if key_color:
        try:
            r, g, b = (c // 256 for c in root.winfo_rgb(key_color))
            key = r | (g << 8) | (b << 16)  # COLORREF: 0x00BBGGRR
            flags |= LWA_COLORKEY
        except Exception:
            key = 0
            flags = LWA_ALPHA

    user32.SetLayeredWindowAttributes(hwnd, key, int(round(alpha * 255)), flags)
