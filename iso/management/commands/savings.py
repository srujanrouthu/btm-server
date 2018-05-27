import pandas as pd
from datetime import datetime, timedelta
from random import normalvariate

from django.core.management.base import BaseCommand

from iso.models import Price, Node


def inverse_charge(level):
    # TODO: Rough approximation; needs more research and regression
    # TODO: Machine learning can help battery charging patterns of a particular device
    return 300 * ((float(level) / 100) ** 2)


def time_required(level):
    max_level = 80  # TODO: Should come from user; should be able to override
    return inverse_charge(max_level) - inverse_charge(level)


charger_power = 11.5  # kW
consumption_per_interval = charger_power * 5 / 60


class Command(BaseCommand):
    def handle(self, *args, **options):
        prices = []
        nodes = Node.objects.all()
        for node in nodes:
            records = Price.objects.filter(node=node, price__isnull=False, prediction__isnull=False) \
                .order_by('start') \
                .values('start', 'price', 'prediction')
            price_df = pd.DataFrame.from_records(records)

            upper = price_df['price'].quantile(0.95)
            lower = price_df['price'].quantile(0.05)
            price_df.loc[price_df['price'] > upper, 'price'] = upper
            price_df.loc[price_df['price'] < lower, 'price'] = lower

            price_df['start'] = price_df['start'].dt.tz_convert('US/Pacific').dt.tz_localize(None)
            price_df['date'] = price_df['start'].dt.date
            price_df['day_of_week'] = price_df['start'].dt.weekday
            price_df = price_df[price_df['day_of_week'] <= 4]
            dates = list(set(price_df['date']))

            for date in dates:
                battery_level = min(normalvariate(50, 5), 90)
                # arrival_time = datetime(date.year, date.month, date.day, 19) + timedelta(minutes=normalvariate(0, 20))
                arrival_time = datetime(date.year, date.month, date.day, 19)
                # charge_end = datetime(date.year, date.month, date.day, 6)

                sub_df = price_df[price_df['date'] == date].copy()
                # sub_df['is_charge_period'] = (sub_df['start'] >= arrival_time) | (sub_df['start'] < charge_end)
                sub_df['is_charge_period'] = ~sub_df['start'].dt.hour.isin([7, 8, 17, 18])
                sub_df['is_evening'] = sub_df['start'] >= arrival_time
                required = time_required(battery_level)
                no_intervals = 1 + int(required / 5)

                sub_df['time_rank'] = sub_df.groupby(['is_evening'])['start'].rank(ascending=True)
                sub_df['price_rank'] = sub_df.groupby(['is_charge_period'])['price'].rank(ascending=True)
                sub_df['prediction_rank'] = sub_df.groupby(['is_charge_period'])['prediction'].rank(ascending=True)

                sub_df['is_usual_charge'] = sub_df['is_evening'] & (sub_df['time_rank'] <= no_intervals)
                sub_df['is_ideal_charge'] = sub_df['is_charge_period'] & (sub_df['price_rank'] <= no_intervals)
                sub_df['is_prediction_charge'] = sub_df['is_charge_period'] & (
                            sub_df['prediction_rank'] <= no_intervals)

                sub_df['usual_pay'] = sub_df['price'] * sub_df['is_usual_charge'] * consumption_per_interval / 1000
                sub_df['ideal_pay'] = sub_df['price'] * sub_df['is_ideal_charge'] * consumption_per_interval / 1000
                sub_df['prediction_pay'] = sub_df['price'] * sub_df[
                    'is_prediction_charge'] * consumption_per_interval / 1000

                prices.append({
                    'usual_pay': sum(sub_df['usual_pay']),
                    'ideal_pay': sum(sub_df['ideal_pay']),
                    'prediction_pay': sum(sub_df['prediction_pay']),
                })

        usuals = [p['usual_pay'] for p in prices]
        ideals = [p['ideal_pay'] for p in prices]
        predictions = [p['prediction_pay'] for p in prices]

        annual_usual_cost = 250 * sum(usuals) / len(usuals)
        annual_ideal_cost = 250 * sum(ideals) / len(ideals)
        annual_prediction_cost = 250 * sum(predictions) / len(predictions)

        print(annual_usual_cost, annual_ideal_cost, annual_prediction_cost)
