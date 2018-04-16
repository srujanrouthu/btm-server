import pytz
import pandas as pd
import numpy as np
from datetime import datetime, time
import matplotlib.pyplot as plt

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from iso.models import Price


class Command(BaseCommand):
    def handle(self, *args, **options):
        nodes = ['MENLO_6_N004', 'GLENWOOD_6_N005', 'WOODSIDE_6_N004', 'BLLEHVN_6_N009', 'SARATOGA_2_N011']
        start = make_aware(datetime(2017, 1, 1), pytz.timezone('America/Los_Angeles'))
        end = make_aware(datetime(2018, 1, 1), pytz.timezone('America/Los_Angeles'))
        price_records = Price.objects.filter(start__gte=start, start__lt=end) \
            .order_by('start') \
            .values('start', 'node', 'price')
        price_df = pd.DataFrame.from_records(price_records)
        price_df['start'] = price_df['start'].dt.tz_convert('US/Pacific').dt.tz_localize(None)
        price_df['day_of_week'] = price_df['start'].dt.weekday

        # price_df_sub = price_df.loc[(price_df['node'] == 'GLENWOOD_6_N005') & (price_df['price'] <= 1000)]
        # price_df_sub.plot('start', 'price')
        # plt.show()

        n_charge_intervals = 21
        interval = 5
        start_hour = 19
        usual_charge_start = time(start_hour, 0)
        usual_charge_end = time(start_hour + int(n_charge_intervals / 12), (n_charge_intervals % 12) * interval)

        price_df['time'] = price_df['start'].dt.time
        price_df['is_usual_charging'] = (price_df['time'] >= usual_charge_start) & \
                                        (price_df['time'] < usual_charge_end) & \
                                        (price_df['day_of_week'] <= 4)

        ideal_charge_start = time(start_hour, 0)
        ideal_charge_end = time(start_hour + 10 - 24, 0)
        price_df['is_charge_period'] = ((price_df['time'] >= ideal_charge_start) &
                                        price_df['day_of_week'].isin([6, 0, 1, 2, 3])) | \
                                       ((price_df['time'] < ideal_charge_end) &
                                        (price_df['day_of_week'] < 4))
        price_df['date'] = price_df['start'].dt.date
        price_df['price_rank_for_charge'] = price_df.groupby(['date', 'node', 'is_charge_period'])['price'].rank(
            ascending=True)
        price_df['is_ideal_charging'] = price_df['is_charge_period'] & (price_df['price_rank_for_charge'] <= 24)

        charger_power = 11.5  # kW
        consumption_per_interval = charger_power * interval / 60

        price_df['usual_cost'] = price_df['is_usual_charging'] * price_df['price'] * consumption_per_interval / 1000
        price_df['ideal_cost'] = price_df['is_ideal_charging'] * price_df['price'] * consumption_per_interval / 1000

        print('Energy cost savings per car per year:')
        print(price_df.groupby(['node'])[['usual_cost', 'ideal_cost']].sum())

        price_df_1d = price_df[(price_df['date'] == datetime(2016, 2, 4).date()) & (price_df['node'] == 'MENLO_6_N004')]
        price_df_1d['hour'] = price_df_1d['start'].dt.hour + (price_df_1d['start'].dt.minute / 60)
        # plt.bar(price_df_1d['hour'], price_df_1d['is_usual_charging'])
        # plt.bar(price_df_1d['hour'], price_df_1d['is_ideal_charging'])
        # plt.show()

        price_df['price_rank'] = price_df.groupby(['date', 'node'])['price'].rank(ascending=False)
        price_df['price_pct'] = price_df.groupby(['date', 'node'])['price'].rank(ascending=True, pct=True)
        peak_pct = 0.9
        trough_pct = 0.1
        price_df['is_peak'] = np.where(price_df['price_pct'] > peak_pct, 1, 0)
        price_df['is_trough'] = np.where(price_df['price_pct'] < trough_pct, 1, 0)

        price_df_sub = price_df[(price_df['day_of_week'] < 5) & (price_df['node'] == 'MENLO_6_N004')][
            ['node', 'time', 'price_rank', 'is_peak', 'is_trough', 'is_ideal_charging', 'price']]
        summary_df = price_df_sub.groupby(['time'])
        # peaks_and_troughs = summary_df['is_peak', 'is_trough', 'is_ideal_charging'].sum().reset_index()
        # plt.plot(peaks_and_troughs['time'], peaks_and_troughs['is_peak'])
        # plt.plot(peaks_and_troughs['time'], peaks_and_troughs['is_ideal_charging'])
        # plt.show()

        price_df_sub2 = price_df[(price_df['day_of_week'] < 5)][
            ['node', 'time', 'price']]
        summary_df = price_df_sub2.groupby(['time', 'node']).agg(['mean', 'max', 'min']).reset_index()
        summary_df.to_csv('../summary.csv')
        # for node in nodes:
        #     plt.plot(summary_df[summary_df['node'] == node]['time'],
        #              summary_df[summary_df['node'] == node]['price']['mean'])
        # plt.plot(summary_df['time'], summary_df['price']['max'])
        # plt.plot(summary_df['time'], summary_df['price']['min'])
        # plt.show()
