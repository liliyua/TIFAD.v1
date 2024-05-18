

import time

from Utils.download import execute_downloadFile
from Utils.fileUtils import getFileNameWithoutExtensionFromPath

__finishFLag = -1


def executeDownload(url: str, rawImagesDirPath: str, retryTimes: int, fileBytesThreshold: int = 1024):
    """下载目标url至rawimagesDirPath文件夹下，通过文件大小阈值判定下载是否成功，失败则重试retryTimes次"""
    retry = 0
    rawImagePath = ""

    for retry in range(1, retryTimes):
        print("#等待服务端数据生成")
        time.sleep(3)
        rawImagePath, filesize = execute_downloadFile(
            url, rawImagesDirPath)

        if filesize < fileBytesThreshold:  # 1kb
            print("#下载失败，准备重试: "+str(retry))
        else:
            print("#下载完成")
            retry = __finishFLag
            break
    if retry != __finishFLag:
        raise Exception("文件下载失败，超过最大重试数")

    name = getFileNameWithoutExtensionFromPath(rawImagePath)
    return rawImagePath, name
