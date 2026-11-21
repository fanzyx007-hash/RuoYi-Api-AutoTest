#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
登录 + 用户列表 并发压测基线脚本（零额外依赖，只要 requests）

用途：在没有装好 JMeter 之前，先拿到一版真实的并发数据，用来定基线和验证场景。
注意：简历上写 JMeter，所以最终仍要用 JMeter 复测一次（见 01-JMeter压测执行手册.md）。

用法：
    python load_baseline.py --threads 10 --loops 20
    python load_baseline.py --threads 30 --loops 20 --csv out30.csv

前提：
    1) 若依后端已启动（默认 http://127.0.0.1:8080）
    2) 已关闭验证码：UPDATE sys_config SET config_value='false' WHERE config_key='sys.account.captchaEnabled';
"""
import argparse
import csv
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

_lock = threading.Lock()
records = []          # [(接口名, 耗时ms, 是否成功, 状态码/错误)]
start_gate = threading.Event()


def one_iteration(session, base_url, username, password, timeout):
    # ---- 1. 登录 ----
    t0 = time.perf_counter()
    ok, detail = False, ""
    token = None
    try:
        r = session.post(f"{base_url}/login",
                         json={"username": username, "password": password},
                         timeout=timeout)
        detail = str(r.status_code)
        body = r.json()
        token = body.get("token")
        ok = r.status_code == 200 and body.get("code") == 200 and bool(token)
        if not ok:
            detail = f"{r.status_code} {body.get('msg')}"
    except Exception as e:                                  # noqa: BLE001
        detail = f"{type(e).__name__}: {e}"
    dt = (time.perf_counter() - t0) * 1000
    with _lock:
        records.append(("POST /login", dt, ok, detail))

    # ---- 2. 带 token 查列表 ----
    if not ok:
        return
    t0 = time.perf_counter()
    ok2, detail2 = False, ""
    try:
        r = session.get(f"{base_url}/system/user/list",
                        params={"pageNum": 1, "pageSize": 10},
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=timeout)
        detail2 = str(r.status_code)
        ok2 = r.status_code == 200 and r.json().get("code") == 200
    except Exception as e:                                  # noqa: BLE001
        detail2 = f"{type(e).__name__}: {e}"
    dt = (time.perf_counter() - t0) * 1000
    with _lock:
        records.append(("GET /system/user/list", dt, ok2, detail2))


def worker(base_url, username, password, loops, timeout):
    session = requests.Session()          # 复用连接，否则压的是 TCP 三次握手
    start_gate.wait()                     # 所有线程就位后同时起跑
    for _ in range(loops):
        one_iteration(session, base_url, username, password, timeout)
    session.close()


def pct(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((p / 100.0) * len(values) + 0.5)) - 1))
    return values[k]


def report(name, rows, elapsed):
    times = [r[1] for r in rows]
    fails = [r for r in rows if not r[2]]
    print(f"\n=== {name} ===")
    print(f"  样本数            : {len(rows)}")
    print(f"  错误数 / 错误率   : {len(fails)} / {len(fails) / len(rows) * 100:.2f}%")
    if times:
        print(f"  平均 RT           : {statistics.mean(times):.1f} ms")
        print(f"  P90 / P95 / P99   : {pct(times, 90):.1f} / "
              f"{pct(times, 95):.1f} / {pct(times, 99):.1f} ms")
        print(f"  Min / Max         : {min(times):.1f} / {max(times):.1f} ms")
    print(f"  TPS（该接口）     : {len(rows) / elapsed:.2f}")
    if fails:
        from collections import Counter
        for detail, cnt in Counter(f[3] for f in fails).most_common(3):
            print(f"  失败原因 x{cnt}      : {detail}")


def main():
    ap = argparse.ArgumentParser(description="若依登录+列表 并发压测基线")
    ap.add_argument("--base-url", default="http://127.0.0.1:8080")
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", default="admin123")
    ap.add_argument("--threads", type=int, default=10)
    ap.add_argument("--loops", type=int, default=20, help="每个线程的循环次数")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    print(f"目标 {args.base_url} | 并发 {args.threads} | 每线程循环 {args.loops} "
          f"| 预计请求数 {args.threads * args.loops * 2}")

    # 先做一次连通性检查，避免 50 个线程同时报 Connection refused
    try:
        requests.get(f"{args.base_url}/captchaImage", timeout=5)
    except Exception as e:                                  # noqa: BLE001
        print(f"[!] 后端连不上：{e}\n    先启动 ruoyi-admin（8080）再跑本脚本。")
        sys.exit(1)

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = [pool.submit(worker, args.base_url, args.username, args.password,
                               args.loops, args.timeout)
                   for _ in range(args.threads)]
        time.sleep(0.3)
        t_start = time.perf_counter()
        start_gate.set()
        for f in futures:
            f.result()
        elapsed = time.perf_counter() - t_start

    login_rows = [r for r in records if r[0].startswith("POST")]
    list_rows = [r for r in records if r[0].startswith("GET")]

    report("POST /login", login_rows, elapsed)
    report("GET /system/user/list", list_rows, elapsed)
    total = len(login_rows) + len(list_rows)
    fail = sum(1 for r in records if not r[2])
    print(f"\n=== 整轮汇总 ===")
    print(f"  总请求 {total} | 错误 {fail} | 用时 {elapsed:.2f}s | 总 TPS {total / elapsed:.2f}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["接口", "耗时ms", "是否成功", "状态码/错误"])
            w.writerows([(r[0], f"{r[1]:.1f}", r[2], r[3]) for r in records])
        print(f"\n明细已写入 {args.csv}")


if __name__ == "__main__":
    main()
