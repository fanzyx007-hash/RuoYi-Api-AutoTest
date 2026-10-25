import allure
import logging
import pymysql
import requests

from config.config import DB_HOST, DB_USER, DB_NAME, DB_PASSWORD

@allure.step("2.发送HTTP请求")
def send_http_request(**request_data):
    #附加请求数据到allure报告
    allure.attach(str(request_data),"请求参数",allure.attachment_type.TEXT)

    res = requests.request(**request_data)

    #附加响应内容到allure报告
    allure.attach(res.text, "响应内容", allure.attachment_type.JSON)

    logging.info(f"2.发送HTTP请求,{res.text}")
    return res

def send_jdbc_request(sql,index = 0):
    with allure.step("发送jdbc请求"):
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME, autocommit=True,
                               charset='utf8')
        cur = conn.cursor()
        cur.execute(sql)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[index]