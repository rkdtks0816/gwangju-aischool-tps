import csv
import numpy as np
from flask import Flask, render_template, request
from sklearn.ensemble import RandomForestRegressor
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import timedelta, date
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)    
app.secret_key = 'tps'



def weather_data(input_area, input_start_date, input_end_date):

    today = date.today()
    start_date = date.fromisoformat(input_start_date)
    start_month = start_date.month
    end_date = date.fromisoformat(input_end_date)

    today_diff = int((start_date - today).days)
    date_diff = int((end_date - start_date).days)

    df_data = {}
    month_change = [-1]
    num = re.compile('[^0-9+]')
    df = pd.read_csv("태양광_테스트_데이터.csv")

    past_month = start_date.month

    for i in range(date_diff+1):
        next_date = start_date + timedelta(days=i)

        df_data['일자'] = str(next_date.day)

        html = requests.get(f"https://www.accuweather.com/ko/kr/{input_area}/224269/daily-weather-forecast/224269?day={today_diff+i+1}", headers={"User-Agent" : "Mozilla/5.0"}).text
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
        
    return df, month_change, start_month

def photovoltaics_train():
    
    photovoltaics_df = pd.read_csv('태양광_데이터.csv')
    X = photovoltaics_df[[
        '최저기온(°C)',
        '최고기온(°C)',
        '일강수량(mm)',
        '평균 풍속(m/s)',
        '평균 전운량(1/10)'
    ]]
    y = photovoltaics_df['발전량'].div(99)
    
    photovoltaics_model = RandomForestRegressor(n_jobs=-1)

    photovoltaics_model.fit(X, y)    
    
    return photovoltaics_model

@app.route("/")
def main_page():
    
    return render_template('home.html')

@app.route("/month", methods=["GET"])
def month():
    input_method = "GET"
    input_capacity = request.args.get("month_capacity")
    input_area = request.args.get("month_area")
    input_start_date = request.args.get("month_start")
    input_end_date = request.args.get("month_end")
    
    train_model = photovoltaics_train()
    weather_df , month_change, start_month = weather_data(input_area, input_start_date, input_end_date)
    
    X_test = weather_df[[
        '최저기온(°C)',
        '최고기온(°C)',
        '일강수량(mm)',
        '평균 풍속(m/s)',
        '평균 전운량(1/10)'
    ]]
    X_test = X_test.astype('float')

    photovoltaics_predict = train_model.predict(X_test) * int(input_capacity)
    
    y_value = int((np.max(photovoltaics_predict) // 100 + 1) * 100)
    photovoltaics_predict_percent = photovoltaics_predict/y_value *100
    photovoltaics_predict_percent = np.asarray(photovoltaics_predict_percent, dtype = int).tolist()
    date_list = weather_df['일자'].values.tolist()
    
    f = open('predict_data/month.csv', 'w', encoding='utf-8', newline='')
    writer = csv.writer(f)
    writer.writerow(photovoltaics_predict_percent)
    writer.writerow(date_list)
    writer.writerow([start_month])
    writer.writerow(month_change)
    writer.writerow([y_value])
    f.close()
    
    return render_template(
                'month.html', 
                photovoltaics_predict_percent=photovoltaics_predict_percent, 
                date_list=date_list, 
                start_month=start_month,
                month_change=month_change,
                y_value=y_value
            )

@app.route("/month_result", methods=["GET"])
def 중기_출력_월별():
    
    input_method = "GET"
    input_month = request.args.get("each_month")
    
    csv_list = []
    f = open("predict_data/month.csv", "r")
    reader = csv.reader(f)

    for row in reader:
        csv_list.append(row)
    
    return render_template(
                'month_result.html',   
                photovoltaics_predict_percent=list(map(int, csv_list[0])), 
                date_list=csv_list[1], 
                start_month=list(map(int, csv_list[2]))[0],
                month_change=list(map(int, csv_list[3])),
                y_value=list(map(int, csv_list[4]))[0],
                input_month=input_month
            )

@app.route("/예상_수익_입력")
def 예상_수익_입력():
    
    return render_template('예상_수익_입력.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='5000', debug=True)