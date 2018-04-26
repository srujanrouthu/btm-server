"""
    Management function to predict prices using regression model for next 24 hours.
    Should be run every day after 00:00 GMT, after running extract.
"""


import math
# import pytz
import pandas as pd
from datetime import timedelta  # , datetime
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt

from django.core.management.base import BaseCommand
# from django.utils.timezone import make_aware

from iso.models import Price, Node

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
        nodes = Node.objects.all()
        for node in nodes:
            latest = Price.objects.latest('start')
            end = latest.end
            start = end - timedelta(days=60)
            # end_raw = datetime.now()
            # end_hour = datetime(end_raw.year, end_raw.month, end_raw.day)
            # end = make_aware(end_hour, pytz.timezone('America/Los_Angeles'))
            # start = make_aware(end_hour - timedelta(days=60), pytz.timezone('America/Los_Angeles'))
            price_records = Price.objects.filter(start__gte=start, start__lt=end, node=node) \
                .order_by('start') \
                .values('start', 'price')
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

            model = smf.ols(formula='ln_price ~ time_of_day + day_of_week', missing='drop', data=reg_df).fit()

            new_start = price_records.reverse()[0]['start'] + timedelta(minutes=5)
            starts = []
            e = new_start + timedelta(days=1)
            while new_start < e:
                starts.append(new_start)
                new_start += timedelta(minutes=5)
            new_df = pd.DataFrame(data=None, columns=price_df.columns)
            new_df['start'] = starts
            new_df['day_of_week'] = new_df['start'].dt.weekday
            new_df['time_of_day'] = new_df['start'].dt.time
            new_df['norm_prediction'] = model.predict(new_df)
            new_df['prediction'] = new_df['norm_prediction'].apply(math.exp) - abs(min(reg_df['price'])) - 0.01

            # len1 = len(list(reg_df['price'])[-1000:])
            # len2 = len(list(new_df['prediction']))
            # plot_results([None] * len1 + list(new_df['prediction']), list(reg_df['price'])[-1000:] + [None] * len2)

            new_df['start'] = new_df['start'].dt.tz_convert('GMT')

            new_data = new_df.to_dict('records')
            new_records = []
            for d in new_data:
                new_records.append(Price(
                    start=d['start'],
                    end=d['start'] + timedelta(minutes=5),
                    node=node,
                    prediction=d['prediction']
                ))
            Price.objects.bulk_create(new_records)
