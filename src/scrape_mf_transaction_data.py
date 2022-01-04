from selenium import webdriver
import pandas as pd
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import getpass

'''
MoneyForward からトランザクションデータをスクレイピングして、CSVに格納する
TODO: ログインに必要な情報の暗号化
TODO: logger の追加
TODO: database への格納
'''
def login_mf(mfid_user, mfid_pswd):
    '''
    MoneyForward にログインする
    '''
    
    # browser = webdriver.Chrome('D:\\Users\\eX\\chromedriver_win32\\chromedriver.exe')
    browser = webdriver.Chrome('/usr/local/bin/chromedriver')
    url = "https://id.moneyforward.com/sign_in/email"

    browser.get(url)
    
    # ユーザID入力&次画面遷移
    time.sleep(3)
    browser.find_element_by_name("mfid_user[email]").send_keys(mfid_user)
    browser.find_element_by_xpath('/html/body/main/div/div/div/div/div[1]/section/form/div[2]/div/div[3]/input').click()

    # パスワード入力&次画面遷移
    time.sleep(3)
    browser.find_element_by_name("mfid_user[password]").send_keys(mfid_pswd)
    browser.find_element_by_xpath('/html/body/main/div/div/div/div/div[1]/section/form/div[2]/div/div[3]/input').click()

    # ログイン後のホーム画面へ遷移
    # To do: ログイン成功かの確認
    browser.find_element_by_xpath('/html/body/main/div/div/div/div[1]/div/ul/li[2]/a').click()
    browser.find_element_by_xpath('/html/body/main/div/div/div/div/div[1]/section/form/div[2]/div/div[2]/input').click()
    
    return browser

def get_table_header_list(table):
    '''
    table header を取得する -> 使わない
    '''
    return [th.get_text().strip() for th in table.find_all('th')]

def get_td_from_attr(trs, tag_class, key):
    '''
    trs(tr object のリスト)に対して、tag_classで指定されたクラスのタグから、 key で指定された属性値の値を取得する
    指定のクラスが見つからない tr に対しては、Noneを返す
    '''
    td_values = []
    for tr in trs:
        if tr.find('td', class_=tag_class) != None:
            td_value = tr.find('td', class_=tag_class)[key]
        else:
            td_value = None
        td_values.append(td_value)
    return td_values

def get_td_text(trs, tag_class):
    '''
    trs(tr object のリスト)に対して、tag_class で指定されたクラスのタグのテキストを取得し、テキストのリストで返す
    指定のクラスが見つからない tr に対しては、Noneを返す
    '''
    td_values = []
    for tr in trs:
        if tr.find('td', class_=tag_class) != None:
            td_value = tr.find('td', class_=tag_class).get_text().strip()
        else:
            td_value = None
        td_values.append(td_value)
    return td_values

def convert_period(period:str) -> str:
    '''
    2021/1/2 を入力されたら0埋めしてYYYYmmddにして返す
    '''
    year = period.split('/')[0]
    month = period.split('/')[1]
    day = period.split('/')[2]
    # 月日はゼロ埋めされていないので、ゼロ埋めする
    month = f'{month:0>2}'
    day = f'{day:0>2}'
    return str(year) + str(month) + str(day)

def parse_html_cf(html_cf):
    '''
    html の transaction のテーブルデータと対象期間を取得する
    '''
    # html データをパース、テーブルデータの取得
    soup = BeautifulSoup(html_cf, 'html.parser')
    cf_detail_table = soup.find('table', id='cf-detail-table')
    trs = cf_detail_table.find('tbody').find_all('tr')

    # 取得対象期間の取得
    # 'YYYY/mm/dd - YYYY/mm/dd' みたいな文字列、csv出力するときにファイル名に使用する
    period = soup.find('span', class_='fc-header-title').get_text().replace(' ','')
    period_start = convert_period(period.split('-')[0])
    period_end = convert_period(period.split('-')[1])
    period = period_start + '-' + period_end
    return trs, period

def get_table_data(html_cf):
    '''
    html の transaction のテーブルデータを取ってくる
    テーブルデータから各 transaction のデータを列ごとに取得して、辞書に格納する
    dataframe にして返す
    '''
    # html データをパース、テーブルデータの取得
    trs, period = parse_html_cf(html_cf)
    
    # データを格納する dictionary
    data_dict = {}
    
    # 計算対象データの取得
    data_dict['計算対象'] = [int(1) if tr.find('i', class_='icon-check') else int(0) for tr in trs]
    
    # 日付情報データの取得
    date_sortables = get_td_from_attr(trs, tag_class='date', key='data-table-sortable-value')
    data_dict['日付'] = [date_sortable.split('-')[0] for date_sortable in date_sortables]
    data_dict['ID'] = [date_sortable.split('-')[1] for date_sortable in date_sortables]
    
    # 内容データの取得
    data_dict['内容'] = get_td_text(trs, tag_class='content')
    
    # 金額データの取得
    amounts = get_td_text(trs, tag_class='number')
    data_dict['金額'] = [int(amount.split('\n')[0].replace(',','')) for amount in amounts]
    data_dict['振替'] = [int(1) if '振替' in amount.split('\n')[-1] else int(0) for amount in amounts]
    
    # 大項目データの取得
    data_dict['大項目'] = get_td_text(trs, tag_class='lctg')
    
    # 中項目データの取得
    data_dict['中項目'] = get_td_text(trs, tag_class='mctg')
    
    # メモデータの取得
    data_dict['メモ'] = get_td_text(trs, tag_class='memo')
    
    # 金融機関情報データの取得
    calc_accounts = [tr.find_all('td', class_='calc')[1].get_text().strip() for tr in trs]
    data_dict['口座_from'] = [calc_account.split('\n')[0] for calc_account in calc_accounts]
    data_dict['口座_to'] = [calc_account.split('\n')[-1] for calc_account in calc_accounts]

    calc_account_infos = [tr.find_all('td', class_='calc')[1]['data-original-title'] for tr in trs]
    data_dict['振替情報'] = [calc_account_info.replace('クリックして編集し、Enterキーを押せば変更出来ます。','') for calc_account_info in calc_account_infos]

    df = pd.DataFrame(data = data_dict).set_index('ID')

    return df, period

if __name__ == '__main__':
    print('login to moneyforward')
    mfid_user = input('User name: ')
    mfid_password = getpass.getpass('Password: ')
    browser = login_mf(mfid_user, mfid_password)
    url_cf = 'https://moneyforward.com/cf' # 家計 > 家計簿 のページ
    browser.get(url_cf)

    df_list = []

    for i in range(13):
        time.sleep(3)
        html_cf = browser.page_source.encode('utf-8')
        updated_time = datetime.now() # データ取得日時
        df, period = get_table_data(html_cf)
        df['更新日時'] = updated_time.strftime('%Y-%m-%d %H:%M:%S')
        df['期間'] = period
        df.to_csv('mf_scraped_data_' + str(period) + '_' + str(updated_time.strftime('%Y%m%d_%H%M%S'))+'.csv', encoding="utf_8_sig")
        df_list.append(df)

        # １つ前の月のページに移動
        browser.find_element_by_xpath('//*[@id="in_out"]/div[2]/button[1]').click()

    #url_bs = 'https://moneyforward.com/bs/portfolio' # 資産 > 資産内訳のページ
    #browser.get(url_bs)
    #html_bs = browser.page_source.encode('utf-8')
    #time.sleep(3)

    browser.close()