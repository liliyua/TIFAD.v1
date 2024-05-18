
import os
import pandas as pd
from Utils.fileUtils import ensureDir, getFileNameWithoutExtensionFromPath
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point
from pyproj import Proj, transform
import numpy as np


class segmentPlanePair:
    segmentName: str
    planeRowIndex: int

    def __init__(self, segmentName: str, planeRowIndex: int):
        self.segmentName = segmentName
        self.planeRowIndex = planeRowIndex


def tif_segment_crop_240217(image_path: str, outdir: str, plane_table_dir: str, map: dict):
    """若成功返回True，若文件路径异常返回False"""

    # 分离文件名，用于构建表格路径
    name = getFileNameWithoutExtensionFromPath(image_path)

    excel_file_path = os.path.join(
        plane_table_dir, f'{name}.csv')

    # 判定CSV文件是否存在
    if not os.path.exists(excel_file_path):
        raise Exception(f"#飞机表不存在: {excel_file_path}")

    # 无飞机的CSV大小为347字节，取350字节作为阈值进行判定，若planeTable不存在飞机，直接返回空路径
    if os.stat(excel_file_path).st_size < 350:
        print(os.stat(excel_file_path).st_size)
        return False

    # 读取CSV文件
    df = pd.read_csv(excel_file_path)

    # 筛选大于4000米的行
    df_filtered = df[df['CALIBRATED ALTITUDE(m)'] > 4000]

    # 重新写入筛选后的CSV
    try:
        df_filtered.to_csv(excel_file_path, index=False)
    except:
        raise Exception(f"csv写入失败，请检查文件是否打开或是否有权限 {excel_file_path}")

    from rasterio.warp import transform

    # 使用rasterio打开图像
    with rasterio.open(image_path) as src:
        # 获取图像的crs和transform属性
        crs = src.crs
        affine_transform = src.transform

        # 遍历筛选后的DataFrame
        for index, csvRow in df_filtered.iterrows():
            lat, lon = csvRow['LATITUDE'], csvRow['LONGITUDE']

            # 将地理坐标转换为图像中的行列坐标
            x, y = transform('epsg:4326', crs, [lon], [lat])
            row, col = ~affine_transform * (x[0], y[0])

            # 计算剪裁的窗口，注意这里的行列坐标需要根据实际情况进行调整
            window = rasterio.windows.Window(
                col - 350, row - 350, 700, 700)

            # 读取窗口内的数据
            clip = src.read(window=window)

            # 保存剪裁后的图像
            clip_path = os.path.join(
                outdir, f'{name}_head_{index}.tiff')

            # 传入至map中
            map[f'{name}_head_{index}'] = segmentPlanePair(
                f'{name}_head_{index}', index)

            with rasterio.open(
                    clip_path,
                    'w',
                    driver='GTiff',
                    height=clip.shape[1],
                    width=clip.shape[2],
                    count=src.count,
                    dtype=clip.dtype,
                    crs=src.crs,
                    transform=rasterio.windows.transform(
                        window, affine_transform)
            ) as clip_dst:
                clip_dst.write(clip)
    return True


def execute_tif_segment_crop(inputDir: str, outputDir: str, plane_table_dir: str) -> str:
    """将inputDir目录下的tif图切片并存储至outputDir目录下,返回切片文件目录，当飞机表中无飞机时，返回空字符串"""

    print("#切片数据: "+inputDir)

    outputSubForlder = ensureDir(outputDir + "/" +
                                 os.path.basename(inputDir))

    map: dict = {}

    for filename in os.listdir(inputDir):
        if filename.endswith('tiff'):
            image_path = inputDir + '/' + filename
            if not tif_segment_crop_240217(
                    image_path, outputSubForlder, plane_table_dir, map):
                return "", map  # 对应#planeTable中无飞机
    print("#切片完成: "+outputSubForlder)
    return outputSubForlder, map
