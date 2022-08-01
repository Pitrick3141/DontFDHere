import time
import sys
import os
import json

import pyperclip
import requests
import hashlib

from PySide2.QtWidgets import QApplication, QMessageBox, QFileDialog, QMainWindow, QPushButton, QDialogButtonBox
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QIcon

from config import current_version, is_debug_enabled


class FDMain:
    # 是否启用调试输出
    isDebugEnabled = False
    # 模板列表
    templates = []
    # 模板hash字典，用于同步模板
    templates_hash = {}
    # 配置字典
    configs = {}
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
        try:
            self.ui = QUiLoader().load('ui\\MainForm.ui')
        except RuntimeError:
            QMessageBox.critical(QMainWindow(), "致命错误",
                                 "读取ui文件ui\\MainForm.ui失败，该文件可能不存在或已损坏，程序无法运行")
            sys.exit(1)

        # 设置窗口图标
        self.app_icon = QIcon("ui\\icon.png")
        self.ui.setWindowIcon(self.app_icon)

        # 传入参数处理
        self.isDebugEnabled = kwargs['debug']

        # 是否显示调试输出
        if not self.isDebugEnabled:
            self.ui.setMinimumSize(730, 520)
            self.ui.setMaximumSize(730, 520)

        # 彩蛋按钮
        if not os.path.exists("FDTemplates\\discovered_eggs.json"):
            self.ui.buttonEggs.setVisible(False)
            self.configs['discovered_eggs'] = {}

        # 绑定按钮事件
        self.ui.buttonRefreshList.clicked.connect(self.loadTemplates)
        self.ui.buttonReplace.clicked.connect(self.replaceContext)
        self.ui.buttonCopy.clicked.connect(self.copyResult)
        self.ui.buttonQuit.clicked.connect(self.quitProgram)
        # self.ui.buttonOpenTemplateDir.clicked.connect(self.openDir)
        # self.ui.buttonImportTemplate.clicked.connect(self.importTemplate)
        # self.ui.buttonCustomTemplate.clicked.connect(self.customTemplate)
        self.ui.buttonEggs.clicked.connect(self.showEggs)
        self.ui.buttonMenu.clicked.connect(self.openMenu)

        # 绑定下模板选择框事件
        self.ui.comboBox.currentIndexChanged.connect(self.showTemplate)

        # 绑定关键词选择框事件
        self.ui.listKeyword.itemClicked.connect(self.keywordChange)

        # 绑定输入框事件
        self.ui.lineCustomKeyword.textEdited.connect(self.customKeyword)
        self.ui.lineReplacement.textEdited.connect(self.replacementChange)

        self.debug("主界面加载完成", type='success')

    def debug(self, text: str, **kwargs) -> None:
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

    def openMenu(self):
        self.debug("已打开功能菜单", type='success')
        fdMenu.ui.show()

    def checkUpdate(self):

        # 检查应用更新
        latest = True
        self.debug("开始检查更新")

        # 获取Github Repo信息
        try:
            r = requests.get(url='https://api.github.com/repos/Pitrick3141/DontFDHere/releases/latest')
        except requests.exceptions.ConnectionError:
            self.debug("网络连接异常，检查更新失败", type='error')
            return

        # 反序列化json数据
        json_data = r.json()
        self.debug("检查更新完成", type='success')

        # 最新版本号
        latest_version = json_data['tag_name']

        # 拆分最新版本号和当前版本号以便比较
        cmp_version = latest_version[1:].split('.')
        cmp_current = current_version[1:].split('.')

        # 发布日期
        publish_time = json_data['published_at']
        # 发布文件
        assets = json_data['assets']
        # 发布文件大小
        file_size = assets[0]['size']
        # 文件描述
        file_des = json_data['body']

        self.debug("检查更新结果:"
                   "<br>当前版本: {}"
                   "<br>最新版本: {}"
                   "<br>最新版本发布时间: {}"
                   "<br>发布文件大小: {} bytes ({} MB)"
                   "<br>最新版本更新说明: {}"
                   .format(current_version,
                           latest_version,
                           publish_time,
                           file_size,
                           file_size / 1000000,
                           file_des))

        # 比较最新版本号和当前版本号
        for v in range(len(cmp_version)):
            if int(cmp_version[v]) > int(cmp_current[v]):
                latest = False
                break
            elif int(cmp_version[v]) < int(cmp_current[v]):
                self.debug("当前版本号较最新版本号更高，可能存在错误", type='warn')
                break
            else:
                continue

        # 若当前版本不是最新
        if not latest:

            # 检测是否忽略了新版本更新
            if 'ignored_version' in self.configs.keys():
                if latest_version in self.configs.get('ignored_version'):
                    self.debug("发现新版本{}，但已被配置项忽视，跳过本次更新".format(latest_version), type='warn')
                    return

            # 弹窗提示更新
            self.debug("发现新版本，已弹出提示窗口", type='warn')
            fdUpdate.setData(json_data)
            fdUpdate.ui.show()

        else:
            self.debug("当前已经是最新版本", type='success')
            if self.initialized:
                QMessageBox.information(self.ui, "检查更新完成", "当前已经是最新版本: " + current_version)

    def syncTemplates(self):
        # 同步计数
        cnt_found = 0
        cnt_new = 0
        cnt_existed = 0
        cnt_changed = 0
        cnt_downloaded = 0

        # 从Github同步模板
        self.debug("开始同步模板")
        try:
            r = requests.get(url='https://api.github.com/repos/Pitrick3141/DontFDHere/contents/FDTemplates',
                             params={'ref': 'master'})
        except requests.exceptions.ConnectionError:
            self.debug("网络连接异常，同步模板失败", type='error')
            return

        # 反序列化json数据
        json_data = r.json()

        self.debug("已获取模板列表", type='success')

        # 遍历云端模板列表
        for template in json_data:
            cnt_found += 1

            # 获取模板信息
            name = template['name'].replace('.json', '')
            sha = template['sha']
            file_size = template['size']
            download_url = template['download_url']

            # 检查是否有新模板
            if name not in self.templates_hash.values():
                cnt_new += 1

                self.debug("发现新模板: {}<br>大小: {} Bytes, 已弹窗询问".format(name, file_size))

                # 弹窗确认是否下载
                ret = QMessageBox.question(self.ui, "下载模板确认", "是否下载新模板{}.json?\n模板大小: {}Bytes ({}MB)"
                                           .format(name,
                                                   file_size,
                                                   file_size / 1000000))

                if ret == QMessageBox.Yes:
                    if self.downloadTemplate(download_url, name):
                        cnt_downloaded += 1

            # 重名模板检查哈希值是否相同
            elif sha not in self.templates_hash.keys():
                cnt_changed += 1

                # 哈希值不同弹窗确认是否覆盖
                self.debug("发现改动的模板: {}<br>大小: {} Bytes, 已弹窗询问".format(name, file_size))
                msgbox = QMessageBox()
                msgbox.setWindowTitle("下载模板确认")
                msgbox.setText("云端模板与本地模板同名但内容不同\n是否覆盖下载？")
                msgbox.setDetailedText("当前本地同名模板:{0}\\FDTemplates\\{1}.json".format(os.getcwd(), name))
                msgbox.setIcon(QMessageBox.Warning)
                msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.Ok | QMessageBox.No)
                msgbox.setDefaultButton(QMessageBox.Yes)
                msgbox.setButtonText(QMessageBox.Yes, "覆盖下载")
                msgbox.setButtonText(QMessageBox.Ok, "重命名下载")
                msgbox.setButtonText(QMessageBox.No, "不下载")
                ret = msgbox.exec_()

                if ret == QMessageBox.Yes:
                    # 覆盖下载
                    if self.downloadTemplate(download_url, name):
                        cnt_downloaded += 1

                elif ret == QMessageBox.Ok:
                    # 重命名下载
                    if self.downloadTemplate(download_url, name + "_云端同步"):
                        cnt_downloaded += 1

            else:
                cnt_existed += 1
                self.debug("模板已存在: {}, 跳过同步".format(self.templates_hash.get(sha)), type='warn')

        # 刷新模板列表
        if not cnt_downloaded == 0:
            self.loadTemplates()

        self.debug("模板同步完成"
                   "\n在云端共发现了{}个模板"
                   "\n其中{}个模板已是最新"
                   "\n{}个模板有变动"
                   "\n{}个模板在本地不存在"
                   "\n本次同步共下载了{}个模板".format(cnt_found, cnt_existed, cnt_changed, cnt_new, cnt_downloaded),
                   type='success')

        QMessageBox.information(self.ui, "模板同步完成",
                                "在云端共发现了{}个模板"
                                "\n其中{}个模板已是最新"
                                "\n{}个模板有变动"
                                "\n{}个模板在本地不存在"
                                "\n本次同步共下载了{}个模板".format(cnt_found, cnt_existed, cnt_changed, cnt_new, cnt_downloaded))

    def downloadTemplate(self, url, name) -> bool:
        self.debug("开始从{}下载模板".format(url))
        try:
            r = requests.get(url=url)
        except requests.exceptions.ConnectionError:
            self.debug("网络连接异常，模板下载失败", type='error')
            return False

        content = r.json()
        with open("FDTemplates\\{0}.json".format(name), "w") as f:
            json.dump(content, f)
        self.debug("模板文件已保存至{0}\\FDTemplates\\{1}.json".format(os.getcwd(), name), type='success')

        return True

    def loadTemplates(self):

        # 防止载入完成之前先读取
        self.initialized = False

        # 清空框架选择列表框和框架列表
        self.ui.comboBox.clear()
        self.templates.clear()
        self.templates_hash.clear()

        self.debug("开始载入模板...")

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
                            self.debug(
                                "已损坏的模板文件：{0}, 模板文件内容为空或不合法, 跳过当前模板文件".format(display_name),
                                type='error')
                            continue
                        except UnicodeDecodeError:
                            self.debug(
                                "已损坏的模板文件：{0}, 模板文件编码格式有误, 跳过当前模板文件".format(display_name),
                                type='error')
                            continue

                        # 将键全部转换为小写，避免大小写混淆
                        for key, value in original_data.items():
                            data[key.lower()] = value

                        # 检测是否是配置文件
                        if 'config' in data.keys():
                            self.debug("发现配置文件：{0}, 开始解析".format(display_name))
                            self.applyConfig(data)
                            continue

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
                        elif hash_value in self.templates_hash.keys():
                            self.debug("已经载入相同的模板文件: {0}, 跳过当前模板文件".format(
                                self.templates_hash.get(hash_value))
                                , type='warn')
                            continue

                        # 将模板添加到模板列表和模板列表框中
                        self.templates.append(data)
                        self.templates_hash[hash_value] = data.get('name')
                        self.ui.comboBox.addItem(data.get('name'))

                    self.debug("已载入模板文件: " + data.get('name'))

                # 文件拓展名不为.json
                else:
                    self.debug("不支持的文件类型(目前仅支持.json格式)：{0}, 跳过当前模板文件".format(display_name),
                               type='error')

        self.ui.comboBox.setCurrentIndex(-1)
        self.debug("模板载入完成,共载入{0}个模板文件".format(len(self.templates)), type='success')
        self.initialized = True

    def applyConfig(self, config_file):
        # 应用配置文件

        # 检测配置文件是否启用
        if not config_file.get('config') is True:
            self.debug("配置文件未被启用或格式错误，跳过本次解析", type='error')
            return

        # 检测配置文件版本是否符合
        if not config_file.get('version') in [current_version, '*', 'all']:
            self.debug(
                "配置文件版本不符或格式错误，跳过本次解析<br>当前版本: {}<br>配置文件版本: {}".format(current_version, config_file.get('version')),
                type='error')
            return

        # 可用配置项
        valid_keys = ['ignored_version', 'allow_command', 'discovered_eggs']

        # 配置项计数
        cnt = 0

        # 应用配置项
        for key in valid_keys:

            # 读取配置文件中的配置项
            if key in config_file.keys():
                self.debug("发现配置项: {} = {}".format(key, config_file.get(key)))

                # 检测配置项是否已经存在
                if key in self.configs.keys():

                    # 若重复添加相同的配置项
                    if self.configs.get(key) == config_file.get(key):
                        self.debug("已存在完全相同的配置项: {}, 配置项值为{}, 跳过本次应用配置项值".format(key, self.configs.get(key)),
                                   type='warn')
                        continue

                    self.debug("已存在的配置项: {}"
                               "<br>原配置项值: {}"
                               "<br>新配置项值: {}, 已弹窗询问".format(key, self.configs.get(key), config_file.get(key)), type='warn')

                    # 弹窗询问处理方法
                    msgbox = QMessageBox()
                    msgbox.setWindowTitle("重复的配置项")
                    msgbox.setText("你要添加的配置项已存在")
                    msgbox.setInformativeText("你想要覆盖原本的配置项值吗？")
                    msgbox.setDetailedText(
                        "已存在的配置项: {}\n原配置项值: {}\n新配置项值: {}".format(key, self.configs.get(key), config_file.get(key)))
                    msgbox.setIcon(QMessageBox.Question)
                    msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msgbox.setDefaultButton(QMessageBox.Yes)
                    msgbox.setButtonText(QMessageBox.Yes, "使用新配置项值")
                    msgbox.setButtonText(QMessageBox.No, "保留原配置项值")
                    ret = msgbox.exec_()

                    # 处理弹窗结果
                    if ret == QMessageBox.Yes:
                        # 覆盖为新配置项值
                        self.configs[key] = config_file.get(key)
                        cnt += 1
                        self.debug("配置项{}已被覆盖为新配置项值: {}".format(key, config_file.get(key)), type='success')
                    else:
                        # 保留原配置项值
                        self.debug("配置项{}仍保留为原配置项值: {}".format(key, self.configs.get(key)), type='success')
                        return

                else:

                    # 应用配置项
                    self.configs[key] = config_file.get(key)
                    cnt += 1
                    self.debug("配置项{}已设为新配置项值: {}".format(key, config_file.get(key)), type='success')

                if key == 'discovered_eggs':
                    self.ui.buttonEggs.setIcon(self.app_icon)
                    self.ui.buttonEggs.setText("已发现彩蛋: {}".format(len(self.configs['discovered_eggs'])))

        self.debug("配置文件解析完成，共应用了{}个配置项".format(cnt), type='success')

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

        if self.ui.textResult.toPlainText() == "EnableDebugMode" \
                and self.ui.lineCustomKeyword.text() == "True" \
                and self.configs.get('allow_command') is True:
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            QMessageBox.information(self.ui, "调试模式已启用", "调试输出模式已被启用", QMessageBox.Ok)
            self.isDebugEnabled = True
            self.ui.setMinimumSize(1290, 520)
            self.ui.setMaximumSize(1290, 520)
            self.debug("调试输出模式已被启用")

        if self.ui.textResult.toPlainText() == "EnableDebugMode" \
                and self.ui.lineCustomKeyword.text() == "False" \
                and self.configs.get('allow_command') is True:
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            QMessageBox.information(self.ui, "调试模式已禁用", "调试输出模式已被禁用", QMessageBox.Ok)
            self.isDebugEnabled = False
            self.ui.setMinimumSize(730, 520)
            self.ui.setMaximumSize(730, 520)
            self.debug("调试输出模式已被禁用")

        if self.ui.textResult.toPlainText() == "FormUpdate" \
                and self.ui.lineCustomKeyword.text() == "Show" \
                and self.configs.get('allow_command') is True:
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            fdUpdate.setData(requests.get(
                url='https://api.github.com/repos/Pitrick3141/DontFDHere/releases/latest').json())
            fdUpdate.ui.show()

        if self.ui.textResult.toPlainText() == "SyncTemplates" \
                and self.ui.lineCustomKeyword.text() == "Check" \
                and self.configs.get('allow_command') is True:
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            self.syncTemplates()

        if self.ui.textResult.toPlainText() == "AboutInfo" \
                and self.ui.lineCustomKeyword.text() == "Show":
            self.ui.textResult.clear()
            self.ui.lineCustomKeyword.clear()
            QMessageBox.about(self.ui, "关于",
                              "DontFDHere {} by ikcye (Github@Pitrick3141)\n别在这立法典，你又不是汉谟拉比".format(current_version))
            self.findEgg("我是谁？")

        if self.ui.lineCustomKeyword.text() == "114514" \
                and '恶 臭 关 键 词' not in self.configs['discovered_eggs'].keys():
            QMessageBox.information(self.ui, "要 素 察 觉",
                                    "这么臭的关键词真的有替换的必要吗？(半恼)\n感觉不如1919810...位数".format(
                                        current_version))
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

        with open(file_dir[0], 'rb') as f:
            # hash
            data = f.read()
            hash_obj = hashlib.sha1()
            hash_str = "blob %u\0" % len(data) + data.decode('utf-8')
            hash_obj.update(hash_str.encode('utf-8'))
            hash_value = hash_obj.hexdigest()

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
                self.debug("已损坏的模板文件：{0}, 模板文件内容为空或不合法, 跳过当前模板文件".format(display_name),
                           type='error')
                return
            except UnicodeDecodeError:
                self.debug("已损坏的模板文件：{0}, 模板文件编码格式有误, 跳过当前模板文件".format(display_name),
                           type='error')
                return

            # 将键全部转换为小写，避免大小写混淆
            for key, value in original_data.items():
                data[key.lower()] = value

            # 检测是否是配置文件
            if 'config' in data.keys():
                self.debug("发现配置文件：{0}, 开始解析".format(display_name))
                self.applyConfig(data)
                return

            # 检测是否有缺失的必需键值对
            for checked_key in ['name', 'content', 'rolename', 'roledes']:
                if checked_key not in data.keys():
                    missed_keys.append(checked_key)

            # 如果有缺失的关键键值对
            if not len(missed_keys) == 0:
                self.debug(
                    "已损坏的模板文件：{0}, 缺失如下键值对:{1}, 跳过当前模板文件".format(display_name, missed_keys)
                    , type='error')
                return

            # 检测是否已经添加了相同的模板
            elif hash_value in self.templates_hash.keys():
                self.debug("已经载入相同的模板文件: {0}, 跳过当前模板文件".format(self.templates_hash.get(hash_value))
                           , type='warn')
                return

            # 将模板添加到模板列表和模板列表框中
            self.templates.append(data)
            self.templates_hash[hash_value] = data.get('name')
            self.ui.comboBox.addItem(data.get('name'))
        self.debug("已载入模板文件: " + data.get('name'), type='success')

    def customTemplate(self):
        self.debug("已打开自定义模板编辑器", type='success')
        fdCustom.ui.show()

    def showEggs(self):
        eggs_list = ""
        for key in self.configs['discovered_eggs'].keys():
            eggs_list += "【{}】 发现时间: {}\n".format(key, self.configs['discovered_eggs'][key])
        QMessageBox.information(self.ui, "恭喜你已经找到了{}个彩蛋".format(len(self.configs['discovered_eggs'])),
                                eggs_list)

    def findEgg(self, title):
        if 'discovered_eggs' not in self.configs.keys():
            self.configs['discovered_eggs'] = {}
        if title not in self.configs['discovered_eggs'].keys():
            self.configs['discovered_eggs'][title] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.ui.buttonEggs.setVisible(True)
        self.ui.buttonEggs.setIcon(self.app_icon)
        self.ui.buttonEggs.setText("已发现彩蛋: {}".format(len(self.configs['discovered_eggs'])))
        self.debug("发现了彩蛋【{}】, 总计已发现彩蛋{}个".format(title, len(self.configs['discovered_eggs'])))
        json_dump = {'config': True, 'version': '*', 'discovered_eggs': self.configs.get('discovered_eggs')}

        # 保存配置文件
        with open("FDTemplates\\discovered_eggs.json", "w") as f:
            json.dump(json_dump, f)

        fdMain.debug("配置文件已保存至{}\\{}".format(os.getcwd(), "FDTemplates\\discovered_eggs.json"))

    @staticmethod
    def openDir():
        # 打开模板文件目录
        os.startfile(os.getcwd() + "\\FDTemplates")

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
            if not fdCustom.saved:
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
                    fdCustom.ui.show()
                    return

            sys.exit(0)
        else:
            return


