
import os
import numpy as np
import pandas as pd
from osgeo import gdal
import os
import numpy as np
import pandas as pd
from osgeo import gdal, osr
from pyproj import Proj, Transformer
from Utils.fileUtils import ensureDir
from Actions.positionInfo import positionInfo


def parse_yolov5_label(txt_file, img_width, img_height):
    with open(txt_file, 'r') as f:
        lines = f.readlines()

    labels = []
    for line in lines:
        data = line.strip().split()
        class_id = int(data[0])
        x_center, y_center, width, height = map(float, data[1:])
        x_center_px = int(x_center * img_width)
        y_center_px = int(y_center * img_height)
        width_px = int(width * img_width)
        height_px = int(height * img_height)
        labels.append(
            (class_id, x_center_px, y_center_px, width_px, height_px))
    return labels


def dn_to_l(dn, gain, offset):
    return dn * gain + offset


def l_to_t(l, a, b):
    return a / np.log(b / l + 1)


def calculate_scr(min_dn, mean_dn, std_dn):
    return (mean_dn - min_dn) / std_dn if std_dn != 0 else 0


def get_dn_stats(img_path, x_center, y_center, width, height):
    dataset = gdal.Open(img_path)
    stats = []

    band_params = [
        (0.003947, 0.167126, 11542.76092164482,
         1655.62780201885),  # Band 1 parameters
        (0.003946, 0.124622, 1342.71869660818,
         838.706318829),      # Band 2 parameters
        (0.005329, 0.22253, 1232.02143586683,
         543.05795222985)      # Band 3 parameters
    ]

    x_start = max(x_center - width // 2 - 1, 0)
    y_start = max(y_center - height // 2 - 1, 0)
    x_end = min(x_center + width // 2 + 1, dataset.RasterXSize)
    y_end = min(y_center + height // 2 + 1, dataset.RasterYSize)

    for band_num, params in enumerate(band_params, start=1):
        gain, offset, a, b = params
        band = dataset.GetRasterBand(band_num)
        pixel_values = band.ReadAsArray(
            x_start, y_start, x_end - x_start, y_end - y_start)
        min_dn = np.min(pixel_values)
        mean_dn = np.mean(pixel_values)
        std_dn = np.std(pixel_values)

        min_l = dn_to_l(min_dn, gain, offset)
        mean_l = dn_to_l(mean_dn, gain, offset)

        min_t = l_to_t(min_l, a, b)
        mean_t = l_to_t(mean_l, a, b)

        scr = calculate_scr(min_dn, mean_dn, std_dn)

        stats.append((min_dn, mean_dn, std_dn, min_l,
                     mean_l, min_t, mean_t, scr))

    return stats


def get_lat_lon(dataset, x_pixel, y_pixel):
    gt = dataset.GetGeoTransform()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(dataset.GetProjectionRef())
    utm_proj = Proj(srs.ExportToProj4())
    transformer = Transformer.from_proj(
        utm_proj, Proj(proj='latlong', datum='WGS84'))

    x_geo = gt[0] + x_pixel * gt[1] + y_pixel * gt[2]
    y_geo = gt[3] + x_pixel * gt[4] + y_pixel * gt[5]

    lon, lat = transformer.transform(x_geo, y_geo)
    return lat, lon


def process_folder(labels_folder, images_folder):
    data = []

    for filename in os.listdir(labels_folder):
        if filename.endswith(".txt"):
            label_file = os.path.join(labels_folder, filename)
            image_file = os.path.join(
                images_folder, filename.replace(".txt", ".tif"))

            if os.path.exists(image_file):
                dataset = gdal.Open(image_file)
                img_width, img_height = dataset.RasterXSize, dataset.RasterYSize

                yolov5_labels = parse_yolov5_label(
                    label_file, img_width, img_height)

                for label in yolov5_labels:
                    class_id, x_center, y_center, width, height = label
                    dn_stats = get_dn_stats(
                        image_file, x_center, y_center, width, height)
                    lat, lon = get_lat_lon(dataset, x_center, y_center)
                    data_row = [filename, class_id, lon, lat]
                    for stats in dn_stats:
                        data_row.extend(stats)
                    data.append(data_row)
            else:
                print(f"Image file not found for {label_file}")

    columns = ['Filename', 'Class ID', 'Longitude', 'Latitude'] + [f'{metric} Band {i}' for i in range(
        1, 4) for metric in ['Aircraft DN', 'Back DN', 'Std Back', 'Aircraft L', 'Back L', 'Aircraft T', 'Back T', 'SCR']]
    df = pd.DataFrame(data, columns=columns)
    output_path = os.path.join(os.path.dirname(labels_folder), 'output.xlsx')
    df.to_excel(output_path, index=False)


def execute_tifLP(labels_folder: str, images_folder: str, outputDir: str, outputFilename: str):
    """提取yolo结果中的坐标，返回坐标存储数据文件路径及数据对象"""
    data = []  # 用于存储结果的列表
    positionInfoList = []
    print("#提取坐标: "+labels_folder)
    for filename in os.listdir(labels_folder):
        if filename.endswith(".txt"):
            label_file = os.path.join(labels_folder, filename)
            image_file = os.path.join(
                images_folder, filename.replace(".txt", ".tiff"))  # 改.tiff

            if os.path.exists(image_file):
                dataset = gdal.Open(image_file)
                img_width, img_height = dataset.RasterXSize, dataset.RasterYSize

                yolov5_labels = parse_yolov5_label(
                    label_file, img_width, img_height)

                for label in yolov5_labels:
                    class_id, x_center, y_center, width, height = label
                    dn_stats = get_dn_stats(
                        image_file, x_center, y_center, width, height)
                    lat, lon = get_lat_lon(dataset, x_center, y_center)

                    # 行信息生成
                    data_row = [filename, class_id, lon, lat]
                    for stats in dn_stats:
                        data_row.extend(stats)
                    data.append(data_row)

                    AircraftLBand1 = data_row[7]
                    SCRBand1 = data_row[11]
                    # 附加信息存储
                    positionInfoList.append(positionInfo(
                        classId=class_id, lon=float(lon), lat=float(lat), fileName=filename, filePath=label_file, aircraftLBand=AircraftLBand1, scrBand=SCRBand1))
            else:
                print(f"Image file not found for {image_file}")

    # 创建 DataFrame 并保存到 Excel
    df = pd.DataFrame(
        data, columns=['Filename', 'Class ID', 'Longitude', 'Latitude'] + [f'{metric} Band {i}' for i in range(
            1, 4) for metric in ['Aircraft DN', 'Back DN', 'Std Back', 'Aircraft L', 'Back L', 'Aircraft T', 'Back T', 'SCR']])

    output_path = os.path.join(ensureDir(outputDir),
                               f'{outputFilename}.csv')
    df.to_csv(output_path, index=False)  # 改csv
    print("#提取完成: " + output_path)
    return output_path, positionInfoList
