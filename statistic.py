import pandas as pd
import csv
import math
import os
from Actions.positionInfo import positionInfo
from shutil import copyfile

from Utils.fileUtils import ensureDir, getFileNameWithoutExtensionFromPath

LATITUDE = 'LATITUDE'
LONGITUDE = 'LONGITUDE'
EPSILON = 0.4
EPSILON_AIRCRAFTLBAND1 = 2.5
EPSILON_SCRBAND1 = 0


class validPosition:
    position: positionInfo  # 当前
    lon: float  # 目标
    lat: float  # 目标
    diff: float  # 误差

    def __init__(self, pos: positionInfo, lon: float, lat: float, diff: float) -> None:
        self.position = pos
        self.lon = lon
        self.lat = lat
        self.diff = diff


def isValid(pos: positionInfo, tlon: float, tlat: float, epsilon: float) -> bool:

    result = True

    # AIRCRAFT L Band 1 判定
    if (pos.aircraftLBand1 <= EPSILON_AIRCRAFTLBAND1):
        result = False

    # SCR Band 1 判定
    if (pos.SCRBand1 <= EPSILON_SCRBAND1):
        result = False

    # 执行坐标比较的逻辑
    # 此处未投影，仅对经纬度简单判定
    lon = pos.lon
    lat = pos.lat
    diff = math.sqrt(math.pow(lon-tlon, 2) + math.pow(lat-tlat, 2))
    result = result and diff < epsilon
    return result, diff


def execute_comparision(segmentMap: dict, dataname: str, planeTablePath: str, data: list[positionInfo], sourcePath: str, outPath: str, date: str):
    """要求planTablePath中存在与dataname相同命名的.csv文件"""

    print("#匹配数据: "+dataname+", lon-lat err<"+str(EPSILON) +
          f", aircraft L band1>{EPSILON_AIRCRAFTLBAND1}, scr band1>{EPSILON_SCRBAND1}")

    targetFile = os.path.join(planeTablePath, dataname+".csv")
    if not os.path.exists(targetFile):
        print(f'飞机清单不存在: {targetFile}')
        return

    # 增加列
    csvfile = pd.read_csv(targetFile, encoding='utf-8')
    totalLine = len(csvfile)
    checkList = x = ['' for i in range(totalLine)]
    csvfile["result"] = checkList
    csvfile.to_csv(targetFile, index=False)

    # 与目标经纬度进行匹配
    latIndex = 0
    lonIndex = 0
    validPositions = []

    outFolder_crop = ensureDir(os.path.join(outPath, "validCrops", date))
    outFolder_label = ensureDir(os.path.join(outPath, "validLabels", date))
    outFolder_planeTable = ensureDir(os.path.join(
        outPath, "validPlaneTable", date))

    anyValid = False

    for pos in data:

        key = getFileNameWithoutExtensionFromPath(pos.filePath)
        rowIndex = segmentMap[key].planeRowIndex

        # 读取csv
        csvReader = csv.reader(open(targetFile, encoding='utf-8'))
        for index, row, in enumerate(csvReader):  # 此处存在重复读取，后期优化
            if (index == 0):
                # 初始化列索引
                latIndex = row.index(LATITUDE)
                lonIndex = row.index(LONGITUDE)
            elif (index-1 == rowIndex):  # index对齐，

                lat = float(row[latIndex])
                lon = float(row[lonIndex])
                valid = False

                valid, diff = isValid(
                    pos, lon, lat, EPSILON)

                if valid:
                    validPositions.append(
                        validPosition(pos, lat, lon, diff))
                    try:
                        # crop tiff 复制
                        filename_tiff = pos.fileName.replace(
                            ".txt", ".tiff")
                        sourceFile_tiff = os.path.join(
                            sourcePath, filename_tiff)
                        outFile_tiff = os.path.join(
                            ensureDir(outFolder_crop), filename_tiff)
                        copyfile(sourceFile_tiff, outFile_tiff)

                        # label txt 复制
                        copyfile(pos.filePath, os.path.join(
                            outFolder_label, pos.fileName))
                        checkList[index -
                                  1] = checkList[index -
                                                 1] + f'lon={pos.lon} lat={pos.lat} ALB1={pos.aircraftLBand1} SB1={pos.SCRBand1} name={pos.fileName.replace(".txt", "")};'
                        anyValid = True
                    except:
                        pass

    # 更新行
    csvfile = pd.read_csv(targetFile, encoding='utf-8')
    csvfile["result"] = checkList
    csvfile.to_csv(targetFile, index=False)

    # 刷新读取
    csvReader = csv.reader(open(targetFile, encoding='utf-8'))

    # 新建planeTable
    validRowCount = 0
    if (anyValid):
        with open(outFolder_planeTable+'/'+dataname+".csv", 'w+') as f:
            for index, row in enumerate(csvReader):
                if (index == 0 or (str(row[24]) != '')):
                    f.write(','.join(row)+'\n')
                    validRowCount += 1

    print(
        f'#匹配结果: {len(validPositions)}/{len(data)} for labels, {validRowCount}/{totalLine} for planes')
    return validPositions
