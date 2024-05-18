import argparse
import os
import cv2
import numpy as np
# import gdal
from osgeo import gdal

from Utils.fileUtils import ensureDir, getFileNameWithoutExtensionFromPath

#  读取原tif数据集


def readTif(fileName, xoff=0, yoff=0, data_width=0, data_height=0):
    dataset = gdal.Open(fileName)
    if dataset == None:
        print(fileName + "文件无法打开")
    #  栅格矩阵的列数
    width = dataset.RasterXSize
    #  栅格矩阵的行数
    height = dataset.RasterYSize
    #  波段数
    bands = dataset.RasterCount
    #  获取数据
    if (data_width == 0 and data_height == 0):
        data_width = width
        data_height = height
    data = dataset.ReadAsArray(xoff, yoff, data_width, data_height)
    #  获取仿射矩阵信息
    geotrans = dataset.GetGeoTransform()
    #  获取投影信息
    proj = dataset.GetProjection()
    return width, height, bands, data, geotrans, proj


#  保存tif文件函数
def writeTiff(im_data, im_geotrans, im_proj, path):
    if 'int8' in im_data.dtype.name:
        datatype = gdal.GDT_Byte
    elif 'int16' in im_data.dtype.name:
        datatype = gdal.GDT_UInt16
    else:
        datatype = gdal.GDT_Float32
    if len(im_data.shape) == 3:
        im_bands, im_height, im_width = im_data.shape
    elif len(im_data.shape) == 2:
        im_data = np.array([im_data])
        im_bands, im_height, im_width = im_data.shape

    # 创建文件
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(path, int(im_width), int(
        im_height), int(im_bands), datatype)
    if (dataset != None):
        dataset.SetGeoTransform(im_geotrans)  # 写入仿射变换参数
        dataset.SetProjection(im_proj)  # 写入投影
    for i in range(im_bands):
        dataset.GetRasterBand(i + 1).WriteArray(im_data[i])
    del dataset


def truncated_linear_stretch(image, max_out=255, min_out=0):
    def gray_process(gray):
        # Calculate the average of non-zero pixels
        non_zero_pixels = gray[gray > 0]
        if non_zero_pixels.size > 0:
            average_non_zero = np.mean(non_zero_pixels)
        else:
            average_non_zero = 0

        # Set zero pixels to the average of non-zero pixels
        gray[gray == 0] = average_non_zero

        truncated_down = np.percentile(gray, 0)
        truncated_up = np.percentile(gray, 95)
        gray = (gray - truncated_down) / (truncated_up -
                                          truncated_down) * (max_out - min_out) + min_out
        gray[gray < min_out] = min_out
        gray[gray > max_out] = max_out

        if max_out <= 255:
            gray = np.uint8(gray)
        elif max_out <= 65535:
            gray = np.uint16(gray)

        return gray

    if len(image.shape) == 3:  # If multi-band
        image_stretch = []
        for i in range(image.shape[0]):
            gray = gray_process(image[i])
            image_stretch.append(gray)
        image_stretch = np.array(image_stretch)
    else:  # If single-band
        image_stretch = gray_process(image)

    return image_stretch


# 百分比线性截断
def truncated_linear_stretch1(image, max_out=255, min_out=0):
    def gray_process(gray):
        truncated_down = np.percentile(gray, 0)
        truncated_up = np.percentile(gray, 95)
        # percentile_1 = np.percentile(data, 0)
        # percentile_99 = np.percentile(data, 95)
        gray = (gray - truncated_down) / (truncated_up -
                                          truncated_down) * (max_out - min_out) + min_out
        gray[gray < min_out] = min_out
        gray[gray > max_out] = max_out
        if (max_out <= 255):
            gray = np.uint8(gray)
        elif (max_out <= 65535):
            gray = np.uint16(gray)
        return gray

    #  如果是多波段
    if (len(image.shape) == 3):
        image_stretch = []
        for i in range(image.shape[0]):
            gray = gray_process(image[i])
            image_stretch.append(gray)
        image_stretch = np.array(image_stretch)
    #  如果是单波段
    else:
        image_stretch = gray_process(image)
    return image_stretch


const_suffix = "_8bit"


def execute_linear_stretch(inputDir: str, outputDir: str) -> str:
    """将inputDir目录下的16位tif图片转换为8位tif图片并存储至outputDir下,返回转8位后的目录"""
    print("#图转8位: "+inputDir)

    # 当前步骤中若切片文件数量为空，则视为异常
    if (len(os.listdir(inputDir)) == 0):
        raise Exception(f"切片为空无需执行{inputDir}")

    outputSubForlder = ensureDir(outputDir + "/" +
                                 os.path.basename(inputDir))

    # 修改路径：16bit图片文件夹
    file_pathname = inputDir

    for root, dirs, files in os.walk(file_pathname):
        #print('root', root)
        #print('dirs', dirs)
        #print('files', files)
        for filename in os.listdir(root):
            # for filename in os.listdir(file_pathname):
            if filename.endswith('tiff'):    # 修改路径：需要被剪裁的图片文件夹
                # if filename.endswith('tif'):
                # if filename.endswith('jpg'):

                #print('filename:', filename)
                image_path = inputDir + '/' + filename
                #print('image_path', image_path)

                # image_path = file_pathname + '/' + filename

                width, height, bands, data, geotrans, proj = readTif(
                    image_path)
                # print('data.shape:', data.shape)

                data_stretch = truncated_linear_stretch(data)
                # SaveName = file_pathname.replace('飞机数据集_剪裁16bit_每日更新', '飞机数据集_剪裁8bit_每日更新') + '/' + filename  # 修改路径：8bit文件夹
                SaveName = outputSubForlder + '/' + filename.replace(
                    '_L4B_crop', '_L4B_crop_8bit')  # 修改路径：8bit文件夹
                #print('SaveName', SaveName)

                # 输出目录不存在则创建
                ensureDir(root.replace('_L4B_crop', '_L4B_crop_8bit'))

                writeTiff(data_stretch, geotrans, proj, SaveName)

    print("#图转完成: "+outputSubForlder)
    return outputSubForlder


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputDir', type=str, default=None)
    parser.add_argument('--outputDir', type=str, default=None)
    args = parser.parse_args()
    inputDir = args.inputDir
    outputDir = args.outputDir
    execute_linear_stretch(inputDir, outputDir)