class FDMenu:
    def __init__(self):
        # 加载菜单UI
        self.ui = QUiLoader().load('ui\\FormMenu.ui')

        # 设置窗口图标
        self.ui.setWindowIcon(fdMain.app_icon)

        # 弹窗按钮
        button_close = QPushButton('关闭菜单')

        # 将按钮添加到弹窗
        self.ui.buttonBox.addButton(button_close, QDialogButtonBox.AcceptRole)

        # 绑定按钮事件
        self.ui.buttonOpenTemplateDir.clicked.connect(fdMain.openDir)
        self.ui.buttonImportTemplate.clicked.connect(fdMain.importTemplate)
        self.ui.buttonCustomTemplate.clicked.connect(fdMain.customTemplate)
        self.ui.buttonSyncTemplates.clicked.connect(fdMain.syncTemplates)
        self.ui.buttonCheckUpdate.clicked.connect(fdMain.checkUpdate)


if __name__ == '__main__':
    # 新建 Pyside2 Application
    app = QApplication([])

# 实例化主窗口
fdMain = FDMain(debug=is_debug_enabled)

if __name__ == '__main__':
    # 实例化更新弹窗和自定义模板生成器
    from FDUpdate import FDUpdate

    fdUpdate = FDUpdate()

    from FDCustom import FDCustom

    fdCustom = FDCustom()
    fdMenu = FDMenu()

    # 显示主窗口并导入模板&检查更新
    fdMain.checkUpdate()
    fdMain.ui.show()
    fdMain.loadTemplates()

    # 开始事件循环
    app.exec_()

    # 窗口关闭后结束Application
    del app
