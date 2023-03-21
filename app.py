import matplotlib.pyplot as plt
import csv
import joblib
import numpy as np
from flask import Flask, render_template, request
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import timedelta, date
import warnings
warnings.filterwarnings('ignore')
from matplotlib import font_manager, rc
font_path = "C:/Windows/Fonts/NGULIM.TTF"
font = font_manager.FontProperties(fname=font_path).get_name()
rc('font', family=font)

app = Flask(__name__)    
app.secret_key = 'tps'

def day_sunrise_sunset(input_day_area):
    options = webdriver.ChromeOptions()

    options.add_argument("headless")

    options.add_experimental_option("prefs", {
      "download.default_directory": "day_data",
      "download.prompt_for_download": False,
      "download.directory_upgrade": True,
      "safebrowsing.enabled": True
    })

    driver = webdriver.Chrome('./chromedriver.exe', chrome_options=options)
    url = 'https://www.google.co.kr'
    driver.get(url)
    wait = WebDriverWait(driver, 5)
    driver.find_element(By.CSS_SELECTOR, "body > div.L3eUgb > div.o3j99.ikrT4e.om7nvf > form > div:nth-child(1) > div.A8SBwf > div.RNNXgb > div > div.a4bIc > input").send_keys(f"{input_day_area} 내일 일출 일몰")
    driver.find_element(By.CSS_SELECTOR, "body > div.L3eUgb > div.o3j99.ikrT4e.om7nvf > form > div:nth-child(1) > div.A8SBwf > div.RNNXgb > div > div.a4bIc > input").send_keys(Keys.ENTER)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    sunrise = int(soup.find_all("div", {"class":"MUxGbd t51gnb lyLwlc lEBKkf"})[0].text[3])
    sunset = int(soup.find_all("div", {"class":"MUxGbd t51gnb lyLwlc lEBKkf"})[1].text[3])
    
    return sunrise, sunset

def day_weather(input_day_area):

    num = re.compile('[^0-9+]')
    df = pd.read_csv("day_data/day_columns.csv", encoding="utf-8-sig")
    html_accu = requests.get(f"https://www.accuweather.com/ko/kr/boseong-gun/224269/hourly-weather-forecast/{input_day_area}?day=2", headers={"User-Agent" : "Mozilla/5.0"}).text
    soup_accu = BeautifulSoup(html_accu, "html.parser")


    for i in range(24):
        data_list = []
        time_weather = soup_accu.find("div", {"id":f"hourlyCard{i}"})
        temp_data = int(num.sub('', time_weather.find("div", {"class":"temp metric"}).text))
        precipitation_data = 0.0
        PM_data = 1
        p_list = time_weather.find_all("p")    
        for p in p_list:
            if "강수량" in p:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
                precipitation_data = int(num.sub('', p.text))/10
            if "바람" in p:
                wind_data = int(num.sub('', p.text))
            if "습도" in p:
                humidity_data = int(num.sub('', p.text))
            if "구름량" in p:
                cloud_data = int(num.sub('', p.text))/10
            if "대기질" in p and "건강에 해로움" in p or "건강에 매우 해로움" in p or "위험" in p:
                PM_data = 0
        data_list.append(i)
        data_list.append(temp_data)
        data_list.append(precipitation_data)
        data_list.append(wind_data)
        data_list.append(humidity_data)
        data_list.append(cloud_data)
        data_list.append(PM_data)
        df = df.append(pd.Series(data_list, index=df.columns), ignore_index=True)
        
    return df

