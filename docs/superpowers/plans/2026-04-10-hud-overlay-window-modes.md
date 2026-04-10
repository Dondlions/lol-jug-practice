# HUD Overlay Window Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app start in a fully visible HUD size, switch to a compact timer-only overlay with click-through after automatic start, and restore the full HUD when a run ends or resets.

**Architecture:** Add a small HUD window state helper that decides geometry and click-through mode, then wire `main.py` to apply those transitions at startup, auto-start, completion, and reset. Keep the actual Windows click-through implementation behind a platform-guarded helper so non-Windows environments keep working.

**Tech Stack:** Python 3.7+, Tkinter, ctypes (Windows only), pytest

---
