
from quartz_solar_forecast.forecast import run_forecast
import csv
from datetime import datetime, timedelta
from quartz_solar_forecast.pydantic_models import PVSite
import numpy as np
import os

def generate_forecast_csv(init_time_frequency, start_datetime_str, end_datetime_str,site):
    start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
    end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
    file_name = f"{start_datetime.strftime('%Y%m%d-%H%M%S')}_{end_datetime.strftime('%Y%m%d-%H%M%S')}.csv"
    downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    file_path = os.path.join(downloads_dir, file_name)

    all_forecasts = []
    current_init_time = init_time_frequency
    while current_init_time <= (end_datetime - start_datetime).total_seconds() / 60:
        forecasts = []
        current_time = start_datetime
        while current_time <= end_datetime:
            forecast_data = run_forecast(site, current_time)
            if isinstance(forecast_data, np.ndarray):
                forecast_list = forecast_data.tolist()  
            else:
                forecast_list = forecast_data["power_wh"].tolist() 
            forecast_dict = {"Init Time": current_time, "Pwh": forecast_list}
            forecasts.append(forecast_dict)
            current_time += timedelta(minutes=init_time_frequency)
        all_forecasts.extend(forecasts)
        current_init_time += init_time_frequency
        break
    with open(file_path, 'w', newline='') as csvfile:
        fieldnames = ["Init Time", "Pwh"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for forecast in all_forecasts:
            writer.writerow(forecast)
    print(f"Forecasts {file_name} generated and saved to Downloads folder.")


#To save the forecast file as a csv during the given time frequency follow below steps:
    
#from quartz_solar_forecast.gen_forecasts import generate_forecast_csv
#from quartz_solar_forecast.pydantic_models import PVSite
    
#site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)

#Pass time frequency(in minutes) (integer) , start datetime(string) YYYY-MM-DD HH:MM ,end datetime (string) YYYY-MM-DD HH:MM and the site
#generate_forecast_csv(10,"2024-03-19 13:00" , "2024-03-19 14:00" , site)
    
#The file will be saved to the downloads folder.