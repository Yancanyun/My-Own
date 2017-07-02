import os
import sqlite3
import time

DebugMode = False
"""
Version 1.1
"""
Run_state = True
DB_name = 'Craddata.sqlite3'
DB_path = ''

Card_info = {'6061_bill_day': '10',
             '6654_bill_day': '22',
             '6061_card_number': 'card_num_6061',
             '6654_card_number': 'card_num_6654'}

DB_table_name = {'main_table': 'brush_card_record',
                 '6061_table_name': 'card_num_6061',
                 '6654_table_name': 'card_num_6654'}

DB_table1_info = '''\
CREATE TABLE %s(
brush_card_date DATE,
brush_card_time TIME,
card_num_6061 INTEGER,
card_num_6654 INTEGER
)'''

DB_card_table_info = '''\
CREATE TABLE %s(
Bill_start_day DATE,
Bill_end_day DATE,
brush_card_sum INTEGER,
brush_card_fee_sum REAL
)'''

Menu_info = ('''\
建行6061 %s至%s账单内已刷金额为：%s,手续费: %s
民生6654 %s至%s账单内已刷金额为：%s,手续费: %s''',
             '''\
选择需要记录的卡：
    (1) 建行6061
    (2) 民生6654
按相应数字进行选择...''')


def app_initial():
    global DB_path
    app_path = os.getcwd()
    if os.name == 'posix' or os.name == 'nt':
        DB_path = app_path + os.sep + DB_name
    else:
        print('未知的系统环境!')
        exit()

    if os.path.exists(DB_path) is not True:
        try:
            fp = open(DB_path, 'wb')
            fp.close()
            print('数据库文件已创建...')
        except:
            pass


def db_table_initial():
    """创建数据库所需表"""
    if create_table(DB_table1_info % DB_table_name['main_table']):
        Cxn.commit()

    if create_table(DB_card_table_info % DB_table_name['6061_table_name']):
        Cxn.commit()

    if create_table(DB_card_table_info % DB_table_name['6654_table_name']):
        Cxn.commit()


def create_table(f_info):
    """创建数据库表"""
    ret = False
    f_info = f_info.replace('\n', ' ')
    try:
        if Cur.execute(f_info):
            ret = True
    except sqlite3.OperationalError:
        pass

    return ret


def card_number_table_initial():
    """卡号对应的表 的初始化操作 创建月账单开始和结束日期"""
    info = 'SELECT Bill_start_day, Bill_end_day FROM %s'

    def temp(f_info):
        Cur.execute(f_info)
        return Cur.fetchall()

    def update_card_table(f_card_table_name):
        now_date = time.strftime('%Y-%m-%d', time.localtime())
        card = temp(info % f_card_table_name)
        if len(card) == 0:
            insert_info = insert_data(f_card_table_name)
            Cur.execute(insert_info)
        elif now_date > card[-1][1]:
            # 当现在日期大于账单日后需要创建新行
            insert_info = insert_data(f_card_table_name)
            Cur.execute(insert_info)

    update_card_table(DB_table_name['6061_table_name'])
    update_card_table(DB_table_name['6654_table_name'])

    Cxn.commit()


def table_insert(f_table_name, f_gold=0, f_card_number=''):
    """表数据插入"""
    insert_info = insert_data(f_table_name, f_gold, f_card_number)
    try:
        Cur.execute(insert_info)
        card_table_update(f_card_number)
        # 每次录入刷卡数据成功后更新卡号对应的表中的数据

        return True
    except sqlite3.OperationalError:
        print('table_insert()函数运行出错!!!')


def insert_data(f_table_name, f_gold=0, f_card_number=''):
    """生成表插入时需要的数据信息"""
    gold_6061 = 0
    gold_6654 = 0
    insert_info = ''
    date = time.strftime('%Y-%m-%d', time.localtime())

    if len(f_card_number) != 0:
        if f_card_number == Card_info['6061_card_number']:
            gold_6061 = f_gold
        elif f_card_number == Card_info['6654_card_number']:
            gold_6654 = f_gold

    if f_table_name == DB_table_name['main_table']:
        now_time = time.strftime('%H:%M:%S', time.localtime())

        insert_info = '''INSERT INTO \
%s(brush_card_date, brush_card_time, card_num_6061, card_num_6654) \
VALUES("%s", "%s", %s, %s)''' % (f_table_name, date, now_time, gold_6061, gold_6654)

    elif f_table_name == DB_table_name['6061_table_name']:
        start_date = get_start_date(date, Card_info['6061_card_number'])
        end_date = get_end_date(start_date, Card_info['6061_card_number'])
        insert_info = 'INSERT INTO %s VALUES("%s", "%s", 0, 0)' % (f_table_name, start_date, end_date)

    elif f_table_name == DB_table_name['6654_table_name']:
        start_date = get_start_date(date, Card_info['6654_card_number'])
        end_date = get_end_date(start_date, Card_info['6654_card_number'])
        insert_info = 'INSERT INTO %s VALUES("%s", "%s", 0, 0)' % (f_table_name, start_date, end_date)

    return insert_info