def month_weather(input_month_area, input_month_start_date, input_month_end_date):

    today = date.today()
    start_date = date.fromisoformat(input_month_start_date)
    start_month = start_date.month
    end_date = date.fromisoformat(input_month_end_date)

    today_diff = int((start_date - today).days)
    date_diff = int((end_date - start_date).days)

    df_data = {}
    month_change = [-1]
    num = re.compile('[^0-9+]')
    df = pd.read_csv("month_data/month_columns.csv")

    past_month = start_date.month

    for i in range(date_diff+1):
        next_date = start_date + timedelta(days=i)

        df_data['일자'] = str(next_date)

        html = requests.get(f"https://www.accuweather.com/ko/kr/boseong-gun/224269/daily-weather-forecast/{input_month_area}?day={today_diff+i+1}", headers={"User-Agent" : "Mozilla/5.0"}).text
        soup = BeautifulSoup(html, "html.parser")

        temperature_list = soup.find_all("div", {"class":"temperature"})
        for temperature in temperature_list:
            if "최고" in str(temperature):
                high = num.sub('', str(temperature))
                df_data['최고기온(°C)'] = float(high)
            if "최저" in str(temperature):
                low = num.sub('', str(temperature))
                df_data['최저기온(°C)'] = float(low)
                break

        panel_item_list = soup.find_all("p", {"class":"panel-item"})
        for panel_item in panel_item_list:
            if ">강수<" in str(panel_item):
                precipitation = num.sub('', str(panel_item))
                df_data['일강수량(mm)'] = float(precipitation)/10
            if "바람" in str(panel_item):
                wind = num.sub('', str(panel_item))
                df_data['평균 풍속(m/s)'] = float(wind)
            if "구름량" in str(panel_item):
                cloud = num.sub('', str(panel_item))
                df_data['평균 전운량(1/10)'] = float(cloud)/10
                break

        df = df.append(df_data, ignore_index=True)
        if next_date.month != past_month:
            month_change.append(i-1)
        past_month = next_date.month
    month_change.append(date_diff)

    smp_df = pd.DataFrame()
    smp_df['temp_max'] = df['최고기온(°C)'].values
    smp_df['temp_min'] = df['최저기온(°C)'].values
    smp_df['temp_mean'] = [smp_df['temp_max'].to_list()[i] + smp_df['temp_min'].to_list()[i] / 2 for i in range(len(smp_df['temp_max'].to_list()))]
    smp_df['month'] = pd.to_datetime(df['일자']).dt.month
    smp_df['dayofweek'] = pd.to_datetime(df['일자']).dt.dayofweek
    supply_model = joblib.load('smp_data/supply_model.pkl')
    smp_df['supply'] = supply_model.predict(smp_df)
    smp_df['weekofyear'] = pd.to_datetime(df['일자']).dt.weekofyear
    smp_df = smp_df.drop(columns='month')

    df['일자'] = pd.to_datetime(df['일자']).dt.day

    smp_model = joblib.load('smp_data/smp_model.pkl')
    smp_predict = smp_model.predict(smp_df)
    
    return smp_df, df, month_change, start_month

#################### app ####################

@app.route("/")
def main_page():
    
    return render_template('home.html')

@app.route("/input_page", methods=["GET"])
def input_page():
    input_method = "GET"
    input_capacity = request.args.get("input_capacity")
    input_city = request.args.get("city")
    input_county = request.args.get("county")
    
    area_df = pd.read_csv('day_data/county.csv', encoding="cp949")
    area_df = area_df[["지역명","지역번호"]]
    area_df.set_index("지역명", inplace=True)
    input_area = str(area_df.loc[input_county].to_list()[0])
    
    train_model = joblib.load('day_data/day_model.pkl')
    day_weather_df = day_weather(input_area)
    day_sunrise, day_sunset = day_sunrise_sunset(input_city +" "+ input_county)
    
    
    
    X_test = day_weather_df[[
        '기온(°C)', 
        '강수량(mm)', 
        '풍속(m/s)', 
        '습도(%)', 
        '전운량(10분위)',
        '미세먼지'
    ]]
    X_test = X_test.astype('float')

    day_predict = list(map(round, (train_model.predict(X_test) * int(input_capacity))))

    
    day_date_list = list(map(int, day_weather_df['일자'].values.tolist()))
    day_total = round(sum(day_predict[day_sunrise+2:day_sunset+13]))
    
    plt.bar(day_date_list[day_sunrise+2:day_sunset+13], day_predict[day_sunrise+2:day_sunset+13], color = '#FFBB00')
    plt.xticks(day_date_list[day_sunrise+2:day_sunset+13], day_date_list[day_sunrise+2:day_sunset+13])
    plt.savefig(f'static/images/day_graph.png', dpi=100)
    plt.close()
    
    # warning
    next_day = date.today() + timedelta(days=1)
    print(str(next_day))
    smp_df, month_weather_df , month_change, start_month = month_weather(input_area, str(next_day), str(next_day))

    warning_img = []
    warning_img.append("sun")
    if month_weather_df['일강수량(mm)'].values >= 110 or month_weather_df['평균 풍속(m/s)'].values >= 50 or month_weather_df['뇌우 확률'].values >= 80:
        warning_img = []
        if month_weather_df['일강수량(mm)'].values >= 110:
            warning_img.append("rain")
        if month_weather_df['평균 풍속(m/s)'].values >= 50:
            warning_img.append("wind")
        if month_weather_df['뇌우 확률'].values >= 80:
            warning_img.append("thunder")
        
    f = open('day_data/input_data.csv', 'w', encoding='utf-8', newline='')
    writer = csv.writer(f)
    writer.writerow([input_capacity])
    writer.writerow([input_area])
    writer.writerow(warning_img)
    writer.writerow([len(warning_img)])
    writer.writerow([day_total])
    f.close()
    
    return render_template('input_page.html', warning_img=warning_img, len_warning_img=len(warning_img), day_total=day_total)

