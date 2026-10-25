import allure
import jsonpath
import logging

from utils.send_request import send_jdbc_request


def json_extractor(case, res, extractor_data):
    if case['jsonExData']:
        with allure.step("4.JSON提取"):
            for key, value in eval(case['jsonExData']).items():  # .items是字典的一个遍历，依次遍历key和value
                value = jsonpath.jsonpath(res.json(), value)[0]
                extractor_data[key] = value
            logging.info(f"4.JSON提取 根据({case['jsonExData']})提取数据，提取后全局变量为:{extractor_data}")

def jdbc_extractor(case,extractor_data):
    if case['sqlExData']:
        with allure.step("4.jdbc提取"):
            for key, value in eval(case['sqlExData']).items():
                value = send_jdbc_request(value)
                extractor_data[key] = value
            logging.info(f"4.jdbc提取 根据({case['sqlExData']})提取数据，提取后全局变量为:{extractor_data}")