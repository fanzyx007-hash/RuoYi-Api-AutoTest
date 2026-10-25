#读取Excel文件
import openpyxl

def excel_read(excel_path):
    # 打开文件本
    workbook = openpyxl.load_workbook(excel_path)
    # 选择sheet
    worksheet = workbook['Sheet2']
    # 读数据操作
    # 0.需要有一个data来返回读取到的数据，data是列表，因为参数化需要传入的是列表
    data = []
    # 1.先把key读出来存到keys中，即先读取第二行
    keys = [cell.value for cell in worksheet[2]]  # cell是一个单元格的对象，我们要获取的是单元格里的值cell.value
    # 2.从第三行开始依次读取值，存入到data中
    for row in worksheet.iter_rows(min_row=3, values_only=True):
        dict_data = dict(zip(keys, row))
        if dict_data['is_true']:
            data.append(dict_data)
    # 关闭文件
    workbook.close()
    return data

