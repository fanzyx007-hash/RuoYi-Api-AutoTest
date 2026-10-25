import logging
import pytest
from jinja2 import Template

from config.config import EXCEL_PATH
from utils.allure_init import allure_init
from utils.analyse_case import analyse_case
from utils.asserts import http_assert, jdbc_assert
from utils.excel_read import excel_read
from utils.extractor import json_extractor, jdbc_extractor
from utils.send_request import send_http_request


class TestRunner:
    data = excel_read(EXCEL_PATH)
    extractor_data = {}    #存取提取的变量值
    @pytest.mark.parametrize("case", data)
    def test_case(self,case,request):
        #动态判断是否标记为xfail
        if case.get('is_xfail'):
            request.node.add_marker(pytest.mark.xfail(reason = f"已知bug:{case['title']}"))

        #说明变量
        extractor_data = self.extractor_data

        #渲染case
        case = eval(Template(str(case)).render(extractor_data))

        #1.初始化allure报告
        allure_init(case)

        logging.info(f"用例id:{case['id']}--{case['title']}")

        #2.封装测试用例
        request_data = analyse_case(case)

        #3.封装请求 http 和 jdbc
        res = send_http_request(**request_data)

        #4.处理断言
        #HTTP断言
        http_assert(case,res)
        #jdbc断言
        jdbc_assert(case)

        #5.提取
        # json提取
        json_extractor(case,res,extractor_data)
        #jdbc提取
        jdbc_extractor(case,extractor_data)