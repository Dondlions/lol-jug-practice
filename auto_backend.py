#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动监控后端协调器
优先使用 Riot 本地 API，失败时回退到视觉识别
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AutoMonitorResult:
    """自动监控启动结果"""

    backend: str
    status_text: str
    fallback_reason: Optional[str] = None


class AutoMonitorCoordinator:
    """协调自动监控后端的选择与切换"""

    def __init__(self, live_client_timer, vision_timer=None, probe_timeout=1.5):
        self.live_client_timer = live_client_timer
        self.vision_timer = vision_timer
        self.probe_timeout = probe_timeout
        self.active_backend = None

    def start(self) -> AutoMonitorResult:
        available, reason = self.live_client_timer.probe(timeout_seconds=0)
        self.live_client_timer.start_monitoring()

        if self.vision_timer is not None:
            self.vision_timer.start_monitoring()
            self.active_backend = "dual"
            return AutoMonitorResult(
                backend="dual",
                status_text="[双通道监控中]",
                fallback_reason=None if available else reason,
            )

        self.active_backend = "riot_api"
        return AutoMonitorResult(
            backend="riot_api",
            status_text="[Riot API 监控中]",
            fallback_reason=None if available else reason,
        )

    def stop(self):
        if self.active_backend in {"riot_api", "dual"}:
            self.live_client_timer.stop_monitoring()
        if self.active_backend in {"vision", "dual"} and self.vision_timer is not None:
            self.vision_timer.stop_monitoring()
        self.active_backend = None
