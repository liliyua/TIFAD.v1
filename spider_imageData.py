import requests
import time
import csv
from requests.adapters import HTTPAdapter
from Utils.fileUtils import ensureDir
from requests.packages.urllib3.util.retry import Retry
from tqdm import tqdm
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

session = requests.session()
retry = Retry(total=3, backoff_factor=1)
session.mount('http://', HTTPAdapter(max_retries=retry))
session.mount('https://', HTTPAdapter(max_retries=retry))


class downloadInfo:
    url: str
    fileName: str

    def __init__(self, url: str, fileName: str):
        self.url = url
        self.fileName = fileName


class spider_imageData:

    urlList: list[downloadInfo] = []
    starttime: str = ""
    writeToFilePath: str = ""

    def __init__(self, writeToFilePath: str):
        self.writeToFilePath = writeToFilePath
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        }
        self.urlList.clear()

    def get_list(self, starttime, endtime):
        url = 'http://124.16.184.48:6008/s/sjcp/queryDataList'
        json = {
            "producttype": "标准产品",
            "regioncode": "",
            "satelliteid": "KX10",
            "sensorid": "TIS",
            "productid": "",
            "productlevel": "L4B",
            "cloudpercent": 0.3,
            "fgeometry": "",
            "imagegsd_min": None,
            "imagegsd_max": None,
            "starttime": f"{starttime} 00:00:00",
            "endtime": f"{endtime} 23:59:59",
            "userName": "niuniumc",
            "gjcx": [],
            "pageindex": 1,
            "pagesize": 10,
            "isEnglish": 0
        }
        response = session.post(url, headers=self.headers, json=json)
        time.sleep(1)
        totalPage = response.json()['result']['totalPage']
        for p in range(1, totalPage+1):
            json.update({"pageindex": p})
            response = session.post(url, headers=self.headers, json=json)
            time.sleep(1)
            items = response.json()['result']['items']
            for i in items:
                self.primarykey = i['primarykey']
                self.name = i['id']
                self.saveSjqd()

    def saveSjqd(self):
        url = "http://124.16.184.48:6008/s/sjqd/saveSjqd"
        json = {
            "cpid": self.primarykey,
            "tjr": "niuniumc",
            "cplx": "标准产品",
            "isEnglish": 0
        }
        response = session.post(url, headers=self.headers, json=json)
        # time.sleep(1)
        if response.json()['result'] == '1条产品已提交到我的数据':
            self.get_file_id()

    def get_file_id(self):
        url = "http://124.16.184.48:6008/s/sjqd/quertSjqd"
        params = {
            "cpid": "",
            "cplx": "",
            "tjKssj": "",
            "tjJssj": "",
            "sjzt": "",
            "tjr": "niuniumc",
            "PageNum": "1",
            "PageSize": "100",
            "isEnglish": "0"
        }
        response = session.get(url, headers=self.headers, params=params)
        # time.sleep(1)
        items = response.json()['result']['items']
        for i in items:
            cpprimarykey = i['cpprimarykey']
            if cpprimarykey == self.primarykey:
                centertime = i['centertime']
                id = i['id']
                self.get_url(centertime, id)
                break

    def get_url(self, centertime, id):
        url = "http://124.16.184.48:6008/s/sjqd/downloadSjqdPT"
        json = {
            "yhmc": "niuniumc",
            "id": id,
            "userId": "53584",
            "downtag": "9fbabc652-f52b-4f13a26bcca291073d5b2fdc69ab8795758b58a7005538ff1f04532fbbd48510b",
            "isEnglish": 0
        }
        response = session.post(url, headers=self.headers, json=json)
        # time.sleep(1)
        download_url = response.json()['result']
        self.urlList.append(downloadInfo(download_url, self.name))

        # self.download(download_url, centertime)
        # 未保存

        current_time = datetime.now()
        formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
        if self.writeToFilePath != "":
            with open(self.writeToFilePath, 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([self.name, self.primarykey, id,
                                centertime, download_url, formatted_time])
        # print(f'{self.name}下载成功！')

    # def download(self, url, centertime):
    #     date = centertime[:10].replace('-', '')
    #     if not os.path.exists(f'./图片保存/{date[:6]}/{date}'):
    #         os.makedirs(f'./图片保存/{date[:6]}/{date}')
    #     print(f'开始下载：{self.name}')
    #     response = session.get(url, stream=True)
    #     local_filename = f'./图片保存/{date[:6]}/{date}/{self.name}.zip'
    #     total_size = int(response.headers.get('content-length', 0))
    #     with open(local_filename, 'wb') as file, tqdm(
    #             desc=local_filename,
    #             total=total_size,
    #             unit='B',
    #             unit_scale=True,
    #             unit_divisor=1024,
    #     ) as bar:
    #         for data in response.iter_content(chunk_size=1024):
    #             file.write(data)
    #             bar.update(len(data))

    def run(self, date: str):
        """函数栈太深，需要优化"""
        self.starttime = date
        endtime = self.starttime    # 结束时间

        if self.writeToFilePath != "":
            with open(self.writeToFilePath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['文件名称', '文件key', '文件id', '文件时间', '下载链接', '下载完成时间'])

        self.get_list(self.starttime, endtime)


def execute_spider_imageData(date: str, writeToFilePath: str = "") -> list[str]:
    """爬取目标日期的图像下载地址列表，data格式示例: '2024-01-01',writeToFilePath格式示例 'XXXX-XXXX.csv ' """
    print(f'#开始抓取日期 {date} 图像数据')

    ensureDir(os.path.dirname(writeToFilePath))

    tt = spider_imageData(writeToFilePath)
    print(date+"changdu "+str(len(tt.urlList)))
    tt.run(date)
    print(f'#爬取完成，共{len(tt.urlList)}条数据')
    return tt.urlList


if __name__ == '__main__':
    execute_spider_imageData('2024-01-03')
