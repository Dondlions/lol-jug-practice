#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Riot 本地 Live Client Data API 计时器
优先使用官方本地 API 获取游戏时间和英雄等级
"""

from dataclasses import dataclass
import json
import ssl
import threading
import time
from typing import Callable, Optional
from urllib import error, request


@dataclass
class LiveClientState:
    """当前对局状态"""

    game_time: float
    level: int


class LiveClientError(Exception):
    """本地客户端 API 错误"""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


class LiveClientTimer:
    """Riot 本地 API 计时器"""

    def __init__(
        self,
        start_callback: Optional[Callable] = None,
        end_callback: Optional[Callable] = None,
        fetch_json: Optional[Callable[[str], dict]] = None,
        base_url: str = "https://127.0.0.1:2999",
        check_interval: float = 0.2,
        request_timeout: float = 0.5,
        startup_timeout: float = 1.5,
        target_time_seconds: float = 55.0,
        target_end_level: int = 4,
    ):
        self.start_callback = start_callback
        self.end_callback = end_callback
        self.base_url = base_url.rstrip("/")
        self.check_interval = check_interval
        self.request_timeout = request_timeout
        self.startup_timeout = startup_timeout
        self.target_time_seconds = target_time_seconds
        self.target_end_level = target_end_level
        self.fetch_json = fetch_json or self._fetch_json

        self.is_running = False
        self.start_detected = False
        self.end_detected = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_state: Optional[LiveClientState] = None
        self.last_error_reason: Optional[str] = None
        self.last_game_time: Optional[float] = None

        # Riot 本地接口使用自签名证书，主动关闭校验以避免误判。
        self.ssl_context = ssl._create_unverified_context()

    def _fetch_json(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = request.Request(url, headers={"Accept": "application/json"})

        try:
            with request.urlopen(
                req,
                timeout=self.request_timeout,
                context=self.ssl_context,
            ) as response:
                payload = response.read().decode("utf-8")
        except ssl.SSLError as exc:
            raise LiveClientError("ssl_error", str(exc)) from exc
        except error.URLError as exc:
            if isinstance(exc.reason, ssl.SSLError):
                raise LiveClientError("ssl_error", str(exc.reason)) from exc
            raise LiveClientError("connection_failed", str(exc.reason)) from exc
        except Exception as exc:
            raise LiveClientError("connection_failed", str(exc)) from exc

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise LiveClientError("invalid_data", "invalid json payload") from exc

    def read_state(self) -> LiveClientState:
        """读取当前游戏时间和英雄等级"""
        gamestats = self.fetch_json("/liveclientdata/gamestats")
        active_player = self.fetch_json("/liveclientdata/activeplayer")

        game_time = gamestats.get("gameTime")
        level = active_player.get("level")

        if game_time is None or level is None:
            raise LiveClientError("invalid_data", "missing gameTime or level")

        try:
            state = LiveClientState(game_time=float(game_time), level=int(level))
        except (TypeError, ValueError) as exc:
            raise LiveClientError("invalid_data", "non-numeric gameTime or level") from exc

        self.last_state = state
        self.last_error_reason = None
        return state

    def probe(self, timeout_seconds: Optional[float] = None):
        """检查 Riot 本地 API 是否可用"""
        timeout_seconds = self.startup_timeout if timeout_seconds is None else timeout_seconds
        deadline = time.time() + max(timeout_seconds, 0)
        last_reason = "startup_timeout"

        while True:
            try:
                self.read_state()
                return True, None
            except LiveClientError as exc:
                last_reason = exc.reason
                self.last_error_reason = exc.reason

            if timeout_seconds <= 0 or time.time() >= deadline:
                break

            time.sleep(self.check_interval)

        return False, last_reason

    def start_monitoring(self):
        """开始监控对局时间与等级"""
        if self.is_running:
            return

        self.is_running = True
        self.start_detected = False
        self.end_detected = False
        self.last_game_time = None
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("[LiveClient] 开始监控 Riot 本地 API")

    def process_state(self, state: LiveClientState):
        """处理单帧对局状态，支持多局连续监控"""
        # 练习模式重置或重新开局时，gameTime 会从较大值回到很小的值。
        if (
            self.last_game_time is not None
            and self.last_game_time >= self.target_time_seconds
            and state.game_time < 10
            and state.game_time + 15 < self.last_game_time
        ):
            self.start_detected = False
            self.end_detected = False
            print("[LiveClient] 检测到新的一局，已重置监控状态")

        if not self.start_detected and state.game_time >= self.target_time_seconds:
            self.start_detected = True
            print(f"[LiveClient] 检测到目标时间: {state.game_time:.2f}s")
            if self.start_callback:
                self.start_callback()

        if self.start_detected and not self.end_detected and state.level >= self.target_end_level:
            self.end_detected = True
            print(f"[LiveClient] 检测到等级{state.level}，触发结束！")
            if self.end_callback:
                self.end_callback()

        self.last_game_time = state.game_time

    def _monitor_loop(self):
        try:
            while self.is_running:
                try:
                    state = self.read_state()
                    self.process_state(state)

                except LiveClientError as exc:
                    self.last_error_reason = exc.reason

                time.sleep(self.check_interval)
        finally:
            self.is_running = False

    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
            self.monitor_thread = None
        print("[LiveClient] 监控已停止")
