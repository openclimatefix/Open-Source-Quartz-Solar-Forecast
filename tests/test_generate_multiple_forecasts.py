"""

Unit testing script for scripts/generate_multiple_forecasts.py

"""

import os
import pandas as pd
import unittest
import subprocess
from quartz_solar_forecast.pydantic_models import PVSite

class TestGenerateForecasts(unittest.TestCase):
    # set up test
    def setUp(self):
        # repeat dummy sites    
        self.sites = {
            # PV_ID: Site
            12323: PVSite(latitude=50, longitude=0, capacity_kwp=7.5),
            2324: PVSite(latitude=54, longitude=2, capacity_kwp=10),
            1023: PVSite(latitude=48, longitude=-1, capacity_kwp=5),
            3242: PVSite(latitude=46, longitude=10, capacity_kwp=10),
            1453: PVSite(latitude=54, longitude=-8, capacity_kwp=2.5)
        }
        
        self.output_dir = "test_forecasts"
        os.makedirs(self.output_dir, exist_ok=True)

    # tear down files when done
    def tearDown(self):
        for file in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

    # run test forecasts
    def test_generate_forecasts(self):
        # Run the script
        subprocess.run(["python", "scripts/generate_multiple_forecasts.py"])

        for pv_id, site in self.sites.items():
            file_path = f"quartz_solar_forecast/dataset/forecast_{pv_id}.csv"
            
            # check if the created file exists
            self.assertTrue(os.path.exists(file_path))

            df = pd.read_csv(file_path)

            # Check if all columns are present
            self.assertIn("pv_id", df.columns)
            self.assertIn("latitude", df.columns)
            self.assertIn("longitude", df.columns)
            self.assertIn("capacity_kwp", df.columns)
            self.assertIn("forecast creation time", df.columns)
            self.assertIn("forecast date", df.columns)
            self.assertIn("forecast time", df.columns)
            self.assertIn("power_wh", df.columns)

if __name__ == '__main__':
    unittest.main()