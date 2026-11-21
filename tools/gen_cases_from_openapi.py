#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 OpenAPI（springdoc / swagger）契约自动生成接口用例骨架，写入若依自动化项目的 Excel。

生成策略（每个接口）：
    1) 正向     —— 全部必填参数填合法样例值
    2) 必填缺失 —— 逐个删除必填参数（参数校验缺失 / 500）
    3) 类型错误 —— 整型传 "abc"、布尔传 "yes"
    4) 枚举越界 —— 枚举字段传非法值
    5) 鉴权缺失 —— 声明了 security 的接口不带 token

产物：xlsx 中新建一个 sheet（默认 Sheet_auto），列结构与现有用例一致（第 2 行为英文键），
      「是否执行」一律填 False —— 必须人工补断言后再打开，否则执行的是空断言。
"""
import argparse
import copy
import json
import sys

import openpyxl

HEADERS_CN = ['编号', '模块', '场景', '标题', '请求方式', '路径', '请求头', 'url参数', 'data参数',
              'json参数', '文件参数', '校验字段', '预期结果', '数据库校验内容', '数据库预期结果',
              'json提取', 'sql提取', '是否执行', '预期失败']
KEYS = ['id', 'feature', 'story', 'title', 'method', 'path', 'headers', 'params', 'data', 'json',
        'files', 'check', 'expected', 'sql_check', 'sql_expected', 'jsonExData', 'sqlExData',
        'is_true', 'is_xfail']

METHODS = {'get', 'post', 'put', 'delete', 'patch'}


def resolve(schema, root, depth=0):
    """解开 $ref，最多 8 层，避免循环引用爆栈。"""
    if depth > 8 or not isinstance(schema, dict):
        return schema or {}
    if '$ref' in schema:
        ref = schema['$ref'].split('/')[-1]
        return resolve(root.get('components', {}).get('schemas', {}).get(ref, {}), root, depth + 1)
    if schema.get('type') == 'array' or 'items' in schema:
        s = copy.deepcopy(schema)
        s['items'] = resolve(schema.get('items', {}), root, depth + 1)
        return s
    if 'properties' in schema:
        s = copy.deepcopy(schema)
        s['properties'] = {k: resolve(v, root, depth + 1) for k, v in schema['properties'].items()}
        return s
    return schema


def sample_value(name, schema, root):
    """按 schema 造一个合法样例值。"""
    schema = resolve(schema, root)
    if 'example' in schema:
        return schema['example']
    if 'default' in schema:
        return schema['default']
    if schema.get('enum'):
        return schema['enum'][0]
    t = schema.get('type')
    if t == 'integer':
        return 1
    if t == 'number':
        return 1.0
    if t == 'boolean':
        return True
    if t == 'array':
        return [sample_value(name, schema.get('items', {}), root)]
    if t == 'object':
        props = schema.get('properties', {})
        return {k: sample_value(k, v, root) for k, v in props.items()
                if k in schema.get('required', [])}
    if 'pageNum' in name or 'page_size' in name or 'pageSize' in name:
        return 1
    return 'test_auto'


def bad_value(schema, root):
    """造一个类型不一致的值。"""
    schema = resolve(schema, root)
    t = schema.get('type')
    if t == 'integer':
        return 'abc'
    if t == 'number':
        return 'abc'
    if t == 'boolean':
        return 'yes'
    return 12345


def build_rows(openapi, token_var='admin_token', start_id=1001, limit=200):
    rows = []
    cid = start_id
    for path, ops in (openapi.get('paths') or {}).items():
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method.lower() not in METHODS:
                continue
            op = op or {}
            tag = (op.get('tags') or ['未分类'])[0]
            summary = op.get('summary') or f"{method.upper()} {path}"

            # --- 参数：query / path / header ---
            params, path_params, header_params, required_names = {}, {}, {}, []
            for p in op.get('parameters', []) or []:
                p = resolve(p, openapi)
                name = p.get('name')
                loc = p.get('in')
                if loc == 'path':
                    path_params[name] = sample_value(name, p.get('schema', {}), openapi)
                elif loc == 'query':
                    params[name] = sample_value(name, p.get('schema', {}), openapi)
                elif loc == 'header':
                    header_params[name] = sample_value(name, p.get('schema', {}), openapi)
                if p.get('required'):
                    required_names.append(name)

            # --- 请求体 ---
            body_props, body_required = {}, []
            rb = op.get('requestBody') or {}
            content = (rb.get('content') or {})
            if content:
                media = content.get('application/json') or list(content.values())[0]
                body_schema = resolve(media.get('schema', {}), openapi)
                body_props = body_schema.get('properties', {})
                body_required = body_schema.get('required', [])
                for k in body_required:
                    if k not in body_props:
                        body_props[k] = {}

            real_path = path
            for k, v in path_params.items():
                real_path = real_path.replace('{%s}' % k, str(v))

            headers_tpl = ('{"Authorization":"Bearer {{%s}}"}' % token_var) \
                if op.get('security') else ''
            if header_params:
                headers_tpl = json.dumps(header_params, ensure_ascii=False) if not headers_tpl else headers_tpl

            def emit(story, title, params_=None, body_=None, headers_=headers_tpl):
                nonlocal cid
                rows.append({
                    'id': cid, 'feature': tag, 'story': story, 'title': title,
                    'method': method.lower(), 'path': real_path,
                    'headers': headers_,
                    'params': json.dumps(params_, ensure_ascii=False) if params_ else '',
                    'data': '', 'files': '',
                    'json': json.dumps(body_, ensure_ascii=False) if body_ is not None else '',
                    'check': '', 'expected': '',
                    'sql_check': '', 'sql_expected': '',
                    'jsonExData': '', 'sqlExData': '',
                    'is_true': 'False', 'is_xfail': '',
                })
                cid += 1

            # 1) 正向
            pos_body = None
            if body_props:
                pos_body = {k: sample_value(k, v, openapi) for k, v in body_props.items()
                            if k in body_required}
            pos_params = dict(params) if params else None
            emit('正向', f'[自动] {summary} - 正向', pos_params, pos_body)

            # 2) 必填缺失
            for name in required_names:
                p2 = dict(pos_params or {})
                p2.pop(name, None)
                emit('参数校验', f'[自动] {summary} - 缺少必填参数 {name}', p2, pos_body)
            for name in body_required:
                b2 = dict(pos_body or {})
                b2.pop(name, None)
                emit('参数校验', f'[自动] {summary} - 缺少必填字段 {name}', pos_params, b2)

            # 3) 类型错误（挑第一个整型/布尔型参数）
            for name in list(required_names) + list(body_required):
                sch = body_props.get(name, {}) if name in body_props else {}
                if not sch:
                    for p in op.get('parameters', []) or []:
                        if p.get('name') == name:
                            sch = p.get('schema', {})
                t = resolve(sch, openapi).get('type')
                if t in ('integer', 'number', 'boolean'):
                    if name in body_props:
                        b3 = dict(pos_body or {})
                        b3[name] = bad_value(sch, openapi)
                        emit('参数校验', f'[自动] {summary} - 字段 {name} 传非法类型', pos_params, b3)
                    else:
                        p3 = dict(pos_params or {})
                        p3[name] = bad_value(sch, openapi)
                        emit('参数校验', f'[自动] {summary} - 参数 {name} 传非法类型', p3, pos_body)
                    break

            # 4) 枚举越界
            for name, sch in body_props.items():
                s = resolve(sch, openapi)
                if s.get('enum'):
                    b4 = dict(pos_body or {})
                    b4[name] = '__INVALID__'
                    emit('参数校验', f'[自动] {summary} - 枚举字段 {name} 传非法值', pos_params, b4)
                    break

            # 5) 鉴权缺失
            if op.get('security'):
                emit('鉴权', f'[自动] {summary} - 不带 token 访问', pos_params, pos_body, headers_='')

            if len(rows) >= limit:
                return rows
    return rows


def write_sheet(xlsx_path, sheet_name, rows):
    wb = openpyxl.load_workbook(xlsx_path)
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)
    ws.append(HEADERS_CN)
    ws.append(KEYS)
    for r in rows:
        ws.append([r.get(k, '') for k in KEYS])
    for col, width in zip('ABCDEFGHIJKLMNOPQRS',
                          [6, 12, 10, 42, 8, 30, 38, 30, 20, 40, 20, 12, 20, 40, 16, 20, 20, 8, 8]):
        ws.column_dimensions[col].width = width
    wb.save(xlsx_path)


def main():
    ap = argparse.ArgumentParser(description='OpenAPI → 若依接口自动化 Excel 用例骨架')
    ap.add_argument('--openapi', required=True, help='openapi.json 路径（/v3/api-docs 导出）')
    ap.add_argument('--xlsx', required=True, help='目标 Excel（data/测试用例.xlsx）')
    ap.add_argument('--sheet', default='Sheet_auto', help='生成到哪个 sheet（默认 Sheet_auto）')
    ap.add_argument('--token-var', default='admin_token', help='鉴权占位变量名')
    ap.add_argument('--limit', type=int, default=200, help='最多生成多少条')
    args = ap.parse_args()

    with open(args.openapi, 'r', encoding='utf-8') as f:
        openapi = json.load(f)
    rows = build_rows(openapi, args.token_var, limit=args.limit)
    if not rows:
        print('[!] 没解析出任何接口，检查 openapi.json 是否为 OpenAPI 3.x')
        sys.exit(1)
    write_sheet(args.xlsx, args.sheet, rows)

    print(f'[OK] 生成 {len(rows)} 条用例骨架 → {args.xlsx} / sheet={args.sheet}')
    print('     所有用例「是否执行=False」；请补齐 check / expected / sql_check 后再改为 True。')
    print('     注意：excel_read.py 目前硬编码 Sheet2 —— 二选一：')
    print('       a) 把补完的用例行复制进 Sheet2；')
    print("       b) 改造 excel_read(EXCEL_PATH, 'Sheet2') 支持传入 sheet 名（推荐）。")


if __name__ == '__main__':
    main()
