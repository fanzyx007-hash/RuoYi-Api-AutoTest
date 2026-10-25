# RuoYi API Automation Test Framework

这是一个基于 Python + Pytest + Requests + Allure 搭建的接口自动化测试框架。

## 🛠️ 技术栈
- Python 3.14
- Pytest (测试框架)
- Requests (HTTP 请求库)
- PyMySQL (数据库断言)
- Allure (测试报告)

## ✨ 核心功能
- **数据驱动**：基于 Excel 管理测试用例。
- **多角色鉴权**：支持 Admin 和普通用户的 Token 自动提取与越权测试。
- **数据库校验**：不仅断言 HTTP 响应，还通过 JDBC 断言数据库状态（如逻辑删除标记）。
- **动态 xfail**：支持已知缺陷的预期失败标记。
- **环境清理**：Fixture 实现测试前后环境数据的自动清理。

## 🚀 运行方式
1. 安装依赖：`requests
pymysql
jsonpath
pytest
openpyxl
allure-pytest
jinja2`
2. 修改配置文件：`config/config.py` 中的数据库与接口地址。
3. 运行若依项目后端
4. 执行测试：`python main.py`
5. 查看报告：打开 `report/html_report/index.html`
