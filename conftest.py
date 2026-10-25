import pymysql
import pytest

from config.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from utils import extractor


@pytest.fixture(scope="session",autouse=True)
def destroy_data():
    #资源销毁，双重保险
    sqls = ["delete from sys_user where user_name = 'fanzy'",
            "delete from sys_user where user_name = 'fuck'",
            "delete from sys_user where user_name = 'komorebi'",
            "delete from sys_user where user_name = 'user01'",
            "delete from sys_user where user_name = 'user02'",
            "delete from sys_user where user_name = 'user03'"
            ]
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME, autocommit=True,
                           charset='utf8')
    cur = conn.cursor()
    for sql in sqls:
        cur.execute(sql)
    cur.close()
    conn.close()

    yield

    #资源销毁
    sqls = ["delete from sys_user where user_name = 'fanzy'",
            "delete from sys_user where user_name = 'fuck'",
            "delete from sys_user where user_name = 'komorebi'",
            "delete from sys_user where user_name = 'user01'",
            "delete from sys_user where user_name = 'user02'",
            "delete from sys_user where user_name = 'user03'"
            ]
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME, autocommit=True,
                           charset='utf8')
    cur = conn.cursor()
    for sql in sqls:
        cur.execute(sql)
    cur.close()
    conn.close()