def card_table_update(f_card_number):
    """更新卡号表的数据"""
    bill_sum = 0
    table_name = ''
    if f_card_number == Card_info['6061_card_number']:
        table_name = DB_table_name['6061_table_name']
    elif f_card_number == Card_info['6654_card_number']:
        table_name = DB_table_name['6654_table_name']

    start_day, end_day = card_bill_day_inquire(table_name)
    get_bill_day_sum_info = 'SELECT %s FROM %s WHERE brush_card_date >= "%s" and brush_card_date <= "%s"' % \
                            (f_card_number, DB_table_name['main_table'], start_day, end_day)

    try:
        Cur.execute(get_bill_day_sum_info)
    except sqlite3.OperationalError:
        print('获取卡号%s的账单月内数据时出错!!!' % f_card_number)

    for temp in Cur.fetchall():
        bill_sum += temp[0]
    fee_sum = round((bill_sum * 0.006), 5)

    update_info = 'UPDATE %s SET brush_card_sum=%s, brush_card_fee_sum=%s WHERE Bill_start_day="%s"' % \
                  (table_name, bill_sum, fee_sum, start_day)

    try:
        Cur.execute(update_info)
    except sqlite3.OperationalError:
        print('更新卡号%s的表的数据时出错!!!' % f_card_number)


def get_start_date(f_date, f_card_number):
    if f_card_number == Card_info['6061_card_number']:
        return f_date[:8] + Card_info['6061_bill_day']

    elif f_card_number == Card_info['6654_card_number']:
        return f_date[:8] + Card_info['6654_bill_day']


def get_end_date(f_start_date, f_card_number):
    month = int(f_start_date[5:7])
    if month == 12:
        month = '01'
    elif month < 9:
        month = '0' + str(month + 1)
    else:
        month = str(month + 1)

    if f_card_number == Card_info['6061_card_number']:
        return f_start_date[:5] + month + '-09'

    elif f_card_number == Card_info['6654_card_number']:
        return f_start_date[:5] + month + '-21'


def card_bill_day_inquire(f_table_name):
    bill_day_inquire_info = 'SELECT Bill_start_day, Bill_end_day FROM %s' % f_table_name
    Cur.execute(bill_day_inquire_info)
    temp_info = Cur.fetchall()

    return temp_info[-1][0], temp_info[-1][1]


def get_table_name(f_card_number):
    table_name = ''

    if f_card_number == Card_info['6061_card_number']:
        table_name = DB_table_name['6061_table_name']

    elif f_card_number == Card_info['6654_card_number']:
        table_name = DB_table_name['6654_table_name']

    return table_name


def get_card_bill():

    def get_data(f_card_table_name):
        info = "SELECT * FROM %s" % f_card_table_name
        Cur.execute(info)
        return Cur.fetchall()

    card_6061_bill = get_data(DB_table_name['6061_table_name'])
    card_6654_bill = get_data(DB_table_name['6654_table_name'])

    return card_6061_bill, card_6654_bill


def app_exit():
    if Run_state is False and DebugMode is False:
        Cur.close()
        Cxn.close()
        #exit()


def menu():
    def get_key(f_char='->'):
        return input(f_char).lstrip().lower()

    def first_menu():
        card_6061, card_6654 = get_card_bill()
        print((Menu_info[0] % (card_6061[-1][0], card_6061[-1][1], int(card_6061[-1][2]), int(card_6061[-1][3]),
                               card_6654[-1][0], card_6654[-1][1], int(card_6654[-1][2]), int(card_6654[-1][3]))))

        print(Menu_info[1])     # 打印菜单

    def second_menu(f_card_number):
        print('输入卡号 %s 此次刷卡金额：' % f_card_number)

        gold = int(get_key(''))
        print('\n卡号 %s 此次刷卡金额为 %s,是否确认?' % (f_card_number[-4:], gold))

        state = get_key(r'Y/N')
        if state == 'y':
            if table_insert(DB_table_name['main_table'], gold, f_card_number):
                Cxn.commit()
                print('记录已添加...\n')
        else:
            print('\n')
            return

    first_menu()
    user_key = get_key()

    if user_key == '1':
        second_menu(Card_info['6061_card_number'])

    elif user_key == '2':
        second_menu(Card_info['6654_card_number'])

    elif user_key == 'q':
        global Run_state
        Run_state = False
        return


if __name__ == '__main__':
    app_initial()
    Cxn = sqlite3.connect(DB_path)
    Cur = Cxn.cursor()

    db_table_initial()
    card_number_table_initial()

    while Run_state is True:
        menu()

    app_exit()
