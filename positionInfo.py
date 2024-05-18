

class positionInfo:
    classId: int
    lon: float
    lat: float
    fileName: str
    filePath: str
    aircraftLBand1: float
    SCRBand1: float

    def __init__(self, classId: int, lon: float, lat: float, fileName: str, filePath: str, aircraftLBand: float, scrBand: float):
        self.classId = classId
        self.lon = lon
        self.lat = lat
        self.fileName = fileName
        self.filePath = filePath
        self.aircraftLBand1 = aircraftLBand
        self.SCRBand1 = scrBand
