import os
import sys
import time

import requests
from PySide2.QtWidgets import QMessageBox, QMainWindow


def rescueMode():
    # 缺少必要文件的恢复模式
    QMessageBox.critical(QMainWindow(), "致命错误",
                         "读取依赖文件失败，该文件可能不存在或已损坏，程序无法运行\n即将进入恢复模式")

    # 弹窗询问是否下载依赖文件
    if QMessageBox.question(QMainWindow(), "恢复模式", "检测到你缺少依赖文件，是否从云端下载？") == QMessageBox.Yes:

        # 获取依赖文件列表
        try:
            r = requests.get(url='https://api.github.com/repos/Pitrick3141/DontFDHere/contents/ui',
                             params={'ref': 'master'})
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(QMainWindow(), "恢复模式", "网络连接异常，依赖文件列表获取失败")
            sys.exit(1)

        # 创建依赖文件目录
        if not os.path.exists("ui"):
            os.mkdir("ui")

        # 依赖文件列表
        required_files = r.json()

        # 已下载文件列表
        downloaded_files = []

        # 生成恢复模式报告
        rescue_report = "恢复模式报告\n------\n"
        rescue_report += "开始恢复时间: {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        # 下载依赖文件
        for file in required_files:

            download_url = file['download_url']
            name = file['name']
            file_hash = file['sha']
            file_size = file['size']
            str_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

            # 若文件存在则跳过下载
            if os.path.exists("ui\\{}".format(name)):
                continue

            try:
                download = requests.get(url=download_url)
            except requests.exceptions.ConnectionError:
                QMessageBox.critical(QMainWindow(), "恢复模式", "网络连接异常，依赖文件下载失败")
                sys.exit(1)

            # 写入依赖文件
            with open("ui\\{}".format(name), "wb") as f:
                f.write(download.content)

            downloaded_files.append(
                "{} 已下载依赖文件: ui\\{}\n文件大小: {}Bytes ({}MB)\n文件哈希: {}\n".format(
                    str_time,
                    name,
                    file_size,
                    file_size / 1000000,
                    file_hash))

        # 弹窗显示恢复模式报告并写入恢复模式报告文件
        for file in downloaded_files:
            rescue_report += file
        rescue_report += "------\n提示：恢复模式会自动下载最新版本依赖文件，若依赖文件与当前版本冲突程序可能无法正常运行，" \
                         "请前往https://github.com/Pitrick3141/DontFDHere/releases/latest下载最新版本\n"
        QMessageBox.information(QMainWindow(), "恢复模式", rescue_report)
        with open("恢复报告_{}.txt".format(time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())), "w") as f:
            f.write(rescue_report)

        # 弹窗提示重启并退出程序
        QMessageBox.information(QMainWindow(), "恢复模式", "所有依赖文件下载完成")
        return

    else:
        sys.exit(1)
