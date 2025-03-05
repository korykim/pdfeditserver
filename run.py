#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF编辑服务器启动脚本

运行此脚本以启动PDF编辑服务器Web应用。
"""

from pdfeditserver import app

if __name__ == '__main__':
    # 确保上传目录存在
    import os
    upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdfeditserver', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    
    # 打印上传目录路径，便于调试
    print(f"上传目录路径: {upload_folder}")
    
    # 启动应用
    print("启动PDF编辑服务器...")
    print("请在浏览器中访问: http://localhost:9000")
    app.run(host='0.0.0.0', port=9000, debug=True)