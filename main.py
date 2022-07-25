import sys
import time
import os
import json
import pyperclip

from PySide2.QtWidgets import QApplication, QMessageBox, QFileDialog
from PySide2.QtUiTools import QUiLoader


def openDir():

    # 打开模板文件目录
    os.startfile(os.getcwd() + "\\FDTemplates")


class FDMain:

    # 是否启用调试输出
    isDebugEnabled = False
    # 模板列表
    templates = []
    # 初始化完成
    initialized = False
    # 当前模板
    current_template = {}
    # 当前替换内容字典
    replacements = {}
    # 当前替换对象
    current_replacement = ""

    def __init__(self, **kwargs) -> None:

        # 加载主窗口UI
        self.ui = QUiLoader().load('ui\\MainForm.ui')

        # 加载自定义模板编辑器
        self.custom_form = FDCustom()

        # 传入参数处理
        self.isDebugEnabled = kwargs['debug']

        # 是否显示调试输出
        if not self.isDebugEnabled:
            self.ui.setMinimumSize(730, 520)
            self.ui.setMaximumSize(730, 520)

        # 绑定按钮事件
        self.ui.buttonRefreshList.clicked.connect(self.loadTemplates)
        self.ui.buttonReplace.clicked.connect(self.replaceContext)
        self.ui.buttonCopy.clicked.connect(self.copyResult)
        self.ui.buttonQuit.clicked.connect(self.quitProgram)
        self.ui.buttonOpenTemplateDir.clicked.connect(openDir)
        self.ui.buttonImportTemplate.clicked.connect(self.importTemplate)
        self.ui.buttonCustomTemplate.clicked.connect(self.customTemplate)

        # 绑定下模板选择框事件
        self.ui.comboBox.currentIndexChanged.connect(self.showTemplate)

        # 绑定关键词选择框事件
        self.ui.listKeyword.itemClicked.connect(self.keywordChange)

        # 绑定输入框事件
        self.ui.lineCustomKeyword.textEdited.connect(self.customKeyword)
        self.ui.lineReplacement.textEdited.connect(self.replacementChange)

        # 载入模板文件
        self.loadTemplates()
        self.debug("主界面加载完成", type='success')

    def debug(self, text: str, **kwargs) -> None:

        # 如果未启用调试输出则直接返回
        if not self.isDebugEnabled:
            return

        # 读取当前时间
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # 处理传入参数
        # 错误信息
        if kwargs.get('type') == 'error':
            output_message = "{0}<b style=\"color:Red;\">[Error] {1}</b>".format(current_time, text)
        # 警告信息
        elif kwargs.get('type') == 'warn':
            output_message = "{0}<span style=\"color:Orange;\">[Warn] {1}</span>".format(current_time, text)
        # 成功信息
        elif kwargs.get('type') == 'success':
            output_message = "{0}<span style=\"color:YellowGreen;\">[Success] {1}</span>".format(current_time, text)
        # 其他信息
        else:
            output_message = "{0}<span>[Info] {1}</span>".format(current_time, text)

        # 将调试信息输出
        self.ui.textDebug.append(output_message)

    def loadTemplates(self):

        # 防止载入完成之前先读取
        self.initialized = False

        # 清空框架选择列表框和框架列表
        self.ui.comboBox.clear()
        self.templates.clear()

        self.debug("开始载入模板...")

        # 默认模板文件目录
        template_dir = os.walk("FDTemplates")

        # 遍历模板文件目录
        for path, dir_list, file_list in template_dir:
            for file_name in file_list:

                # 检查文件拓展名是否合法
                if not file_name.find(".json") == -1:

                    # 打开模板文件
                    with open(os.path.abspath(path) + "\\" + file_name, 'rb') as load_json:

                        # 模板文件字典
                        data = {}
                        # 缺少的键值对
                        missed_keys = []
                        # 显示的相对路径名称
                        display_name = path + "\\" + file_name

                        # 尝试读取模板文件并转换为字典
                        try:
                            original_data = json.load(load_json)

                        # 解码失败异常：一般是内容为空或者不合法
                        except json.decoder.JSONDecodeError:
                            self.debug("已损坏的模板文件：{0}, 模板文件内容为空或不合法, 跳过当前模板文件".format(display_name), type='error')
                            continue
                        except UnicodeDecodeError:
                            self.debug("已损坏的模板文件：{0}, 模板文件编码格式有误, 跳过当前模板文件".format(display_name), type='error')
                            continue

                        # 将键全部转换为小写，避免大小写混淆
                        for key, value in original_data.items():
                            data[key.lower()] = value

                        # 检测是否有缺失的必需键值对
                        for checked_key in ['name', 'content', 'rolename', 'roledes']:
                            if checked_key not in data.keys():
                                missed_keys.append(checked_key)

                        # 如果有缺失的关键键值对
                        if not len(missed_keys) == 0:
                            self.debug("已损坏的模板文件：{0}, 缺失如下键值对:{1}, 跳过当前模板文件".format(display_name, missed_keys)
                                       , type='error')
                            continue

                        # 检测是否已经添加了相同的模板
                        elif data in self.templates:
                            self.debug("已经载入相同的模板文件: {0}, 跳过当前模板文件".format(display_name)
                                       , type='warn')
                            continue

                        # 将模板添加到模板列表和模板列表框中
                        self.templates.append(data)
                        self.ui.comboBox.addItem(data.get('name'))
                    self.debug("已载入模板文件: " + data.get('name'))

                # 文件拓展名不为.json
                else:
                    self.debug("不支持的文件类型(目前仅支持.json格式)：{0}, 跳过当前模板文件".format(display_name), type='error')

        self.ui.comboBox.setCurrentIndex(-1)
        self.debug("模板载入完成,共载入{0}个模板文件".format(len(self.templates)), type='success')
        self.initialized = True

    def showTemplate(self):

        # 防止在载入模板前先读取模板内容
        if not self.initialized:
            return

        # 重置替换关键词字典
        self.replacements.clear()
        self.current_replacement = ""

        self.current_template = self.templates[self.ui.comboBox.currentIndex()]
        # 将选择的模板输出
        self.ui.textResult.setText(self.current_template.get('content'))
        self.debug("已选择模板:" + self.ui.comboBox.currentText())

        # 将模板的关键词加入到关键词列表
        self.ui.listKeyword.clear()
        self.ui.listKeyword.addItems(self.current_template.get('rolename'))

    def keywordChange(self):

        # 清空自定义关键词输入框
        self.ui.lineCustomKeyword.clear()

        # 选中的关键词和描述
        current_keyword_index = self.ui.listKeyword.currentRow()
        current_keyword_name = self.current_template.get('rolename')[current_keyword_index]
        current_keyword_des = self.current_template.get('roledes')[current_keyword_index]
        self.current_replacement = current_keyword_name
        self.ui.labelKeyword.setText("{0}({1})".format(current_keyword_name, current_keyword_des))

        # 读取先前的替换关键词
        if current_keyword_name in self.replacements.keys():
            self.ui.lineReplacement.setText(self.replacements[current_keyword_name])
        else:
            self.ui.lineReplacement.clear()

    def customKeyword(self):

        if self.ui.textResult.toPlainText() == "EnableDebugMode" and self.ui.lineCustomKeyword.text() == "True":
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            QMessageBox.information(self.ui, "调试模式已启用", "调试输出模式已被启用", QMessageBox.Ok)
            self.isDebugEnabled = True
            self.ui.setMinimumSize(1290, 520)
            self.ui.setMaximumSize(1290, 520)
            self.debug("调试输出模式已被启用")

        if self.ui.textResult.toPlainText() == "EnableDebugMode" and self.ui.lineCustomKeyword.text() == "False":
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            QMessageBox.information(self.ui, "调试模式已禁用", "调试输出模式已被禁用", QMessageBox.Ok)
            self.isDebugEnabled = False
            self.ui.setMinimumSize(730, 520)
            self.ui.setMaximumSize(730, 520)

        if self.ui.textResult.toPlainText() == "CustomTemplateEditor" and self.ui.lineCustomKeyword.text() == "Show":
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            self.debug("已打开自定义模板编辑器", type='success')
            self.custom_form.ui.show()

        # 自定义的关键词
        current_keyword_name = self.ui.lineCustomKeyword.text()
        current_keyword_des = "自定义关键词"
        self.current_replacement = current_keyword_name
        self.ui.labelKeyword.setText("{0}({1})".format(current_keyword_name, current_keyword_des))

        # 读取先前的替换关键词
        if current_keyword_name in self.replacements.keys():
            self.ui.lineReplacement.setText(self.replacements[current_keyword_name])
        else:
            self.ui.lineReplacement.clear()

    def replacementChange(self):

        # 在字典中保存替换的关键词对
        self.replacements[self.current_replacement] = self.ui.lineReplacement.text()

        # 若替换为空则从字典中移除
        if self.ui.lineReplacement.text() == "":
            self.replacements.pop(self.current_replacement)

    def replaceContext(self):

        # 检测是否已经选择模板
        if self.current_template == {}:
            self.debug("还未选择任何模板, 跳过此次替换", type='error')
            return

        # 检测替换字典是否为空
        if len(self.replacements) == 0:
            self.debug("没有输入任何替换的内容, 跳过此次替换", type='warn')
            return

        # 获取模板内容
        context = self.current_template.get('content')

        # 遍历字典中替换对并逐一替换
        for replacement in self.replacements.keys():
            context = context.replace(replacement, self.replacements[replacement])
            self.debug("已将关键词\"{0}\"替换为\"{1}\"".format(replacement, self.replacements[replacement]))
        self.debug("关键词替换完成", type='success')

        # 输出替换后的内容
        self.ui.textResult.setText(context)

    def copyResult(self):

        # 检测输出区是否为空
        if self.ui.textResult.toPlainText() == "":
            self.debug("输出区内没有可复制的内容", type='warn')
            return

        # 将输出区内容复制到剪切板
        pyperclip.copy(self.ui.textResult.toPlainText())
        self.debug("已将输出结果复制到剪切板", type='success')

    def importTemplate(self):

        # 打开选择文件对话框
        file_dialog = QFileDialog(self.ui)
        file_dir = file_dialog.getOpenFileName(self.ui, "导入模板文件", os.getcwd(), "模板文件 (*.json)")

        # 若未选择任何文件就关闭对话框
        if file_dir[0] == "":
            self.debug("已取消导入模板文件", type='warn')
            return

        # 打开选择的文件并导入
        self.debug("正在尝试导入模板文件{0}...".format(file_dir[0]))
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
                self.debug("已损坏的模板文件：{0}, 模板文件内容为空或不合法, 跳过当前模板文件".format(display_name), type='error')
                return

            except UnicodeDecodeError:
                self.debug("已损坏的模板文件：{0}, 模板文件编码格式有误, 跳过当前模板文件".format(display_name), type='error')
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
                self.debug("已损坏的模板文件：{0}, 缺失如下键值对:{1}, 跳过当前模板文件".format(display_name, missed_keys)
                           , type='error')
                return

            # 检测是否已经添加了相同的模板
            elif data in self.templates:
                self.debug("已经载入相同的模板文件: {0}, 跳过当前模板文件".format(display_name)
                           , type='warn')
                return

            # 将模板添加到模板列表和模板列表框中
            self.templates.append(data)
            self.ui.comboBox.addItem(data.get('name'))
        self.debug("已载入模板文件: " + data.get('name'), type='success')

    def customTemplate(self):
        self.debug("已打开自定义模板编辑器", type='success')
        self.custom_form.ui.show()

    def quitProgram(self):

        # 弹窗确认是否退出程序
        msgbox = QMessageBox()
        msgbox.setWindowTitle("确认退出")
        msgbox.setText("你确定要关闭法典生成器吗？")
        msgbox.setIcon(QMessageBox.Question)
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.Yes)
        msgbox.setButtonText(QMessageBox.Yes, "确定")
        msgbox.setButtonText(QMessageBox.No, "再想想")
        ret = msgbox.exec_()
        if ret == QMessageBox.Yes:
            # 检测是否有未保存的改动
            if not self.custom_form.saved:
                # 弹窗确认是否退出程序
                msgbox = QMessageBox()
                msgbox.setWindowTitle("你有未保存的改动")
                msgbox.setText("你在模板编辑器中有未保存的改动，你确定要关闭法典生成器吗？")
                msgbox.setInformativeText("警告:该操作不可逆, 你将丢失所有未保存的改动")
                msgbox.setIcon(QMessageBox.Warning)
                msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msgbox.setDefaultButton(QMessageBox.Yes)
                msgbox.setButtonText(QMessageBox.Yes, "确定退出程序")
                msgbox.setButtonText(QMessageBox.No, "去保存改动")
                ret = msgbox.exec_()

                if ret == QMessageBox.No:
                    self.custom_form.ui.show()
                    return

            sys.exit(0)
        else:
            return


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
        self.ui = QUiLoader().load('ui\\FormCustom.ui')

        # 绑定按钮事件
        self.ui.buttonAdd.clicked.connect(self.addKeyword)
        self.ui.buttonRemove.clicked.connect(self.removeKeyword)
        self.ui.buttonClear.clicked.connect(self.clearTemplate)
        self.ui.buttonSave.clicked.connect(self.saveTemplate)
        self.ui.buttonClose.clicked.connect(self.closeEditor)

        # 绑定编辑框事件
        self.ui.textContent.textChanged.connect(self.contentChange)
        self.ui.lineName.textEdited.connect(self.nameChange)

        # 绑定列表框事件
        self.ui.listKeyword.itemClicked.connect(self.keywordChange)

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

        # 从列表和列表框中移除关键词
        self.ui.listKeyword.takeItem(index)
        del self.keywords[index]
        del self.descriptions[index]

        # 清空关键词和描述输入框
        self.ui.lineKeyword.clear()
        self.ui.lineDescription.clear()

        # 标记为未保存
        self.changeOccur()

    def clearTemplate(self):

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

        if ret == QMessageBox.Yes:

            # 检测是否已经保存
            if not self.saved:
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
            msgbox.setDetailedText("当前同名模板:{0}\\FDTemplates\\{1}.json".format(os.getcwd(), self.name))
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.Yes)
            msgbox.setButtonText(QMessageBox.Yes, "是")
            msgbox.setButtonText(QMessageBox.No, "否")
            ret = msgbox.exec_()
            if ret == QMessageBox.No:
                return

        # 处理json字典
        json_dump = {'Name': self.name, 'Content': self.content, 'Rolename': self.keywords,
                     'RoleDes': self.descriptions}

        # 保存json文件
        with open("FDTemplates\\{0}.json".format(self.name), "w") as f:
            json.dump(json_dump, f)

        # 标记已经保存
        self.saved = True
        self.ui.labelUnsaved.setText("<span style=\" font-size:10pt; color:Green;\">所有改动已保存</span>")

        QMessageBox.information(self.ui,
                                "保存成功",
                                "模板文件已保存至{0}\\FDTemplates\\{1}.json".format(os.getcwd(), self.name),
                                QMessageBox.Ok)

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
            # 关闭当前窗口
            self.ui.close()

    def changeOccur(self):

        # 模板发生改动
        self.saved = False
        self.ui.labelUnsaved.setVisible(True)
        self.ui.labelUnsaved.setText("<span style=\" font-size:10pt; font-weight:600; color:Red;\">您有未保存的改动!</span>")


# 新建 Pyside2 Application
app = QApplication([])
# 实例化主窗口
fdMain = FDMain(debug=False)
# 显示主窗口
fdMain.ui.show()
# 开始事件循环
app.exec_()
