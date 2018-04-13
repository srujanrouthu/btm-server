import pytz
import pandas as pd
from datetime import datetime, time, timedelta
import matplotlib.pyplot as plt

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from iso.models import Price


class Command(BaseCommand):
    def handle(self, *args, **options):
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
        start_hour = 20
        usual_charge_start = time(start_hour, 0)
        usual_charge_end = time(start_hour + int(n_charge_intervals / 12), (n_charge_intervals % 12) * interval)

        price_df['is_usual_charging'] = (price_df['start'].dt.time >= usual_charge_start) & \
                                  (price_df['start'].dt.time < usual_charge_end) & \
                                  (price_df['day_of_week'] <= 4)

        ideal_charge_start = time(start_hour, 0)
        ideal_charge_end = time(start_hour + 10 - 24, 0)
        price_df['is_charge_period'] = ((price_df['start'].dt.time >= ideal_charge_start) &
                                        price_df['day_of_week'].isin([6, 0, 1, 2, 3])) | \
                                       ((price_df['start'].dt.time < ideal_charge_end) &
                                        (price_df['day_of_week'] < 4))
        price_df['date'] = price_df['start'].dt.date
        price_df['price_rank'] = price_df.groupby(['date', 'node', 'is_charge_period'])['price'].rank(ascending=True)
        price_df['is_ideal_charging'] = price_df['is_charge_period'] & (price_df['price_rank'] <= 24)

        charger_power = 11.5    # kW
        consumption_per_interval = charger_power * interval / 60

        price_df['usual_cost'] = price_df['is_usual_charging'] * price_df['price'] * consumption_per_interval / 1000
        price_df['ideal_cost'] = price_df['is_ideal_charging'] * price_df['price'] * consumption_per_interval / 1000

        # price_df.to_csv('../prices.csv')

        # print(price_df)
        print(price_df.groupby(['node'])[['usual_cost', 'ideal_cost']].sum())