@app.route("/month", methods=["GET"])
def month():
    input_method = "GET"
    input_start_date = request.args.get("month_start")
    input_end_date = request.args.get("month_end")
    
    csv_list = []
    f = open('day_data/input_data.csv', 'r', encoding='utf-8', newline='')
    rea = csv.reader(f)
    for row in rea:
        csv_list.append(row)
    f.close()

    input_capacity = list(map(int, csv_list[0]))[0]
    input_area = csv_list[1][0]
    warning_img = csv_list[2]
    len_warning_img = list(map(int, csv_list[3]))[0]
    day_total = list(map(int, csv_list[4]))[0]
    
    smp_df, month_weather_df , month_change, start_month = month_weather(input_area, input_start_date, input_end_date)
    
    train_model = joblib.load('month_data/month_model.pkl')
    smp_model = joblib.load('smp_data/smp_model.pkl')
    
    X_test = month_weather_df[[
        '최저기온(°C)',
        '최고기온(°C)',
        '일강수량(mm)',
        '평균 풍속(m/s)',
        '평균 전운량(1/10)'
    ]]
    X_test = X_test.astype('float')

    month_predict = list(map(round, (train_model.predict(X_test) * int(input_capacity))))
    smp_predict = smp_model.predict(smp_df)
    
    month_total = round(sum(month_predict))
    smp_total = round(sum([month_predict[i] * smp_predict[i] for i in range(len(smp_df['temp_max'].to_list()))]))
    month_date_list = month_weather_df['일자'].values.tolist()
    
    for input_month_select in range(1, len(month_change)):
        plt.bar(month_date_list[(month_change[input_month_select-1]+1):(month_change[input_month_select]+1)], month_predict[(month_change[input_month_select-1]+1):(month_change[input_month_select]+1)], color = '#FFBB00')
        plt.xticks(month_date_list[(month_change[input_month_select-1]+1):(month_change[input_month_select]+1)], month_date_list[(month_change[input_month_select-1]+1):(month_change[input_month_select]+1)])
        plt.savefig(f'static/images/month_graph{start_month+input_month_select-1}.png', dpi=100)
        plt.close()
        plt.bar(month_date_list[(month_change[input_month_select-1]+1):(month_change[input_month_select]+1)], smp_predict[(month_change[input_month_select-1]+1):(month_change[input_month_select]+1)], color = '#FFBB00')
        plt.xticks(month_date_list[(month_change[input_month_select-1]+1):(month_change[input_month_select]+1)], month_date_list[(month_change[input_month_select-1]+1):(month_change[input_month_select]+1)])
        plt.savefig(f'static/images/smp_graph{start_month+input_month_select-1}.png', dpi=100)
        plt.close()
    
    f = open('month_data/month_predict.csv', 'w', encoding='utf-8', newline='')
    writer = csv.writer(f)
    writer.writerow([start_month])
    writer.writerow(month_change)
    writer.writerow([month_total])
    writer.writerow([smp_total])
    writer.writerow(warning_img)
    writer.writerow([len_warning_img])
    writer.writerow([day_total])
    f.close()
    
    return render_template(
                'month.html', 
                month_date_list=month_date_list, 
                start_month=start_month,
                month_change=month_change,
                month_total=month_total,
                smp_total=smp_total,
                warning_img=warning_img,
                len_warning_img=len_warning_img,
                day_total=day_total
            )

@app.route("/month_result", methods=["GET"])
def month_result():
    input_method = "GET"
    input_month_select = int(request.args.get("month_select"))
    
    csv_list = []
    f = open('month_data/month_predict.csv', 'r', encoding='utf-8', newline='')
    rea = csv.reader(f)
    for row in rea:
        csv_list.append(row)
    f.close()

    start_month=list(map(int, csv_list[0]))[0]
    month_change=list(map(int, csv_list[1]))
    month_total=list(map(int, csv_list[2]))[0]
    smp_total=list(map(int, csv_list[3]))[0]
    warning_img = csv_list[4]
    len_warning_img = list(map(int, csv_list[5]))[0]
    day_total = list(map(int, csv_list[6]))[0]
    
    return render_template(
                'month_result.html',  
                start_month=start_month,
                month_change=month_change,
                input_month_select=input_month_select,
                month_total=month_total,
                smp_total=smp_total,
                warning_img=warning_img,
                len_warning_img=len_warning_img,
                day_total=day_total
            )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='5000', debug=True)