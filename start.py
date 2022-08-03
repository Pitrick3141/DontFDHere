from PySide2.QtWidgets import QApplication

import global_var
import FDDebug
import FDUpdate
import FDCustom
import FDUtility
import FDMain


# 新建 Pyside2 Application
app = QApplication([])

# 初始化模块
FDDebug.init()
global_var.init()
FDUpdate.init()
FDCustom.init()
FDUtility.init()

# 初始化主窗口
FDMain.init()

# 显示主窗口并导入模板&检查更新
FDMain.display()
FDUtility.checkUpdate()
FDMain.loadTemplates()

# 开始事件循环
# noinspection PyUnboundLocalVariable
app.exec_()

# 窗口关闭后结束Application
del app
