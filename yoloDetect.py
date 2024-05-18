

import subprocess


yoloCmdTemplate: str = "yolo detect predict model=#modelPath source=#dataDir save_txt=True save_crop=True save=True project=#project name=#name"


def execute_yoloDetect(dataDir: str, project: str, name: str, yoloModelPath: str) -> str:

    yoloCmd = yoloCmdTemplate.replace(
        '#modelPath', yoloModelPath).replace('#dataDir', dataDir).replace('#project', project).replace('#name', name)

    print("#开始yolo检测: "+yoloCmd)
    proc = subprocess.Popen(
        yoloCmd,  # cmd特定的查询空间的命令
        stdin=None,  # 标准输入 键盘
        stdout=subprocess.PIPE,  # -1 标准输出（演示器、终端) 保存到管道中以便进行操作
        stderr=subprocess.PIPE,  # 标准错误，保存到管道
        shell=True)
    outinfo, errinfo = proc.communicate()  # 获取输出和错误信息
    # print(outinfo.decode('gbk'))  # 外部程序 (windows系统)决定编码格式
    error = str(errinfo.decode('gbk'))
    output = f'{project}/{name}'
    if error != "":
        print("#"+error)
    else:
        print("#yolo完成: "+output)
    return output
