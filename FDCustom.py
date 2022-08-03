import time
import os
import json

from PySide2.QtWidgets import QMessageBox, QFileDialog
from PySide2.QtUiTools import QUiLoader

import FDRescue
import global_var
import FDDebug

global fdCustom


class FDCustom:
    # 关键词列表
    keywords = []
    # 关键词描述列表
    descriptions = []
    # 当前模板名称
    name = ""
    # 当前模板内容
    content = ""
    # 是否已经保存
    saved = True

    def __init__(self):

        # 加载模板编辑器UI
        try:
            self.ui = QUiLoader().load('ui\\FormCustom.ui')
        except RuntimeError:
            # 缺少必要文件，启用恢复模式
            FDRescue.rescueMode()
            self.ui = QUiLoader().load('ui\\FormCustom.ui')

        # 设置窗口图标
        self.ui.setWindowIcon(global_var.app_icon)

        # 绑定按钮事件
        self.ui.buttonAdd.clicked.connect(self.addKeyword)
        self.ui.buttonRemove.clicked.connect(self.removeKeyword)
        self.ui.buttonClear.clicked.connect(self.clearTemplate)
        self.ui.buttonSave.clicked.connect(self.saveTemplate)
        self.ui.buttonClose.clicked.connect(self.closeEditor)
        self.ui.buttonLoad.clicked.connect(self.loadTemplate)

        # 绑定编辑框事件
        self.ui.textContent.textChanged.connect(self.contentChange)
        self.ui.lineName.textEdited.connect(self.nameChange)

        # 绑定列表框事件
        self.ui.listKeyword.itemClicked.connect(self.keywordChange)

        FDDebug.debug("自定义模板编辑模块初始化完成", type='success', who=self.__class__.__name__)

    def loadTemplate(self):

        ret = None

        # 弹窗询问是否清空模板
        if not self.saved:
            msgbox = QMessageBox()
            msgbox.setWindowTitle("打开模板")
            msgbox.setText("你确定打开新的模板吗？当前模板将被清空")
            msgbox.setInformativeText("警告:该操作不可逆, 你将丢失所有未保存的改动")
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.Yes)
            msgbox.setButtonText(QMessageBox.Yes, "确认清空当前模板")
            msgbox.setButtonText(QMessageBox.No, "否")
            ret = msgbox.exec_()

        if ret == QMessageBox.Yes or self.saved:
            self.clearTemplate(forced=True)
        else:
            return

        # 打开选择文件对话框
        file_dialog = QFileDialog(self.ui)
        file_dir = file_dialog.getOpenFileName(self.ui, "导入模板文件", os.getcwd(), "模板文件 (*.json)")

        # 若未选择任何文件就关闭对话框
        if file_dir[0] == "":
            FDDebug.debug("已取消导入模板文件", type='warn', who=self.__class__.__name__)
            return

        # 打开选择的文件并导入
        FDDebug.debug("正在尝试导入模板文件{0}...".format(file_dir[0]), who=self.__class__.__name__)

        with open(file_dir[0], 'rb') as load_json:

            # 模板文件字典
            data = {}
            # 缺少的键值对
            missed_keys = []
            # 显示的相对路径名称
            display_name = file_dir[0]

            # 尝试读取模板文件并转换为字典
            try:
                original_data = json.load(load_json)

            # 解码失败异常：一般是内容为空或者不合法
            except json.decoder.JSONDecodeError:
                FDDebug.debug("已损坏的模板文件：{0}, 模板文件内容为空或不合法, 跳过当前模板文件".format(display_name),
                              type='error', who=self.__class__.__name__)
                return
            except UnicodeDecodeError:
                FDDebug.debug("已损坏的模板文件：{0}, 模板文件编码格式有误, 跳过当前模板文件".format(display_name),
                              type='error', who=self.__class__.__name__)
                return

            # 将键全部转换为小写，避免大小写混淆
            for key, value in original_data.items():
                data[key.lower()] = value

            # 检测是否有缺失的必需键值对
            for checked_key in ['name', 'content', 'rolename', 'roledes']:
                if checked_key not in data.keys():
                    missed_keys.append(checked_key)

            # 如果有缺失的关键键值对
            if not len(missed_keys) == 0:
                FDDebug.debug(
                    "已损坏的模板文件：{0}, 缺失如下键值对:{1}, 跳过当前模板文件".format(display_name, missed_keys)
                    , type='error', who=self.__class__.__name__)
                return

            self.ui.lineName.setText(data.get('name'))
            self.name = data.get('name')
            self.ui.textContent.setText(data.get('content'))
            self.content = data.get('content')
            role = data.get('rolename')
            des = data.get('roledes')
            for i in range(0, len(role)):
                self.keywords.append(role[i])
                self.descriptions.append(des[i])
                self.ui.listKeyword.addItem("{0}({1})".format(role[i], des[i]))

            FDDebug.debug("已载入模板文件: " + data.get('name'), type='success', who=self.__class__.__name__)

    def nameChange(self):

        # 更改当前模板名称
        self.name = self.ui.lineName.text()

        # 标记为未保存
        self.changeOccur()

    def contentChange(self):

        # 更改当前模板内容
        self.content = self.ui.textContent.toPlainText()

        # 标记为未保存
        self.changeOccur()

    def keywordChange(self):

        # 更换当前编辑的关键词
        # 获取当前关键词序号
        index = self.ui.listKeyword.currentRow()

        # 读取当前关键词和描述
        self.ui.lineKeyword.setText(self.keywords[index])
        self.ui.lineDescription.setText(self.descriptions[index])

    def addKeyword(self):

        # 检测关键词和描述是否为空
        if not self.ui.lineKeyword.text() == "" and not self.ui.lineDescription.text() == "":

            # 检测关键词是否已经存在
            if self.ui.lineKeyword.text() not in self.keywords:

                # 关键词不存在
                # 存储关键词及描述到列表中
                self.keywords.append(self.ui.lineKeyword.text())
                self.descriptions.append(self.ui.lineDescription.text())

                # 添加到关键词列表框中
                self.ui.listKeyword.addItem("{0}({1})".format(self.ui.lineKeyword.text(),
                                                              self.ui.lineDescription.text()))
            else:

                # 关键词已经存在
                # 获取当前正在编辑的关键词序号
                index = self.keywords.index(self.ui.lineKeyword.text())

                # 更改当前关键词描述
                self.descriptions[index] = self.ui.lineDescription.text()

                # 更新关键词列表框
                self.ui.listKeyword.takeItem(index)
                self.ui.listKeyword.insertItem(index, "{0}({1})".format(self.ui.lineKeyword.text(),
                                                                        self.ui.lineDescription.text()))

            FDDebug.debug("已添加关键词{}({})".format(self.ui.lineKeyword.text(), self.ui.lineDescription.text()),
                          type='success', who=self.__class__.__name__)

            # 清空关键词和描述输入框
            self.ui.lineKeyword.clear()
            self.ui.lineDescription.clear()

            # 标记为未保存
            self.changeOccur()

        else:
            QMessageBox.warning(self.ui, "关键词为空", "当前关键词或描述为空, 无法添加", QMessageBox.Ok)

    def removeKeyword(self):

        # 移除选中的关键词
        # 获取当前选中的关键词序号
        index = self.ui.listKeyword.currentRow()

        # 检测序号是否合法(未选择任何项是-1)
        if index == -1:
            QMessageBox.warning(self.ui, "未选择任何关键词", "当前未选择任何关键词, 无法移除", QMessageBox.Ok)
            return

        FDDebug.debug("移除了关键词{}({})".format(self.ui.lineKeyword.text(), self.ui.lineDescription.text()),
                      type='success', who=self.__class__.__name__)
        # 从列表和列表框中移除关键词
        self.ui.listKeyword.takeItem(index)
        del self.keywords[index]
        del self.descriptions[index]

        # 清空关键词和描述输入框
        self.ui.lineKeyword.clear()
        self.ui.lineDescription.clear()

        # 标记为未保存
        self.changeOccur()

    def clearTemplate(self, **kwargs):

        forced = False

        if kwargs.get('forced') is True:
            forced = True

        ret = None

        if not forced:
            # 弹窗确认是否清空模板
            msgbox = QMessageBox()
            msgbox.setWindowTitle("清空当前模板")
            msgbox.setText("你确定要清空当前模板吗？")
            msgbox.setIcon(QMessageBox.Question)
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.Yes)
            msgbox.setButtonText(QMessageBox.Yes, "是")
            msgbox.setButtonText(QMessageBox.No, "否")
            ret = msgbox.exec_()

        if ret == QMessageBox.Yes or forced:

            # 检测是否已经保存
            if not self.saved and not forced:
                # 再次确认
                msgbox = QMessageBox()
                msgbox.setWindowTitle("您有未保存的改动")
                msgbox.setText("你确定要清空当前模板吗？")
                msgbox.setInformativeText("警告:该操作不可逆, 你将丢失所有未保存的改动")
                msgbox.setIcon(QMessageBox.Warning)
                msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msgbox.setDefaultButton(QMessageBox.Yes)
                msgbox.setButtonText(QMessageBox.Yes, "确认清空当前模板")
                msgbox.setButtonText(QMessageBox.No, "否")
                ret = msgbox.exec_()

                if ret == QMessageBox.No:
                    return

            # 清空模板
            if not forced:
                FDDebug.debug("已清空模板", type='success', who=self.__class__.__name__)
            else:
                FDDebug.debug("已清空模板以打开新模板", type='success', who=self.__class__.__name__)

            self.ui.textContent.clear()
            self.content = ""
            self.ui.lineKeyword.clear()
            self.ui.listKeyword.clear()
            self.keywords = []
            self.ui.lineDescription.clear()
            self.descriptions = []
            self.ui.lineName.clear()
            self.name = ""

            self.saved = True
            self.ui.labelUnsaved.setVisible(False)

    def saveTemplate(self):
        save_name = ""

        # 检测模板是否为空
        if self.content == "":
            QMessageBox.warning(self.ui, "模板内容为空", "不能保存内容为空的模板", QMessageBox.Ok)
            return

        # 默认模板名称
        if self.name == "":
            self.name = "未命名自定义模板" + time.strftime("_%Y_%m_%d_%H_%M_%S", time.localtime())

        # 检测同名模板是否存在
        if os.path.exists("FDTemplates\\{0}.json".format(self.name)):
            # 弹窗确认是否覆盖保存
            msgbox = QMessageBox()
            msgbox.setWindowTitle("同名模板已存在")
            msgbox.setText("你确定要覆盖当前模板吗？")
            msgbox.setInformativeText("当前同名模板:{0}\\FDTemplates\\{1}.json".format(os.getcwd(), self.name))
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.Ok | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.Yes)
            msgbox.setButtonText(QMessageBox.Yes, "覆盖保存")
            msgbox.setButtonText(QMessageBox.Ok, "重命名保存")
            msgbox.setButtonText(QMessageBox.No, "取消保存")
            ret = msgbox.exec_()
            if ret == QMessageBox.Ok:
                save_name = "FDTemplates\\{0}_自定义于_{1}.json".format(self.name, time.strftime(
                    "%Y_%m_%d_%H_%M_%S", time.localtime()))
            elif ret == QMessageBox.Yes:
                save_name = "FDTemplates\\{0}.json".format(self.name)
            else:
                return

        # 处理json字典
        json_dump = {'Name': self.name, 'Content': self.content, 'Rolename': self.keywords,
                     'RoleDes': self.descriptions}

        # 保存json文件
        with open(save_name, "w") as f:
            json.dump(json_dump, f)

        # 标记已经保存
        self.saved = True
        self.ui.labelUnsaved.setText("<span style=\" font-size:10pt; color:Green;\">所有改动已保存</span>")

        QMessageBox.information(self.ui,
                                "保存成功",
                                "模板文件已保存至{0}\\{1}".format(os.getcwd(), save_name),
                                QMessageBox.Ok)
        FDDebug.debug("模板文件已保存至{0}\\{1}".format(os.getcwd(), save_name),
                      type='success', who=self.__class__.__name__)

    def closeEditor(self):
        # 弹窗确认是否关闭
        msgbox = QMessageBox()
        msgbox.setWindowTitle("关闭编辑器")
        msgbox.setText("你确定要关闭编辑器吗？")
        if not self.saved:
            msgbox.setInformativeText("你不会因此丢失未保存的信息, 重新打开编辑器后可以继续编辑")
        msgbox.setIcon(QMessageBox.Question)
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.Yes)
        msgbox.setButtonText(QMessageBox.Yes, "是")
        msgbox.setButtonText(QMessageBox.No, "否")
        ret = msgbox.exec_()
        if ret == QMessageBox.Yes:
            FDDebug.debug("关闭了自定义模板编辑器", type='success', who=self.__class__.__name__)
            # 关闭当前窗口
            self.ui.close()

    def changeOccur(self):

        # 模板发生改动
        self.saved = False
        self.ui.labelUnsaved.setVisible(True)
        self.ui.labelUnsaved.setText(
            "<span style=\" font-size:10pt; font-weight:600; color:Red;\">您有未保存的改动!</span>")


def init():
    global fdCustom
    fdCustom = FDCustom()


def display():
    FDDebug.debug("已打开自定义模板编辑器示界面", type='success', who='FDCustom')
    fdCustom.ui.show()


def get_saved():
    return fdCustom.saved
