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
        available, reason = self.live_client_timer.probe(timeout_seconds=self.probe_timeout)
        if available:
            self.live_client_timer.start_monitoring()
            self.active_backend = "riot_api"
            return AutoMonitorResult(
                backend="riot_api",
                status_text="[Riot API 监控中]",
            )

        if self.vision_timer is not None:
            self.vision_timer.start_monitoring()
            self.active_backend = "vision"
            return AutoMonitorResult(
                backend="vision",
                status_text="[Riot API 不可用，已切换视觉识别]",
                fallback_reason=reason,
            )

        self.active_backend = None
        return AutoMonitorResult(
            backend="unavailable",
            status_text="[自动监控不可用]",
            fallback_reason=reason,
        )

    def stop(self):
        if self.active_backend == "riot_api":
            self.live_client_timer.stop_monitoring()
        elif self.active_backend == "vision" and self.vision_timer is not None:
            self.vision_timer.stop_monitoring()
        self.active_backend = None
