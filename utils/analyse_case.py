#封装测试用例
import allure
import logging

import json

from config.config import BASE_URL

#封装返回json字典格式   
def parse_json_data(data_str):
    if isinstance(data_str,str) and data_str.strip():
        try:
            return json.loads(data_str)
        except json.JSONDecodeError as e:
            logging.error(f"json解析失败，请检查Excel格式，内容：{data_str},错误信息：{e}")
            return None
    return None

@allure.step("1.解析请求数据")
def analyse_case(case):
    method = case['method']
    url = BASE_URL + case['path']
    headers = parse_json_data(case['headers'])
    params = parse_json_data(case['params'])
    json = parse_json_data(case['json'])
    data = parse_json_data(case['data'])
    files = eval(case['files']) if isinstance(case['files'],str) and case['files'].strip() else None

    request_data = {
        'method': method,
        'url': url,
        'headers': headers,
        'params': params,
        'json': json,
        'data': data,
        'files': files,
    }
    logging.info(f"1.解析请求数据，{request_data}")
    return request_data

