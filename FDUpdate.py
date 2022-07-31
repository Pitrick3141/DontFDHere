import os
import json
import requests
import webbrowser
from PySide2.QtWidgets import QMessageBox, QPushButton, QDialogButtonBox
from PySide2.QtUiTools import QUiLoader
from config import current_version
from FDMain import fdMain


class FDUpdate:

    def __init__(self):

        # 加载更新弹窗UI
        self.ui = QUiLoader().load('ui\\FormUpdate.ui')

        # 设置窗口图标
        self.ui.setWindowIcon(fdMain.app_icon)

        # 最新版本信息
        self.json_data = {}

        # 弹窗按钮
        button_web = QPushButton('打开发布页面')
        button_download = QPushButton('下载更新')
        button_cancel = QPushButton('取消')
        button_ignore = QPushButton('此版本不再提醒')

        # 将按钮添加到弹窗
        self.ui.buttonBox.addButton(button_download, QDialogButtonBox.AcceptRole)
        self.ui.buttonBox.addButton(button_web, QDialogButtonBox.AcceptRole)
        self.ui.buttonBox.addButton(button_cancel, QDialogButtonBox.RejectRole)
        self.ui.buttonBox.addButton(button_ignore, QDialogButtonBox.RejectRole)

        # 绑定按钮事件
        button_web.clicked.connect(self.openPublishPage)
        button_download.clicked.connect(self.downloadUpdate)
        button_ignore.clicked.connect(self.ignoreUpdate)

    def setData(self, data):
        # 设置最新版本数据并显示
        self.json_data = data

        update_info = "发现新版本，是否更新？" \
                      "\n-----更新信息-----" \
                      "\n当前版本: {}" \
                      "\n最新版本: {}" \
                      "\n发布时间: {}" \
                      "\n文件大小: {} bytes ({} MB)" \
                      "\n更新说明: {}".format(current_version,
                                          self.json_data['tag_name'],
                                          self.json_data['published_at'],
                                          self.json_data['assets'][0]['size'],
                                          self.json_data['assets'][0]['size'] / 1000000,
                                          self.json_data['body'])

        self.ui.textInfo.setText(update_info)

    def openPublishPage(self):

        # 打开最新版本发布页面
        fdMain.debug("已打开最新版本发布页面", type='success')
        webbrowser.open(self.json_data['html_url'])

    def downloadUpdate(self):

        # 下载最新版本更新文件

        # 检测是否已经存在更新文件
        if os.path.exists(self.json_data['assets'][0]['name']):
            fdMain.debug("发现已下载的更新文件{},跳过本次下载".format(self.json_data['assets'][0]['name']), type='warn')
            return

        # 下载更新文件
        fdMain.debug("开始下载更新文件{}".format(self.json_data['assets'][0]['browser_download_url']))
        try:
            update_file = requests.get(self.json_data['assets'][0]['browser_download_url'])
        except requests.exceptions.ConnectionError:
            fdMain.debug("网络连接异常，下载更新文件失败", type='error')
            return

        fdMain.debug("已下载更新文件".format(self.json_data['assets'][0]['name']), type='success')
        fdMain.debug("正在保存更新文件到{}\\{}".format(os.getcwd(),
                                              self.json_data['assets'][0]['name']))

        # 保存更新文件到运行目录
        with open(self.json_data['assets'][0]['name'], 'wb') as f:
            f.write(update_file.content)
            f.close()
        fdMain.debug("更新文件已保存至{}\\{}".format(os.getcwd(),
                                             self.json_data['assets'][0]['name']), type='success')
        QMessageBox.information(self.ui, "更新文件下载完成", "更新文件已保存至{}\\{}\n{}".format(os.getcwd(),
                                                                                 self.json_data['assets'][0]['name'],
                                                                                 "请手动解压并覆盖当前版本"))

    def ignoreUpdate(self):

        # 弹窗询问是否跳过当前版本更新
        msgbox = QMessageBox()
        msgbox.setWindowTitle("确认跳过版本")
        msgbox.setText("你确定要跳过当前版本更新吗？")
        msgbox.setInformativeText("你将不再收到当前版本的更新推送")
        msgbox.setIcon(QMessageBox.Question)
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.Yes)
        msgbox.setButtonText(QMessageBox.Yes, "确定")
        msgbox.setButtonText(QMessageBox.No, "再想想")
        ret = msgbox.exec_()
        if ret == QMessageBox.Yes:

            # 将当前已忽略的版本和新忽略的版本序列化
            ignored_version = [self.json_data['tag_name']]
            if 'ignored_version' in fdMain.configs.keys():
                for ver in fdMain.configs.get('ignored_version'):
                    ignored_version.append(ver)
            fdMain.debug("当前跳过的版本: {}".format(ignored_version))
            json_dump = {'config': True, 'version': current_version, 'ignored_version': [self.json_data['tag_name']]}

            # 保存配置文件
            with open("FDTemplates\\ignored_version.json", "w") as f:
                json.dump(json_dump, f)

            fdMain.debug("配置文件已保存至{}\\{}".format(os.getcwd(), "FDTemplates\\ignored_version.json"))
