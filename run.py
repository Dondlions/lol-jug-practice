#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOL 打野练习计时器 - 启动脚本
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import JungleTimer

if __name__ == "__main__":
    try:
        app = JungleTimer()
        app.run()
    except KeyboardInterrupt:
        print("\n程序已退出")
        sys.exit(0)
    except Exception as e:
        print(f"程序出错: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")
        sys.exit(1)
