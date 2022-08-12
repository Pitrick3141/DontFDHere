from PySide2.QtGui import QIcon

# 当前版本号，用于检查更新

current_version = 'v1.3.0'

# 程序图标

global app_icon

# 配置项字典

global _configs

# 模板列表
global _templates

# 模板hash字典，用于同步模板
global _templates_hash


def init():
    global _configs
    _configs = {}

    global app_icon
    app_icon = QIcon("ui\\icon.png")

    global _templates
    _templates = []

    global _templates_hash
    _templates_hash = {}

    return


def set_config(key, value):
    _configs[key] = value
    return


def get_config(key):
    return _configs.get(key)


def config_keys():
    return _configs.keys()


def templates_hash_keys():
    return _templates_hash.keys()


def templates_hash_values():
    return _templates_hash.values()


def get_templates_hash(key):
    return _templates_hash.get(key)


def set_templates_hash(key, value):
    _templates_hash[key] = value
    return


def templates_hash_clear():
    _templates_hash.clear()
    return


def templates_append(value):
    _templates.append(value)
    return


def get_templates(value):
    return _templates[value]


def len_templates():
    return len(_templates)


def templates_clear():
    _templates.clear()
    return
