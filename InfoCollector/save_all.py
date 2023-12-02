# -- coding: utf-8 --
""":authors:
    zhuxiaohu
:create_date:
    2023/10/21 14:39
:last_date:
    2023/10/21 14:39
:description:
    
"""
import json
import os

import akshare as ak
import logging
import concurrent.futures
import threading

import requests
from bs4 import BeautifulSoup


def get_price(symbol, start_time, end_time, period="daily"):
    """
    获取指定股票一定时间段内的收盘价
    :param symbol: 股票代码
    :param start_time:开始时间
    :param end_time:结束时间
    :param period:时间间隔
    :return:
    """
    if "daily" == period:
        result = ak.stock_zh_a_hist(symbol=symbol, period=period, start_date=start_time, end_date=end_time,
                                    adjust="qfq")
    else:
        result = ak.stock_zh_a_hist_min_em(symbol=symbol, period=period, start_date=start_time, end_date=end_time,
                                           adjust="qfq")
    return result


# def save_all_data():
#     stock_data_df = ak.stock_zh_a_spot_em()
#     exclude_code = []
#     exclude_code.extend(ak.stock_kc_a_spot_em()['代码'].tolist())
#     exclude_code.extend(ak.stock_cy_a_spot_em()['代码'].tolist())
#     for _, stock_data in stock_data_df.iterrows():
#         name = stock_data['名称'].replace('*', '')
#         code = stock_data['代码']
#         if code in exclude_code:
#             continue
#         price_data = get_price(code, '19700101', '20231018', period='daily')
#         filename = 'daily_data_exclude_new/{}_{}.txt'.format(name, code)
#         price_data.to_csv(filename, index=False)

# Setting up the logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


def save_stock_data(stock_data, exclude_code):
    name = stock_data['名称'].replace('*', '')
    code = stock_data['代码']
    if code not in exclude_code:
        price_data = get_price(code, '19700101', '20291021', period='daily')
        filename = '../daily_data_exclude_new_can_buy/{}_{}.txt'.format(name, code)
        # price_data不为空才保存
        if not price_data.empty:
            price_data.to_csv(filename, index=False)
            # Logging the save operation with the timestamp
            logging.info(f"Saved data for {name} ({code}) to {filename}")

def write_json(file_path, data):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing {file_path} exception: {e}")

def fetch_announcements(stock_code):
    extracted_data = []
    page = 1

    while True:
        if page == 1:
            url = f'https://guba.eastmoney.com/list,{stock_code},3,f.html'
        else:
            url = f'https://guba.eastmoney.com/list,{stock_code},3,f_{page}.html'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        response = requests.get(url, headers=headers)

        soup = BeautifulSoup(response.text, 'html.parser')
        # 找到包含article_list的脚本
        scripts = soup.find_all('script')
        article_list_script = None
        for script in scripts:
            if 'article_list' in script.text:
                article_list_script = script.text
                break

        article_list_str = article_list_script.split('var article_list=')[1].split('};')[0] + '}'
        article_list_json = json.loads(article_list_str)
        code_name = article_list_json['bar_name']
        # Extracting the required information from each article
        articles = article_list_json['re']
        if len(articles) == 0:
            break
        for article in articles:
            title = article['post_title']
            notice_type = article['notice_type']
            publish_time = article['post_publish_time']
            extracted_data.append({
                'post_title': title,
                'notice_type': notice_type,
                'post_publish_time': publish_time
            })
        page += 1
    # 将extracted_data写入文件
    write_json(f'../announcements/{code_name}_{stock_code}.json', extracted_data)
    print(f"Saved data for {code_name} ({stock_code}) to ../announcements/{code_name}_{stock_code}.json")

def get_all_notice():
    stock_data_df = ak.stock_zh_a_spot_em()
    exclude_code = []
    need_code = []
    exclude_code.extend(ak.stock_kc_a_spot_em()['代码'].tolist())
    exclude_code.extend(ak.stock_cy_a_spot_em()['代码'].tolist())
    # 获取以00或者30开头的股票代码
    need_code.extend([code for code in stock_data_df['代码'].tolist() if code.startswith('000') or code.startswith('002')  or code.startswith('003')
                      or code.startswith('001') or code.startswith('600') or code.startswith('601') or code.startswith('603') or code.startswith('605')])
    for code in need_code:
        fetch_announcements(code)

def save_all_data():

    stock_data_df = ak.stock_zh_a_spot_em()
    # 获取stock_data_df中的股票代码
    all_code = stock_data_df['代码'].tolist()
    exclude_code = []
    need_code = []
    exclude_code.extend(ak.stock_kc_a_spot_em()['代码'].tolist())
    exclude_code.extend(ak.stock_cy_a_spot_em()['代码'].tolist())
    # 获取以00或者30开头的股票代码
    need_code.extend([code for code in stock_data_df['代码'].tolist() if code.startswith('000') or code.startswith('002')  or code.startswith('003')
                      or code.startswith('001') or code.startswith('600') or code.startswith('601') or code.startswith('603') or code.startswith('605')])

    new_exclude_code = [code for code in all_code if code not in need_code]
    new_exclude_code.extend(exclude_code)
    # 将new_exclude_code去重
    new_exclude_code = list(set(new_exclude_code))
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as executor:
        futures = [executor.submit(save_stock_data, stock_data, new_exclude_code) for _, stock_data in
                   stock_data_df.iterrows()]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error occurred: {e}")


def fun():
    save_all_data()


if __name__ == '__main__':
    # price_data = get_price('000001', '19700101', '20231017', period='daily')
    # print(price_data)
    # data = ak.stock_financial_analysis_indicator('600242')
    # data1 = ak.stock_zh_a_st_em()
    # data2 = ak.stock_notice_report(symbol='全部', date="20231106")
    # data3 = ak.stock_zh_a_gdhs_detail_em(symbol="600242")
    # fun()
    get_all_notice()
