# src/sleep_kit/__init__.py

# 暴露核心功能
from .io import psg_load_raw
from .annotation import load_annotation
from .cli import main

# 新增：暴露一键预处理函数
from .api import fast_preprocess