

from Automation.Config import pipelineConfig
from Automation.Pipeline import pipeline
from Actions.spider_imageData import downloadInfo, execute_spider_imageData


class PipeLineManager:
    config: pipelineConfig

    def __init__(self, config: pipelineConfig):
        self.config = config

    def Execute(self, date: str):

        pipelines: list[pipeline] = []
        fileList = execute_spider_imageData(
            date, f'{self.config.downloadImagePath}/{date}.csv')
        for file in fileList:
            pipelines.append(pipeline(self.config, date, file))

        tot = len(pipelines)
        cur = 0

        for pip in pipelines:
            cur += 1

            print(f'#----------Run [{cur}/{tot}]----------')
            if pip.Execute():
                print(f'#----------Finish [{cur}/{tot}]-----------')
            else:
                print(f'#----------Error [{cur}/{tot}]-----------')

        print(f"#----------All {cur}/{tot} cycles done----------")
