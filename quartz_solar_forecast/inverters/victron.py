from typing import Callable

import pandas as pd
from datetime import datetime, timedelta
from quartz_solar_forecast.inverters.inverter import AbstractInverter
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from vrmapi.vrm import VRM_API


class VictronSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    username: str = Field(alias="VICTRON_USER")
    password: str = Field(alias="VICTRON_PASS")


class VictronInverter(AbstractInverter):

    def __init__(self, get_sites: Callable, get_kwh_stats: Callable):
        self.__get_sites = get_sites
        self.__get_kwh_stats = get_kwh_stats

    @classmethod
    def from_settings(cls, settings: VictronSettings):
        api = VRM_API(username=settings.username, password=settings.password)
        get_sites = lambda: api.get_user_sites(api.user_id)
        end = datetime.now()
        start = end - timedelta(weeks=1)
        get_kwh_stats = lambda site_id: api.get_kwh_stats(site_id, start=start, end=end)
        return cls(get_sites, get_kwh_stats)

    def get_data(self, ts: pd.Timestamp) -> pd.DataFrame:
        sites = self.__get_sites()
        # get first site (bit of a guess)
        first_site_id = sites["records"][0]["idSite"]

        stats = self.__get_kwh_stats(first_site_id)

        kwh = stats["records"]["kwh"]

        df = pd.DataFrame(kwh)

        df[0] = pd.to_datetime(df[0], unit='ms')
        df.columns = ["timestamp", "power_kw"]
        return df
