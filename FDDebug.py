import time

from PySide2.QtUiTools import QUiLoader

import FDRescue

global fdDebug


class FDDebug:

    def __init__(self):
        # 加载调试窗口UI
        try:
            self.ui = QUiLoader().load('ui\\FormDebug.ui')
        except RuntimeError:
            # 缺少必要文件，启用恢复模式
            FDRescue.rescueMode()
            self.ui = QUiLoader().load('ui\\FormDebug.ui')
        self.debug("调试输出模块初始化完成", type='success', who=self.__class__.__name__)

    def debug(self, text: str, **kwargs) -> None:
        # 读取当前时间
        current_time = time.strftime("%H:%M:%S", time.localtime())

        # 处理传入参数

        # 分割线
        if kwargs.get('split') is True:
            # 将调试信息输出
            self.ui.textDebug.append("-" * 10)
            # 移动到文本框底部
            self.ui.textDebug.moveCursor(self.ui.textDebug.textCursor().End)
            print("-" * 10)
            return

        # 信息来源
        info_from = "@主界面"
        if kwargs.get('who') == 'FDCustom':
            info_from = '@自定义模板编辑器'
        elif kwargs.get('who') == 'FDUpdate':
            info_from = '@更新检查实用工具'
        elif kwargs.get('who') == 'FDMenu':
            info_from = '@功能菜单'
        elif kwargs.get('who') == 'FDDebug':
            info_from = '@调试输出'
        elif kwargs.get('who') == 'FDRescue':
            info_from = '@恢复模式'

        # 错误信息
        if kwargs.get('type') == 'error':
            prefix = "<b style=\"color:Red;\">"
            suffix = "</b>"
            output_message = " [Error{}] {}".format(info_from, text)
        # 警告信息
        elif kwargs.get('type') == 'warn':
            prefix = "<span style=\"color:Orange;\">"
            suffix = "</span>"
            output_message = " [Warn{}] {}".format(info_from, text)
        # 成功信息
        elif kwargs.get('type') == 'success':
            prefix = "<span style=\"color:YellowGreen;\">"
            suffix = "</span>"
            output_message = " [Success{}] {}".format(info_from, text)
        # 其他信息
        else:
            prefix = "<span>"
            suffix = "</span>"
            output_message = " [Info{}] {}".format(info_from, text)

        # 将调试信息输出
        self.ui.textDebug.append(prefix + current_time + output_message + suffix)
        # 移动到文本框底部
        self.ui.textDebug.moveCursor(self.ui.textDebug.textCursor().End)
        print(current_time + output_message)


def init():
    global fdDebug
    fdDebug = FDDebug()


def debug(text: str, **kwargs) -> None:
    fdDebug.debug(text, **kwargs)


def split():
    fdDebug.debug("", split=True)


def display() -> None:
    debug("已打开调试输出界面", type='success', who='FDDebug')
    fdDebug.ui.show()
