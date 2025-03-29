import json
import os
import sys
from common.log import logger

# 全局配置
config = {}

def load_config():
    global config
    config_path = "config.json"
    if not os.path.exists(config_path):
        logger.error("配置文件不存在: config.json")
        sys.exit(1)
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info("配置加载成功")
    except Exception as e:
        logger.error(f"配置加载错误: {e}")
        sys.exit(1)
    return config

def get_value(key, default=None):
    global config
    if key in config:
        return config[key]
    else:
        return default 