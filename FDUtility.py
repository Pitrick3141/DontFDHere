import hashlib
import json
import os

import requests
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QPushButton, QDialogButtonBox, QMessageBox, QFileDialog

import FDRescue
import global_var
import FDDebug
import FDUpdate
import FDCustom
import FDMain

global fdMenu


class FDMenu:
    def __init__(self):
        # 加载菜单UI
        try:
            self.ui = QUiLoader().load('ui\\FormMenu.ui')
        except RuntimeError:
            # 缺少必要文件，启用恢复模式
            FDRescue.rescueMode()
            self.ui = QUiLoader().load('ui\\FormMenu.ui')

        # 设置窗口图标
        self.ui.setWindowIcon(global_var.app_icon)

        # 是否是启动第一次检查更新
        self.first_check = True

        # 弹窗按钮
        button_close = QPushButton('关闭菜单')

        # 将按钮添加到弹窗
        self.ui.buttonBox.addButton(button_close, QDialogButtonBox.AcceptRole)

        # 绑定按钮事件
        self.ui.buttonOpenTemplateDir.clicked.connect(self.openDir)
        self.ui.buttonImportTemplate.clicked.connect(self.importTemplate)
        self.ui.buttonCustomTemplate.clicked.connect(self.customTemplate)
        self.ui.buttonSyncTemplates.clicked.connect(self.syncTemplates)
        self.ui.buttonCheckUpdate.clicked.connect(self.checkUpdate)
        self.ui.buttonDebug.clicked.connect(self.showDebug)

    def checkUpdate(self):

        # 检查应用更新
        latest = True
        FDDebug.debug("开始检查更新", who=self.__class__.__name__)

        # 获取Github Repo信息
        try:
            r = requests.get(url='https://api.github.com/repos/Pitrick3141/DontFDHere/releases/latest')
        except requests.exceptions.ConnectionError:
            FDDebug.debug("网络连接异常，检查更新失败", type='error', who=self.__class__.__name__)
            return

        # 反序列化json数据
        json_data = r.json()
        FDDebug.debug("检查更新完成", type='success', who=self.__class__.__name__)

        # 最新版本号
        latest_version = json_data['tag_name']

        # 拆分最新版本号和当前版本号以便比较
        cmp_version = latest_version[1:].split('.')
        cmp_current = global_var.current_version[1:].split('.')

        # 发布日期
        publish_time = json_data['published_at']
        # 发布文件
        assets = json_data['assets']
        # 发布文件大小
        file_size = assets[0]['size']
        # 文件描述
        file_des = json_data['body']

        FDDebug.debug("检查更新结果:"
                      "<br>----------"
                      "<br>当前版本: {}"
                      "<br>最新版本: {}"
                      "<br>最新版本发布时间: {}"
                      "<br>发布文件大小: {} bytes ({} MB)"
                      "<br>最新版本更新说明: {}"
                      "<br>----------"
                      .format(global_var.current_version,
                              latest_version,
                              publish_time,
                              file_size,
                              file_size / 1000000,
                              file_des), who=self.__class__.__name__)

        # 比较最新版本号和当前版本号
        for v in range(len(cmp_version)):
            if int(cmp_version[v]) > int(cmp_current[v]):
                latest = False
                break
            elif int(cmp_version[v]) < int(cmp_current[v]):
                FDDebug.debug("当前版本号较最新版本号更高，可能存在错误", type='warn', who=self.__class__.__name__)
                break
            else:
                continue

        # 若当前版本不是最新
        if not latest:

            # 检测是否忽略了新版本更新
            if 'ignored_version' in global_var.config_keys():
                if latest_version in global_var.get_config('ignored_version'):
                    FDDebug.debug("发现新版本{}，但已被配置项忽视，跳过本次更新".format(latest_version),
                                  type='warn',
                                  who=self.__class__.__name__)
                    return

            # 弹窗提示更新
            FDDebug.debug("发现新版本，已弹出提示窗口", type='warn', who=self.__class__.__name__)
            FDUpdate.set_data(json_data)
            FDUpdate.display()

        else:
            FDDebug.debug("当前已经是最新版本", type='success', who=self.__class__.__name__)
            if not self.first_check:
                QMessageBox.information(self.ui, "检查更新完成", "当前已经是最新版本: " + global_var.current_version)

        self.first_check = False

    def syncTemplates(self):
        # 同步计数
        cnt_found = 0
        cnt_new = 0
        cnt_existed = 0
        cnt_changed = 0
        cnt_downloaded = 0

        # 从Github同步模板
        FDDebug.debug("开始同步模板", who=self.__class__.__name__)

        # 若不存在模板文件夹则建立模板文件夹
        if not os.path.exists("FDTemplates"):
            os.mkdir("FDTemplates")

        try:
            r = requests.get(url='https://api.github.com/repos/Pitrick3141/DontFDHere/contents/FDTemplates',
                             params={'ref': 'master'})
        except requests.exceptions.ConnectionError:
            FDDebug.debug("网络连接异常，同步模板失败", type='error', who=self.__class__.__name__)
            return

        # 反序列化json数据
        json_data = r.json()

        FDDebug.debug("已获取模板列表", type='success', who=self.__class__.__name__)

        # 新模板列表
        new_templates = []

        # 遍历云端模板列表
        for template in json_data:
            cnt_found += 1

            # 获取模板信息
            name = template['name'].replace('.json', '')
            sha = template['sha']
            file_size = template['size']
            download_url = template['download_url']

            # 检查是否有新模板
            if name not in global_var.templates_hash_values():
                cnt_new += 1

                FDDebug.debug("发现新模板: {}<br>大小: {} Bytes".format(name, file_size), who=self.__class__.__name__)

                # 加入新模板列表中
                new_templates.append((name, file_size, download_url))

            # 重名模板检查哈希值是否相同
            elif sha not in global_var.templates_hash_keys():
                cnt_changed += 1

                # 哈希值不同弹窗确认是否覆盖
                FDDebug.debug("发现改动的模板: {}<br>大小: {} Bytes, 已弹窗询问".format(name, file_size),
                              who=self.__class__.__name__)
                msgbox = QMessageBox()
                msgbox.setWindowTitle("下载模板确认")
                msgbox.setText("云端模板与本地模板同名但内容不同\n是否覆盖下载？")
                msgbox.setInformativeText("当前本地同名模板:{0}\\FDTemplates\\{1}.json".format(os.getcwd(), name))
                msgbox.setIcon(QMessageBox.Warning)
                msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.Ok | QMessageBox.No)
                msgbox.setDefaultButton(QMessageBox.Yes)
                msgbox.setButtonText(QMessageBox.Yes, "覆盖下载")
                msgbox.setButtonText(QMessageBox.Ok, "重命名下载")
                msgbox.setButtonText(QMessageBox.No, "不下载")
                ret = msgbox.exec_()

                if ret == QMessageBox.Yes:
                    # 覆盖下载
                    FDDebug.debug("已选择覆盖下载模板: {}".format(name), who=self.__class__.__name__)
                    if self.downloadTemplate(download_url, name):
                        cnt_downloaded += 1

                elif ret == QMessageBox.Ok:
                    # 重命名下载
                    FDDebug.debug("已选择重命名下载模板: {}".format(name), who=self.__class__.__name__)
                    if self.downloadTemplate(download_url, name + "_云端同步"):
                        cnt_downloaded += 1
                else:
                    # 不下载
                    FDDebug.debug("已选择不下载模板: {}, 跳过同步".format(name), type='warn', who=self.__class__.__name__)

            else:
                cnt_existed += 1
                FDDebug.debug("模板已存在: {}, 跳过同步".format(global_var.get_templates_hash(sha)),
                              type='warn',
                              who=self.__class__.__name__)

        # 弹窗提示并下载所有新模板
        if len(new_templates) > 0:
            str_new_templates = "是否下载如下{}个新模板:\n".format(len(new_templates))
            for (temp_name, temp_size, temp_url) in new_templates:
                str_new_templates += "模板名称: {}.json 模板大小: {}Bytes ({}MB)\n".format(
                    temp_name,
                    temp_size,
                    temp_size / 1000000)
            ret = QMessageBox.question(self.ui, "下载模板确认", str_new_templates)

            if ret == QMessageBox.Yes:
                for (temp_name, temp_size, temp_url) in new_templates:
                    if self.downloadTemplate(temp_url, temp_name):
                        cnt_downloaded += 1

        # 刷新模板列表
        if not cnt_downloaded == 0:
            FDMain.loadTemplates()

        FDDebug.debug("模板同步完成"
                      "\n在云端共发现了{}个模板"
                      "\n其中{}个模板已是最新"
                      "\n{}个模板有变动"
                      "\n{}个模板在本地不存在"
                      "\n本次同步共下载了{}个模板".format(cnt_found, cnt_existed, cnt_changed, cnt_new, cnt_downloaded),
                      type='success',
                      who=self.__class__.__name__)

        QMessageBox.information(self.ui, "模板同步完成",
                                "在云端共发现了{}个模板"
                                "\n其中{}个模板已是最新"
                                "\n{}个模板有变动"
                                "\n{}个模板在本地不存在"
                                "\n本次同步共下载了{}个模板".format(
                                    cnt_found,
                                    cnt_existed,
                                    cnt_changed,
                                    cnt_new,
                                    cnt_downloaded))

    @staticmethod
    def downloadTemplate(url, name) -> bool:
        FDDebug.debug("开始从{}下载模板".format(url), who='FDMenu')
        try:
            r = requests.get(url=url)
        except requests.exceptions.ConnectionError:
            FDDebug.debug("网络连接异常，模板下载失败", type='error', who='FDMenu')
            return False

        content = r.json()
        with open("FDTemplates\\{0}.json".format(name), "w") as f:
            json.dump(content, f)
        FDDebug.debug("模板文件已保存至{0}\\FDTemplates\\{1}.json".format(os.getcwd(), name),
                      type='success',
                      who='FDMenu')

        return True

    def importTemplate(self):

        # 打开选择文件对话框
        file_dialog = QFileDialog(self.ui)
        file_dir = file_dialog.getOpenFileName(self.ui, "导入模板文件", os.getcwd(), "模板文件 (*.json)")

        # 若未选择任何文件就关闭对话框
        if file_dir[0] == "":
            FDDebug.debug("已取消导入模板文件", type='warn', who=self.__class__.__name__)
            return

        # 打开选择的文件并导入
        FDDebug.debug("正在尝试导入模板文件{0}...".format(file_dir[0]), who=self.__class__.__name__)

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
                FDDebug.debug("已损坏的模板文件：{0}, 模板文件内容为空或不合法, 跳过当前模板文件".format(display_name),
                              type='error',
                              who=self.__class__.__name__)
                return
            except UnicodeDecodeError:
                FDDebug.debug("已损坏的模板文件：{0}, 模板文件编码格式有误, 跳过当前模板文件".format(display_name),
                              type='error',
                              who=self.__class__.__name__)
                return

            # 将键全部转换为小写，避免大小写混淆
            for key, value in original_data.items():
                data[key.lower()] = value

            # 检测是否是配置文件
            if 'config' in data.keys():
                FDDebug.debug("发现配置文件：{0}, 开始解析".format(display_name), who=self.__class__.__name__)
                FDMain.applyConfig(data)
                return

            # 检测是否有缺失的必需键值对
            for checked_key in ['name', 'content', 'rolename', 'roledes']:
                if checked_key not in data.keys():
                    missed_keys.append(checked_key)

            # 如果有缺失的关键键值对
            if not len(missed_keys) == 0:
                FDDebug.debug("已损坏的模板文件：{0}, 缺失如下键值对:{1}, 跳过当前模板文件"
                              .format(display_name, missed_keys),
                              type='error',
                              who=self.__class__.__name__)
                return

            # 检测是否已经添加了相同的模板
            elif hash_value in global_var.templates_hash_keys():
                FDDebug.debug("已经载入相同的模板文件: {0}, 跳过当前模板文件"
                              .format(global_var.get_templates_hash(hash_value)),
                              type='warn',
                              who=self.__class__.__name__)
                return

            # 将模板添加到模板列表和模板列表框中
            global_var.templates_append(data)
            global_var.set_templates_hash(hash_value, data.get('name'))
            self.ui.comboBox.addItem(data.get('name'))
        FDDebug.debug("已载入模板文件: " + data.get('name'), type='success', who=self.__class__.__name__)

    @staticmethod
    def showDebug():
        # 显示调试输出
        FDDebug.display()

    @staticmethod
    def customTemplate():
        FDCustom.display()

    @staticmethod
    def openDir():
        # 打开模板文件目录
        FDDebug.debug("已打开模板目录", type='success', who='FDMenu')
        os.startfile(os.getcwd() + "\\FDTemplates")


def init():
    global fdMenu
    fdMenu = FDMenu()


def display():
    fdMenu.ui.show()
    FDDebug.debug("已打开功能菜单界面", type='success', who='FDMenu')


def set_debug_button_visible(is_visible):
    if is_visible:
        fdMenu.ui.buttonDebug.setVisible(True)
    else:
        fdMenu.ui.buttonDebug.setVisible(False)
    return


def syncTemplates():
    fdMenu.syncTemplates()
    return


def checkUpdate():
    fdMenu.checkUpdate()
    return
