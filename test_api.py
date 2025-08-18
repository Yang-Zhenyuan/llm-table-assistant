# -*- coding: utf-8 -*-
"""
Created on Mon Aug 18 04:02:38 2025

@author: LENOVO
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import os
import sys
from retrieval_graph.llm_utils import load_chat_model


print("脚本开始执行")

print("当前工作目录:", os.getcwd())
print("环境变量里 OPENAI_API_KEY 前缀:", os.getenv("OPENAI_API_KEY", "")[:8])
print("环境变量里 OPENAI_MODEL:", os.getenv("OPENAI_MODEL", "未设置"))

try:
    llm = load_chat_model()
    print("模型加载成功:", llm)

    resp = llm.invoke("Say 'Hello from API' in English and Chinese.")
    print("模型响应:", resp)

except Exception as e:
    print("出错了:", e, file=sys.stderr)
