import math
import pytz
import pandas as pd
from datetime import datetime
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from iso.models import Price

pd.options.mode.use_inf_as_na = True


def plot_results(predicted_data, true_data):
    fig = plt.figure(facecolor='white')
    ax = fig.add_subplot(111)
    ax.plot(true_data, label='True Data')
    plt.plot(predicted_data, label='Prediction')
    plt.legend()
    plt.show()


class Command(BaseCommand):
    def handle(self, *args, **options):
        # nodes = ['MENLO_6_N004', 'GLENWOOD_6_N005', 'WOODSIDE_6_N004', 'BLLEHVN_6_N009', 'SARATOGA_2_N011']
        start = make_aware(datetime(2017, 12, 1), pytz.timezone('America/Los_Angeles'))
        end = make_aware(datetime(2018, 1, 1), pytz.timezone('America/Los_Angeles'))
        price_records = Price.objects.filter(start__gte=start, start__lt=end) \
            .order_by('start') \
            .values('start', 'node', 'price')
        price_df = pd.DataFrame.from_records(price_records)
        price_df['start'] = price_df['start'].dt.tz_convert('US/Pacific').dt.tz_localize(None)

        price_df['day_of_week'] = price_df['start'].dt.weekday
        price_df['time_of_day'] = price_df['start'].dt.time

        upper = price_df['price'].quantile(0.95)
        lower = price_df['price'].quantile(0.05)

        price_df.loc[price_df['price'] > upper, 'price'] = upper
        price_df.loc[price_df['price'] < lower, 'price'] = lower

        reg_df = price_df[['price', 'time_of_day', 'day_of_week']].copy()
        reg_df['price_transform'] = reg_df['price'] + abs(min(reg_df['price'])) + 0.01
        reg_df['ln_price'] = reg_df['price_transform'].apply(math.log)
        reg_df['ln_price'] = reg_df['ln_price'].astype(float)
        reg_df['time_of_day'] = reg_df['time_of_day'].astype('category')
        reg_df['day_of_week'] = reg_df['day_of_week'].astype('category')
        print(reg_df.head())

        model = smf.ols(formula='ln_price ~ time_of_day + day_of_week', missing='drop', data=reg_df).fit()
        print(model.summary())
        reg_df['prediction'] = model.predict(reg_df)
        reg_df['price_prediction'] = reg_df['prediction'].apply(math.exp) - abs(min(reg_df['price'])) - 0.01

        plot_results(reg_df['price_prediction'][0:10000], reg_df['price'][0:10000])
