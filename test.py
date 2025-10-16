from miio import AirConditioningCompanionMcn02

device = AirConditioningCompanionMcn02(ip="192.200.1.12", token="1724bf8d57b355173dfa08ae23367f86")
device.off()
# print(dev.info())
# print(dev.model)
# print(dev.raw_id)