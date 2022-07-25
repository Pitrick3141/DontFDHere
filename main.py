import sys
import time
import os
import json
import pyperclip

from PySide2.QtWidgets import QApplication, QMessageBox, QFileDialog
from PySide2.QtUiTools import QUiLoader


def quitProgram():

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
        sys.exit(0)
    else:
        return


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
        self.ui.buttonQuit.clicked.connect(quitProgram)
        self.ui.buttonOpenTemplateDir.clicked.connect(openDir)
        self.ui.buttonImportTemplate.clicked.connect(self.importTemplate)

        # 绑定下模板选择框事件
        self.ui.comboBox.currentIndexChanged.connect(self.showTemplate)

        # 绑定关键词选择框事件
        self.ui.listKeyword.currentRowChanged.connect(self.keywordChange)

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
            output_message = "{0}[Info] {1}".format(current_time, text)

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


# 新建 Pyside2 Application
app = QApplication([])
# 实例化主窗口
fdMain = FDMain(debug=False)
# 显示主窗口
fdMain.ui.show()
# 开始事件循环
app.exec_()
