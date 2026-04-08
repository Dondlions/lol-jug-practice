#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOL 打野计时器 - 视觉识别模块
通过识别游戏画面自动计时
"""

import cv2
import numpy as np
import mss
import time
import threading
from typing import Callable, Optional, Tuple
import os


class VisionTimer:
    """视觉识别计时器"""
    
    def __init__(self, 
                 start_callback: Optional[Callable] = None,
                 end_callback: Optional[Callable] = None):
        self.sct = mss.mss()
        self.start_callback = start_callback
        self.end_callback = end_callback
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.start_detected = False
        self.end_detected = False
        
        # 检测区域（游戏右上角时间区域）
        self.time_region = None
        # 检测区域（左下角英雄等级区域）
        self.level_region = None
        
        self.set_resolution(1920, 1080)
        
        # 检测参数
        self.target_time = "0:55"  # 目标时间
        self.check_interval = 0.1  # 检测间隔（秒）
        self.confidence_threshold = 0.7  # 置信度阈值
        
        # OCR 配置
        self.use_tesseract = False
        self._init_ocr()
        
    def _init_ocr(self):
        """初始化 OCR 引擎"""
        try:
            import pytesseract
            self.use_tesseract = True
            # 配置只识别数字和冒号
            self.ocr_config = '--psm 7 -c tessedit_char_whitelist=0123456789:'
        except ImportError:
            print("[Vision] pytesseract 未安装，将使用备用检测方案")
            self.use_tesseract = False
            
    def set_resolution(self, width: int, height: int):
        """设置游戏分辨率，调整检测区域"""
        # 计算相对于 1920x1080 的缩放比例
        scale = min(width / 1920, height / 1080)
        
        # ===== 时间检测区域（右上角）=====
        x1 = int(width * 0.917)  # 时间大约在屏幕 91.7% 位置开始
        y1 = int(height * 0.019) # 大约在顶部 1.9%
        w = max(80, int(100 * scale))
        h = max(30, int(35 * scale))
        
        self.time_region = {
            "left": x1,
            "top": y1,
            "width": w,
            "height": h
        }
        
        # ===== 等级检测区域（左下角）=====
        # 等级显示在左下角英雄头像右侧
        # 大约在屏幕 2% 宽度，88-92% 高度
        lx = int(width * 0.068)   # 等级数字左侧
        ly = int(height * 0.888)  # 等级数字顶部
        lw = max(40, int(50 * scale))   # 等级数字宽度
        lh = max(30, int(40 * scale))   # 等级数字高度
        
        self.level_region = {
            "left": lx,
            "top": ly,
            "width": lw,
            "height": lh
        }
        
        self.current_resolution = (width, height)
        print(f"[Vision] 分辨率: {width}x{height}")
        print(f"[Vision] 时间检测区域: {self.time_region}")
        print(f"[Vision] 等级检测区域: {self.level_region}")
        
    def set_custom_region(self, x: int, y: int, width: int, height: int):
        """手动设置检测区域"""
        self.time_region = {
            "left": x,
            "top": y,
            "width": width,
            "height": height
        }
        print(f"[Vision] 自定义检测区域: {self.time_region}")
        
    def capture_screen(self) -> np.ndarray:
        """捕获屏幕区域"""
        if self.time_region is None:
            raise ValueError("检测区域未设置")
        screenshot = self.sct.grab(self.time_region)
        img = np.array(screenshot)
        # 转换 BGRA 到 RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        return img
        
    def recognize_time_tesseract(self, img: np.ndarray) -> str:
        """使用 Tesseract OCR 识别时间"""
        import pytesseract
        
        # 预处理图像
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # OCR 识别
        text = pytesseract.image_to_string(binary, config=self.ocr_config)
        return text.strip()
        
    def recognize_time_digit(self, img: np.ndarray) -> str:
        """
        轻量级数字识别 - 专门检测游戏时间的数字
        通过检测像素特征来判断是否为 0:55
        """
        # 转换为灰度
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # 二值化 - 游戏时间数字是白色的（高亮度）
        _, binary = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤太小的轮廓（噪声）
        min_area = 20
        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
        
        # 按x坐标排序（从左到右）
        valid_contours.sort(key=lambda c: cv2.boundingRect(c)[0])
        
        # 游戏时间格式是 "M:SS" 或 "MM:SS"
        # 我们需要至少3个数字字符（分钟、十位秒、个位秒）
        # 对于 0:55，应该是：0、5、5
        
        if len(valid_contours) >= 3:
            # 获取所有轮廓的边界框
            bboxes = [cv2.boundingRect(c) for c in valid_contours]
            
            # 检测冒号位置（两个数字之间的小区域）
            # 冒号通常比数字小，且在中间位置
            colon_idx = -1
            for i in range(len(bboxes) - 1):
                x1, y1, w1, h1 = bboxes[i]
                x2, y2, w2, h2 = bboxes[i + 1]
                gap = x2 - (x1 + w1)
                
                # 冒号的特征：高度小，位置在中间
                if h1 < binary.shape[0] * 0.4 and w1 < h1:
                    colon_idx = i
                    break
            
            # 尝试识别秒数的十位和个位（冒号后的两个数字）
            if colon_idx >= 0 and colon_idx + 2 < len(valid_contours):
                # 冒号后的第一个数字是秒的十位
                sec_tens_idx = colon_idx + 1
                sec_ones_idx = colon_idx + 2
                
                # 分析这两个数字的形状特征
                sec_tens = self._classify_digit(valid_contours[sec_tens_idx], binary)
                sec_ones = self._classify_digit(valid_contours[sec_ones_idx], binary)
                
                # 构建识别结果
                result = f"0:{sec_tens}{sec_ones}"
                return result
            else:
                # 如果找不到冒号，可能是 "55" 这种格式（只有秒数）
                # 尝试直接识别最后两个数字
                if len(valid_contours) >= 2:
                    sec_tens = self._classify_digit(valid_contours[-2], binary)
                    sec_ones = self._classify_digit(valid_contours[-1], binary)
                    result = f"0:{sec_tens}{sec_ones}"
                    return result
        
        return ""
        
    def _classify_digit(self, contour, binary_img) -> str:
        """
        简单的数字分类 - 基于轮廓特征
        专门针对 LOL 游戏时间的数字字体
        """
        x, y, w, h = cv2.boundingRect(contour)
        
        # 提取数字区域
        digit_roi = binary_img[y:y+h, x:x+w]
        
        if digit_roi.size == 0:
            return "?"
        
        # 计算特征
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        aspect_ratio = float(w) / h if h > 0 else 0
        
        # 计算内部白色像素比例
        white_pixels = np.sum(digit_roi == 255)
        total_pixels = digit_roi.size
        fill_ratio = white_pixels / total_pixels if total_pixels > 0 else 0
        
        # 基于特征分类数字（针对 LOL 的等宽数字字体）
        # 这些阈值需要根据实际测试调整
        
        # 1: 瘦长，填充比例小
        if aspect_ratio < 0.4 and fill_ratio < 0.3:
            return "1"
        
        # 0: 宽高比接近1，填充比例适中，有空心
        if 0.4 < aspect_ratio < 0.8 and 0.3 < fill_ratio < 0.6:
            # 检查是否有空心（内部有黑色区域）
            return "0"
        
        # 5: 填充比例较大，顶部较宽
        if fill_ratio > 0.5 and aspect_ratio > 0.5:
            return "5"
        
        # 2,3: 填充比例中等
        if 0.4 < fill_ratio < 0.6:
            # 通过更多的形状特征区分 2 和 3
            if aspect_ratio > 0.6:
                return "3"
            else:
                return "2"
        
        # 默认返回 5（因为我们主要关心 55）
        return "5"
        
    def recognize_time_easyocr(self, img: np.ndarray) -> str:
        """使用 EasyOCR 识别时间（更准但慢）"""
        try:
            import easyocr
            if not hasattr(self, '_easyocr_reader'):
                self._easyocr_reader = easyocr.Reader(['en'])
            
            result = self._easyocr_reader.readtext(img)
            if result:
                return result[0][1]  # 返回识别的文本
            return ""
        except ImportError:
            return ""
            
    def check_time(self, img: np.ndarray) -> Tuple[bool, str]:
        """检查是否到达目标时间"""
        detected_time = ""
        
        try:
            if self.use_tesseract:
                # 优先使用 Tesseract OCR
                detected_time = self.recognize_time_tesseract(img)
            else:
                # 使用轻量级数字识别
                detected_time = self.recognize_time_digit(img)
                    
        except Exception as e:
            print(f"[Vision] 识别错误: {e}")
            
        # 检查是否匹配目标时间
        # 支持模糊匹配，如 "0:55" 可以匹配 "0:55" 或 "0:54" 等接近的时间
        is_match = False
        if detected_time:
            # 精确匹配
            if self.target_time in detected_time or detected_time == self.target_time:
                is_match = True
            else:
                # 尝试提取秒数进行模糊匹配
                try:
                    # 解析检测到的格式 "M:SS"
                    parts = detected_time.split(':')
                    if len(parts) == 2:
                        seconds = int(parts[1])
                        # 如果在 54-56 秒之间，都算匹配（容错）
                        if 54 <= seconds <= 56:
                            is_match = True
                except:
                    pass
        
        return is_match, detected_time
        
    def capture_level_region(self) -> np.ndarray:
        """捕获等级区域"""
        if self.level_region is None:
            raise ValueError("等级检测区域未设置")
        screenshot = self.sct.grab(self.level_region)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        return img
        
    def recognize_level(self, img: np.ndarray) -> int:
        """
        识别英雄等级
        返回识别到的等级数字（1-18），识别失败返回0
        """
        try:
            # 转换为灰度
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            # 二值化 - 等级数字通常是白色或金色
            _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            
            # 查找轮廓
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 过滤并排序轮廓
            valid_contours = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 15:  # 过滤噪声
                    x, y, w, h = cv2.boundingRect(cnt)
                    aspect = w / h if h > 0 else 0
                    # 数字的宽高比通常在 0.3-1.0 之间
                    if 0.2 < aspect < 1.2:
                        valid_contours.append((x, cnt))
            
            # 按x坐标排序
            valid_contours.sort(key=lambda x: x[0])
            
            if not valid_contours:
                return 0
            
            # 识别每个数字
            digits = []
            for _, cnt in valid_contours:
                digit = self._classify_level_digit(cnt, binary)
                if digit != -1:
                    digits.append(digit)
            
            # 组合数字
            if len(digits) == 1:
                return digits[0]
            elif len(digits) >= 2:
                # 两位数（10级以上）
                return digits[0] * 10 + digits[1]
            
            return 0
            
        except Exception as e:
            print(f"[Vision] 等级识别错误: {e}")
            return 0
            
    def _classify_level_digit(self, contour, binary_img) -> int:
        """分类等级数字"""
        x, y, w, h = cv2.boundingRect(contour)
        
        if h < 10 or w < 5:
            return -1
            
        # 提取ROI
        roi = binary_img[y:y+h, x:x+w]
        if roi.size == 0:
            return -1
        
        # 计算特征
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        aspect_ratio = float(w) / h
        
        # 归一化特征
        white_pixels = np.sum(roi == 255)
        fill_ratio = white_pixels / (w * h)
        
        # 简单的数字分类（针对LOL等级字体）
        # 主要通过填充比例和宽高比区分
        
        # 数字1: 很瘦
        if aspect_ratio < 0.35:
            return 1
        
        # 通过轮廓复杂度和填充比例判断
        if fill_ratio > 0.75:
            # 填充多：0, 6, 8, 9
            if aspect_ratio > 0.65:
                return 0
            else:
                # 通过更多特征区分6/8/9
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = float(area) / hull_area if hull_area > 0 else 0
                
                if solidity > 0.9:
                    return 8
                elif aspect_ratio > 0.55:
                    return 9
                else:
                    return 6
        elif fill_ratio > 0.55:
            # 中等填充：2, 3, 4, 5, 7
            if aspect_ratio > 0.75:
                return 7
            elif aspect_ratio > 0.6:
                return 4 if fill_ratio < 0.65 else 3
            else:
                return 5 if fill_ratio > 0.5 else 2
        else:
            # 填充较少
            return 1
            
    def check_level(self, target_level: int = 4) -> Tuple[bool, int]:
        """
        检查是否到达目标等级
        返回: (是否匹配, 识别到的等级)
        """
        try:
            img = self.capture_level_region()
            level = self.recognize_level(img)
            
            is_match = (level >= target_level)
            return is_match, level
            
        except Exception as e:
            print(f"[Vision] 等级检查错误: {e}")
            return False, 0
        
    def start_monitoring(self):
        """开始监控游戏时间"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_detected = False
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"[Vision] 开始监控游戏时间，目标: {self.target_time}")
        
    def _monitor_loop(self):
        """监控循环 - 同时监控开始时间和结束等级"""
        time_matches = 0
        level_matches = 0
        required_matches = 2
        target_end_level = 4  # 目标结束等级
        
        print(f"[Vision] 监控中... 开始目标: {self.target_time}, 结束目标: 等级{target_end_level}")
        
        while self.is_running:
            try:
                # ===== 检测开始时间 =====
                if not self.start_detected:
                    img = self.capture_screen()
                    is_match, detected = self.check_time(img)
                    
                    if is_match:
                        time_matches += 1
                        if time_matches >= required_matches:
                            self.start_detected = True
                            print(f"[Vision] 检测到目标时间: {detected}")
                            if self.start_callback:
                                self.start_callback()
                    else:
                        time_matches = 0
                        
                    self.last_frame = img
                    self.last_detected = detected
                
                # ===== 检测结束等级 =====
                elif not self.end_detected and self.start_detected:
                    is_level_match, detected_level = self.check_level(target_end_level)
                    
                    if is_level_match:
                        level_matches += 1
                        if level_matches >= required_matches:
                            self.end_detected = True
                            print(f"[Vision] 检测到等级{detected_level}，触发结束！")
                            if self.end_callback:
                                self.end_callback()
                            # 检测到后停止监控
                            break
                    else:
                        level_matches = 0
                        
                    self.last_level = detected_level
                    
            except Exception as e:
                print(f"[Vision] 监控错误: {e}")
                
            time.sleep(self.check_interval)
            
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        print("[Vision] 监控已停止")
        
    def calibrate(self):
        """校准检测区域 - 同时校准时间和等级区域"""
        try:
            # 捕获多帧取平均，确保画面稳定
            frames = []
            for _ in range(3):
                img = self.capture_screen()
                frames.append(img)
                time.sleep(0.05)
            
            # 使用最后一帧
            img = frames[-1]
            
            # ===== 校准时间区域 =====
            detected_time, debug_img_time = self._recognize_with_debug(img)
            
            # 保存时间区域调试图
            debug_path_time = os.path.join(os.path.dirname(__file__), "debug_time_region.png")
            cv2.imwrite(debug_path_time, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            
            debug_path_time2 = os.path.join(os.path.dirname(__file__), "debug_time_recognition.png")
            cv2.imwrite(debug_path_time2, cv2.cvtColor(debug_img_time, cv2.COLOR_RGB2BGR))
            
            # ===== 校准等级区域 =====
            level_img = self.capture_level_region()
            detected_level = self.recognize_level(level_img)
            
            # 保存等级区域调试图
            debug_path_level = os.path.join(os.path.dirname(__file__), "debug_level_region.png")
            cv2.imwrite(debug_path_level, cv2.cvtColor(level_img, cv2.COLOR_RGB2BGR))
            
            # 创建等级调试图（带识别结果）
            level_debug = level_img.copy()
            cv2.putText(level_debug, f"Level: {detected_level}", (5, level_img.shape[0]-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            debug_path_level2 = os.path.join(os.path.dirname(__file__), "debug_level_recognition.png")
            cv2.imwrite(debug_path_level2, cv2.cvtColor(level_debug, cv2.COLOR_RGB2BGR))
            
            print(f"[Vision] 时间校准截图: {debug_path_time}")
            print(f"[Vision] 等级校准截图: {debug_path_level}")
            print(f"[Vision] 识别结果 - 时间: '{detected_time}', 等级: {detected_level}")
            print("[Vision] 请确认截图中包含游戏时间和等级显示")
            
            return debug_path_time
        except Exception as e:
            print(f"[Vision] 校准失败: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def _recognize_with_debug(self, img: np.ndarray) -> Tuple[str, np.ndarray]:
        """识别时间并返回调试图像"""
        debug_img = img.copy()
        
        # 转换为灰度
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # 二值化
        _, binary = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 在调试图上绘制轮廓
        for i, cnt in enumerate(contours):
            if cv2.contourArea(cnt) > 20:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 1)
                cv2.putText(debug_img, str(i), (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 尝试识别
        detected = self.recognize_time_digit(img)
        
        # 在图像上显示识别结果
        cv2.putText(debug_img, f"Detected: {detected}", (5, img.shape[0]-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        return detected, debug_img
            
    def preview_detection(self, duration: float = 5.0):
        """预览检测效果"""
        print(f"[Vision] 开始 {duration} 秒检测预览...")
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                img = self.capture_screen()
                is_match, detected = self.check_time(img)
                status = "✓ 匹配" if is_match else "  检测中"
                print(f"\r{status} | 识别结果: '{detected}'", end="", flush=True)
            except Exception as e:
                print(f"\r[Vision] 错误: {e}", end="", flush=True)
            time.sleep(0.2)
            
        print("\n[Vision] 预览结束")


class SimpleVisionTrigger:
    """简化版视觉触发器 - 检测特定像素颜色变化"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.is_running = False
        self.sct = mss.mss()
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 检测配置
        self.check_interval = 0.05  # 20fps 检测
        self.triggered = False
        
    def set_pixel_region(self, x: int, y: int):
        """设置检测的像素点（游戏时间的数字位置）"""
        self.pixel_region = {"left": x, "top": y, "width": 1, "height": 1}
        
    def detect_time_change(self, threshold: int = 200) -> bool:
        """检测时间显示区域是否有变化（亮度变化）"""
        try:
            screenshot = self.sct.grab(self.pixel_region)
            img = np.array(screenshot)
            brightness = np.mean(img)
            return brightness > threshold
        except:
            return False
            
    def start(self, timeout: float = 120.0):
        """开始检测，超时后停止"""
        if self.is_running:
            return
            
        self.is_running = True
        self.triggered = False
        self.monitor_thread = threading.Thread(
            target=self._detect_loop, 
            args=(timeout,),
            daemon=True
        )
        self.monitor_thread.start()
        
    def _detect_loop(self, timeout: float):
        """检测循环 - 检测时间数字的亮度变化"""
        start_time = time.time()
        last_state = False
        stable_count = 0
        
        print("[Vision] 等待游戏时间显示...")
        
        while self.is_running and time.time() - start_time < timeout:
            current_state = self.detect_time_change()
            
            # 检测从黑到亮的变化（游戏时间出现）
            if current_state and not last_state:
                stable_count += 1
                if stable_count >= 3:  # 连续3帧检测到
                    self.triggered = True
                    print("[Vision] 检测到游戏开始！")
                    if self.callback:
                        self.callback()
                    break
            else:
                stable_count = 0
                
            last_state = current_state
            time.sleep(self.check_interval)
            
        self.is_running = False
        
    def stop(self):
        """停止检测"""
        self.is_running = False


# 测试代码
if __name__ == "__main__":
    print("=" * 50)
    print("LOL 视觉识别计时器测试")
    print("=" * 50)
    print("\n1. 确保LOL游戏在运行")
    print("2. 游戏分辨率应为 1920x1080")
    print("3. 等待测试开始...\n")
    
    def on_trigger():
        print("\n🎮 检测到游戏时间！计时开始！")
        
    # 创建计时器
    timer = VisionTimer(callback=on_trigger)
    
    # 校准模式
    print("正在进行区域校准...")
    debug_file = timer.calibrate()
    
    if debug_file:
        print(f"\n请查看保存的截图: {debug_file}")
        print("确认包含游戏时间后按回车继续...")
        input()
        
    # 开始监控
    print(f"\n开始监控，将在检测到 {timer.target_time} 时触发...")
    print("按 Ctrl+C 停止\n")
    
    timer.start_monitoring()
    
    try:
        while True:
            time.sleep(1)
            if timer.start_detected:
                print("触发成功！程序将在3秒后退出...")
                time.sleep(3)
                break
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        timer.stop_monitoring()
