from selenium import webdriver
import pandas as pd
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import getpass

def login_zaim(id, pswd):
    '''
    Selenium で Zaim にログインする
    '''
    browser = webdriver.Chrome('/usr/local/bin/chromedriver')
    url = 'https://auth.zaim.net/'
    browser.get(url)
    
    browser.find_element_by_id("UserEmail").send_keys(account_id)
    browser.find_element_by_id("UserPassword").send_keys(password)
    browser.find_element_by_xpath('//*[@id="UserLoginForm"]/div[4]/input').click()
    
    return browser

def create_target_url(YYYYmm_from, YYYYmm_to):
    urls = []
    
    YYYYmm = YYYYmm_from
        
    while int(YYYYmm) <= int(YYYYmm_to):
        mm = int(YYYYmm[4:])
        YYYY = int(YYYYmm[:4])
        
        url = 'https://zaim.net/money?month=' + YYYYmm
        urls.append(url)
        
        if mm == 12:
            mm = 1
            YYYY = YYYY + 1
        else:
            mm = mm + 1
            
        YYYYmm = str(YYYY * 100 + mm)
            
    return urls

def get_table_data(html):
    '''
    html の transaction のテーブルデータを取ってくる
    テーブルデータから各 transaction のデータを列ごとに取得して辞書に格納する
    dataframe にして返す
    '''
    soup = BeautifulSoup(html, 'html.parser')
    
    period = soup.find('div', class_='MoneySearchBar-module__monthTitle___d2CDA').get_text() # "2021 年 1 月”の形式
    period = period.replace(' ', '').replace('月', '')
    year = period.split('年')[0]
    month = period.split('年')[1]
    period = f'{year}' + f'{month:0>2}' # YYYYmm の形式

    table = soup.find('div', class_='SearchResult-module__listField___1sWk-')
    trs = table.find_all('div', class_='SearchResult-module__body___1CNGh')    
    
    data_dict = {}
    data_urls = [tr.find('i', class_='SearchResult-module__icon___hD8NZ')['data-url'] for tr in trs]
    data_dict['id'] = [data_url.split('/')[2] for data_url in data_urls]
    data_dict['計算対象'] = [tr.find('div', class_='SearchResult-module__calc___1p4Cf').find_next()['title'] for tr in trs]
    data_dict['日付'] = [tr.find('div', class_='SearchResult-module__date___2mixB').get_text() for tr in trs]
    data_dict['大項目'] = [tr.find('div', class_='SearchResult-module__category___1H220').find('span', class_='material-icons icon-sm')['data-title'] for tr in trs]
    data_dict['中項目'] = [tr.find('div', class_='SearchResult-module__category___1H220').find('span', class_='SearchResult-module__link___19Lax').get_text() for tr in trs]
    data_dict['金額'] = [int(tr.find('div', class_='SearchResult-module__price___3MV22').get_text().replace(',', '').replace('¥', '')) for tr in trs]
    data_dict['口座_from'] = [tr.find('div', class_='SearchResult-module__fromAccount___2-lXL').find('img')['data-title'] if tr.find('div', class_='SearchResult-module__fromAccount___2-lXL').find('img') != None else None for tr in trs]
    data_dict['口座_to'] = [tr.find('div', class_='SearchResult-module__toAccount___X4LW3').find('img')['data-title'] if tr.find('div', class_='SearchResult-module__toAccount___X4LW3').find('img') != None else None for tr in trs]

    data_dict['内容'] = [tr.find('div', class_='SearchResult-module__place___1rIP-').get_text() for tr in trs]
    data_dict['品目'] = [tr.find('div', class_='SearchResult-module__name___eCzGb').get_text() for tr in trs]
    data_dict['メモ'] = [tr.find('div', class_='SearchResult-module__comment___2Kvn5').get_text() for tr in trs]
    
    return pd.DataFrame(data = data_dict).set_index('id'), period

if __name__ == '__main__':
    print('login to Zaim')
    account_id = input('User name (email address): ')
    password = getpass.getpass('Password: ')
    browser = login_zaim(account_id, password)
    
    target_urls = create_target_url('201911', '202112')
    
    for target_url in target_urls:
        browser.get(target_url)
        time.sleep(3)
        html = browser.page_source.encode('utf-8')
        updated_time = datetime.now() # データ取得日時        
        df, period = get_table_data(html)
        df['更新日時'] = updated_time.strftime('%Y-%m-%d %H:%M:%S')
        df['期間'] = period

        df.to_csv('zaim_scraped_data_' + str(period) + '_' + str(updated_time.strftime('%Y%m%d_%H%M%S'))+'.csv', encoding="utf_8_sig")
    
    browser.close()