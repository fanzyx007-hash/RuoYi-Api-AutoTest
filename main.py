import os

import pytest
#"./testcases/test_runner.py"是指定一个目录生成中间结果
if __name__ == '__main__':
    pytest.main(["-vs","./testcases/test_runner.py","--alluredir=./report/json_report","--clean-alluredir"])
    os.system("allure generate ./report/json_report -o ./report/html_report --clean")#"./testcases/test_runner.py"中间结果 "-o"生成 ./report/html_report --clean最终结果