import time
import sys
import os
import json
import pyperclip
import requests
import hashlib

from PySide2.QtWidgets import QMessageBox
from PySide2.QtUiTools import QUiLoader

import FDRescue
import global_var
import FDDebug
import FDUtility
import FDUpdate
import FDCustom


global fdMain


class FDMain:

    # 正在读取模板
    loading_templates = False
    # 当前模板
    current_template = {}
    # 当前替换内容字典
    replacements = {}
    # 当前替换对象
    current_replacement = ""

    def __init__(self) -> None:

        # 加载主窗口UI
        try:
            self.ui = QUiLoader().load('ui\\MainForm.ui')
        except RuntimeError:
            # 缺少必要文件，启用恢复模式
            FDRescue.rescueMode()
            self.ui = QUiLoader().load('ui\\MainForm.ui')

        # 设置窗口图标
        self.ui.setWindowIcon(global_var.app_icon)

        # 彩蛋按钮
        if not os.path.exists("FDTemplates\\discovered_eggs.json"):
            self.ui.buttonEggs.setVisible(False)
            global_var.set_config('discovered_eggs', {})

        # 绑定按钮事件
        self.ui.buttonRefreshList.clicked.connect(self.loadTemplates)
        self.ui.buttonReplace.clicked.connect(self.replaceContext)
        self.ui.buttonCopy.clicked.connect(self.copyResult)
        self.ui.buttonQuit.clicked.connect(self.quitProgram)
        self.ui.buttonEggs.clicked.connect(self.showEggs)
        self.ui.buttonMenu.clicked.connect(self.openMenu)

        # 绑定下模板选择框事件
        self.ui.comboBox.currentIndexChanged.connect(self.showTemplate)

        # 绑定关键词选择框事件
        self.ui.listKeyword.itemClicked.connect(self.keywordChange)

        # 绑定输入框事件
        self.ui.lineCustomKeyword.textEdited.connect(self.customKeyword)
        self.ui.lineReplacement.textEdited.connect(self.replacementChange)

        if __name__ == '__main__':
            FDDebug.debug("主界面初始化完成", type='success')

    @staticmethod
    def openMenu():
        if global_var.get_config('enable_debug') is True:
            FDUtility.set_debug_button_visible(True)
        else:
            FDUtility.set_debug_button_visible(False)
        FDUtility.display()

    def loadTemplates(self):

        # 读取模板，防止改变列表框列表而触发显示模板
        self.loading_templates = True
        # 清空框架选择列表框和框架列表
        self.ui.comboBox.clear()
        global_var.templates_clear()
        global_var.templates_hash_clear()

        FDDebug.debug("开始载入模板...")

        # 若不存在模板文件夹则建立并从云端同步模板
        if not os.path.exists("FDTemplates"):
            QMessageBox.critical(self.ui, "错误",
                                 "模板文件夹不存在或已损坏\n正在建立新的模板文件夹并从云端同步模板文件")
            FDUtility.syncTemplates()
            return

        # 默认模板文件目录
        template_dir = os.walk("FDTemplates")

        # 遍历模板文件目录
        for path, dir_list, file_list in template_dir:
            for file_name in file_list:

                # 检查文件拓展名是否合法
                if not file_name.find(".json") == -1:
                    with open(os.path.abspath(path) + "\\" + file_name, 'rb') as f:
                        # hash
                        data = f.read()
                        hash_obj = hashlib.sha1()
                        hash_str = "blob %u\0" % len(data) + data.decode('utf-8')
                        hash_obj.update(hash_str.encode('utf-8'))
                        hash_value = hash_obj.hexdigest()

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
                            FDDebug.debug(
                                "已损坏的模板文件：{0}, 模板文件内容为空或不合法, 跳过当前模板文件".format(display_name),
                                type='error')
                            continue
                        except UnicodeDecodeError:
                            FDDebug.debug(
                                "已损坏的模板文件：{0}, 模板文件编码格式有误, 跳过当前模板文件".format(display_name),
                                type='error')
                            continue

                        # 将键全部转换为小写，避免大小写混淆
                        for key, value in original_data.items():
                            data[key.lower()] = value

                        # 检测是否是配置文件
                        if 'config' in data.keys():
                            FDDebug.debug("发现配置文件：{0}, 开始解析".format(display_name))
                            self.applyConfig(data)
                            continue

                        # 检测是否有缺失的必需键值对
                        for checked_key in ['name', 'content', 'rolename', 'roledes']:
                            if checked_key not in data.keys():
                                missed_keys.append(checked_key)

                        # 如果有缺失的关键键值对
                        if not len(missed_keys) == 0:
                            FDDebug.debug("已损坏的模板文件：{0}, 缺失如下键值对:{1}, 跳过当前模板文件".format(
                                display_name,
                                missed_keys)
                                , type='error')
                            continue

                        # 检测是否已经添加了相同的模板
                        elif hash_value in global_var.templates_hash_keys():
                            FDDebug.debug("已经载入相同的模板文件: {0}, 跳过当前模板文件".format(
                                global_var.get_templates_hash(hash_value))
                                , type='warn')
                            continue

                        # 将模板添加到模板列表和模板列表框中
                        global_var.templates_append(data)
                        global_var.set_templates_hash(hash_value, data.get('name'))
                        self.ui.comboBox.addItem(data.get('name'))

                    FDDebug.debug("已载入模板文件: " + data.get('name'))

                # 文件拓展名不为.json
                else:
                    FDDebug.debug("不支持的文件类型(目前仅支持.json格式)：{0}, 跳过当前模板文件".format(display_name),
                                  type='error')

        self.ui.comboBox.setCurrentIndex(-1)
        self.loading_templates = False
        FDDebug.debug("模板载入完成,共载入{0}个模板文件".format(global_var.len_templates()), type='success')

    def applyConfig(self, config_file):
        # 应用配置文件

        # 检测配置文件是否启用
        if not config_file.get('config') is True:
            FDDebug.debug("配置文件未被启用或格式错误，跳过本次解析", type='error')
            return

        # 检测配置文件版本是否符合
        if not config_file.get('version') in [global_var.current_version, '*', 'all']:
            FDDebug.debug(
                "配置文件版本不符或格式错误，跳过本次解析<br>当前版本: {}<br>配置文件版本: {}".format(
                    global_var.current_version,
                    config_file.get('version')),
                type='error')
            return

        # 可用配置项
        valid_keys = ['ignored_version', 'allow_command', 'discovered_eggs', 'enable_debug']

        # 配置项计数
        cnt = 0

        # 应用配置项
        for key in valid_keys:

            # 读取配置文件中的配置项
            if key in config_file.keys():
                FDDebug.debug("发现配置项: {} = {}".format(key, config_file.get(key)))

                # 检测配置项是否已经存在
                if key in global_var.config_keys():

                    # 若重复添加相同的配置项
                    if global_var.get_config(key) == config_file.get(key):
                        FDDebug.debug("已存在完全相同的配置项: {}, 配置项值为{}, 跳过本次应用配置项值".format(
                            key,
                            global_var.get_config(key)),
                            type='warn')
                        continue

                    FDDebug.debug("已存在的配置项: {}"
                                  "<br>原配置项值: {}"
                                  "<br>新配置项值: {}, 已弹窗询问".format(key, global_var.get_config(key), config_file.get(key)),
                                  type='warn')

                    # 弹窗询问处理方法
                    msgbox = QMessageBox()
                    msgbox.setWindowTitle("重复的配置项")
                    msgbox.setText("你要添加的配置项已存在")
                    msgbox.setInformativeText("你想要覆盖原本的配置项值吗？")
                    msgbox.setDetailedText(
                        "已存在的配置项: {}\n原配置项值: {}\n新配置项值: {}".format(
                            key,
                            global_var.get_config(key),
                            config_file.get(key)))
                    msgbox.setIcon(QMessageBox.Question)
                    msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msgbox.setDefaultButton(QMessageBox.Yes)
                    msgbox.setButtonText(QMessageBox.Yes, "使用新配置项值")
                    msgbox.setButtonText(QMessageBox.No, "保留原配置项值")
                    ret = msgbox.exec_()

                    # 处理弹窗结果
                    if ret == QMessageBox.Yes:
                        # 覆盖为新配置项值
                        global_var.set_config(key, config_file.get(key))
                        cnt += 1
                        FDDebug.debug("配置项{}已被覆盖为新配置项值: {}".format(key, config_file.get(key)),
                                      type='success')
                    else:
                        # 保留原配置项值
                        FDDebug.debug("配置项{}仍保留为原配置项值: {}".format(key, global_var.get_config(key)), type='success')
                        return

                else:

                    # 应用配置项
                    global_var.set_config(key, config_file.get(key))
                    cnt += 1
                    FDDebug.debug("配置项{}已设为: {}".format(key, config_file.get(key)), type='success')

                if key == 'discovered_eggs':
                    self.ui.buttonEggs.setIcon(global_var.app_icon)
                    self.ui.buttonEggs.setText("已发现彩蛋: {}".format(len(global_var.get_config('discovered_eggs'))))

        FDDebug.debug("配置文件解析完成，共应用了{}个配置项".format(cnt), type='success')

    def showTemplate(self):

        # 若还未完成读取则不显示模板
        if self.loading_templates:
            return

        # 重置替换关键词字典
        self.replacements.clear()
        self.current_replacement = ""

        self.current_template = global_var.get_templates(self.ui.comboBox.currentIndex())

        # 将选择的模板输出
        self.ui.textResult.setText(self.current_template.get('content'))
        FDDebug.debug("已选择模板:" + self.ui.comboBox.currentText())

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

        if self.ui.textResult.toPlainText() == "EnableDebugMode" \
                and self.ui.lineCustomKeyword.text() == "True" \
                and global_var.get_config('allow_command') is True:
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            global_var.set_config('enable_debug', True)
            FDUtility.set_debug_button_visible(True)
            QMessageBox.information(self.ui, "调试模式已启用", "调试输出模式已被启用", QMessageBox.Ok)
            FDDebug.debug("调试输出模式已被启用")

        if self.ui.textResult.toPlainText() == "EnableDebugMode" \
                and self.ui.lineCustomKeyword.text() == "False" \
                and global_var.get_config('allow_command') is True:
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            global_var.set_config('enable_debug', False)
            FDUtility.set_debug_button_visible(False)
            QMessageBox.information(self.ui, "调试模式已禁用", "调试输出模式已被禁用", QMessageBox.Ok)
            FDDebug.debug("调试输出模式已被禁用")

        if self.ui.textResult.toPlainText() == "FormUpdate" \
                and self.ui.lineCustomKeyword.text() == "Show" \
                and global_var.get_config('allow_command') is True:
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()

            FDUpdate.set_data(requests.get(
                url='https://api.github.com/repos/Pitrick3141/DontFDHere/releases/latest').json())
            FDUpdate.display()

        if self.ui.textResult.toPlainText() == "SyncTemplates" \
                and self.ui.lineCustomKeyword.text() == "Check" \
                and global_var.get_config('allow_command') is True:
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            FDUtility.syncTemplates()

        if self.ui.textResult.toPlainText() == "AboutInfo" \
                and self.ui.lineCustomKeyword.text() == "Show":
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            QMessageBox.about(self.ui, "关于",
                              "DontFDHere {} by ikcye (Github@Pitrick3141)\n别在这立法典，你又不是汉谟拉比".format(
                                  global_var.current_version))
            self.findEgg("我是谁？")

        if self.ui.lineCustomKeyword.text() == "114514" \
                and '恶 臭 关 键 词' not in global_var.get_config('discovered_eggs').keys():
            QMessageBox.information(self.ui, "要 素 察 觉",
                                    "这么臭的关键词真的有替换的必要吗？(半恼)\n感觉不如1919810...位数"
                                    .format(global_var.current_version))
            self.ui.lineCustomKeyword.setText("1919810")
            self.findEgg('恶 臭 关 键 词')

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
            FDDebug.debug("还未选择任何模板, 跳过此次替换", type='error')
            return

        # 检测替换字典是否为空
        if len(self.replacements) == 0:
            FDDebug.debug("没有输入任何替换的内容, 跳过此次替换", type='warn')
            return

        # 获取模板内容
        context = self.current_template.get('content')

        # 遍历字典中替换对并逐一替换
        for replacement in self.replacements.keys():
            context = context.replace(replacement, self.replacements[replacement])
            FDDebug.debug("已将关键词\"{0}\"替换为\"{1}\"".format(replacement, self.replacements[replacement]))
        FDDebug.debug("关键词替换完成", type='success')

        # 输出替换后的内容
        self.ui.textResult.setText(context)

    def copyResult(self):

        # 检测输出区是否为空
        if self.ui.textResult.toPlainText() == "":
            FDDebug.debug("输出区内没有可复制的内容", type='warn')
            return

        # 将输出区内容复制到剪切板
        pyperclip.copy(self.ui.textResult.toPlainText())
        FDDebug.debug("已将输出结果复制到剪切板", type='success')

    def showEggs(self):
        discovered_eggs = global_var.get_config('discovered_eggs')
        eggs_list = ""
        for key in discovered_eggs.keys():
            eggs_list += "【{}】 发现时间: {}\n".format(key, discovered_eggs[key])
        QMessageBox.information(self.ui, "恭喜你已经找到了{}个彩蛋".format(len(discovered_eggs)), eggs_list)

    def findEgg(self, title):
        if 'discovered_eggs' not in global_var.config_keys():
            global_var.set_config('discovered_eggs', {})
        discovered_eggs = global_var.get_config('discovered_eggs')
        if title not in discovered_eggs.keys():
            discovered_eggs[title] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            global_var.set_config('discovered_eggs', discovered_eggs)
        self.ui.buttonEggs.setVisible(True)
        self.ui.buttonEggs.setIcon(global_var.app_icon)
        self.ui.buttonEggs.setText("已发现彩蛋: {}".format(len(discovered_eggs)))
        FDDebug.debug("发现了彩蛋【{}】, 总计已发现彩蛋{}个".format(title, len(discovered_eggs)))
        json_dump = {'config': True, 'version': '*', 'discovered_eggs': discovered_eggs}

        # 保存配置文件
        with open("FDTemplates\\discovered_eggs.json", "w") as f:
            json.dump(json_dump, f)

        FDDebug.debug("配置文件已保存至{}\\{}".format(os.getcwd(), "FDTemplates\\discovered_eggs.json"))

    @staticmethod
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
            # 检测是否有未保存的改动
            if not FDCustom.get_saved():
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
                    FDCustom.display()
                    return

            sys.exit(0)
        else:
            return


def init():
    global fdMain
    fdMain = FDMain()


def display():
    FDDebug.debug("已打开主界面", type='success')
    fdMain.ui.show()


def loadTemplates():
    fdMain.loadTemplates()
    return


def applyConfig(config):
    fdMain.applyConfig(config)
    return
