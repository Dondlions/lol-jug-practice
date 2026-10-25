#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 全局热键监听

游戏在前台时 Tk 的 bind 收不到按键，这里用 Win32 RegisterHotKey
在独立线程里跑消息循环，把命中的热键名字放进队列，由 Tk 主线程轮询。
"""

import ctypes
import platform
import queue
import threading

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

VK_J = 0x4A
VK_H = 0x48


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint32),
        ("wParam", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_uint32),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
        ("lPrivate", ctypes.c_uint32),
    ]


class HotkeyListener:
    """在独立线程里注册并监听全局热键"""

    def __init__(self):
        self._queue = queue.Queue()
        self._hotkeys = {}
        self._thread = None
        self._thread_id = None
        self._ready = threading.Event()
        self.registered = False

    def start(self, hotkeys):
        """hotkeys: {name: (modifiers, vk)}，必须在主线程调用一次"""
        if platform.system() != "Windows" or self._thread is not None:
            return False
        self._hotkeys = {idx + 1: (name, mods, vk)
                         for idx, (name, (mods, vk)) in enumerate(hotkeys.items())}
        self._thread = threading.Thread(target=self._run, name="hotkey-listener", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2.0)
        return self.registered

    def _run(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()

        ok = True
        for hid, (_name, mods, vk) in self._hotkeys.items():
            if not user32.RegisterHotKey(None, hid, mods, vk):
                ok = False
        self.registered = ok
        self._ready.set()
        if not ok:
            return

        msg = MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    entry = self._hotkeys.get(int(msg.wParam or 0))
                    if entry:
                        self._queue.put(entry[0])
        finally:
            for hid in self._hotkeys:
                user32.UnregisterHotKey(None, hid)

    def poll(self):
        """取走攒下的热键事件（Tk 主线程调用）"""
        events = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events

    def stop(self):
        if self._thread is None:
            return
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._thread = None
