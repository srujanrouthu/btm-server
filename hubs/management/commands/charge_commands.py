"""
    Management function to issue commands to devices to charge or not.
    Should be run every day after 00:00 GMT.
"""

from datetime import datetime, timedelta
import pytz
import pandas as pd
import requests

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from hubs.models import Device
from iso.models import Node


ENVIRONMENT = 'production'

# TODO: Need to move to config file; to be done once code is hosted on EC2
if ENVIRONMENT == 'production':
    TESLA_API = 'https://btm-ev.herokuapp.com/'
else:
    TESLA_API = 'http://127.0.0.1:5002/'


class Command(BaseCommand):
    def handle(self, *args, **options):
        devices = Device.objects.filter(in_range=True)
        for device in devices:
            def closest_node(loc):
                nodes = Node.objects.all()
                # TODO: Need to calculate closest node; before that fetch node locations
                return nodes[0]

            def inverse_charge(level):
                # TODO: Rough approximation; needs more research and regression
                # TODO: Machine learning can help battery charging patterns of a particular device
                return 300 * ((float(level) / 100) ** 2)

            def time_required(level):
                max_level = 80  # TODO: Should come from user; should be able to override
                return inverse_charge(max_level) - inverse_charge(level)

            now = datetime.now() - timedelta(minutes=5)
            period_start = make_aware(now, pytz.timezone('GMT'))  # Can also use django's default timezone
            overrides = device.overrides.filter(at_required__gt=period_start)

            location = {
                'latitude': device.hub.latitude,
                'longitude': device.hub.longitude
            }
            node = closest_node(location)

            # TODO: Need to authenticate with Tesla API before request;
            charge_state_response = requests.get(TESLA_API + 'charge_state')
            charge_state = charge_state_response.json()
            duration = time_required(charge_state['battery_level'])
            no_charge_intervals = int(duration / 5)

            if not overrides:
                if period_start.hour >= 12:
                    end_time = period_start + timedelta(days=1)
                else:
                    end_time = period_start
                # TODO: Need to use the at_default_idle_end field of device; making time field aware is non-trivial
                period_end = make_aware(datetime(end_time.year, end_time.month, end_time.day, 6),
                                        pytz.timezone('US/Pacific'))
            else:
                period_end = overrides.latest('at_required').at_required

            period_duration = (period_end - period_start).seconds / 60
            no_intervals = int(period_duration / 5)

            if no_intervals <= no_charge_intervals:
                command = 'charge_start'
            else:
                price_records = node.prices.filter(start__gte=period_start, start__lt=period_end) \
                    .order_by('start') \
                    .values('start', 'end', 'prediction')
                if len(price_records) <= no_charge_intervals:
                    command = 'charge_start'
                else:
                    price_df = pd.DataFrame.from_records(price_records)

                    price_df['is_charging_period'] = (price_df['start'] >= period_start) & (
                                price_df['start'] < period_end)
                    price_df['price_rank'] = price_df.groupby(['is_charging_period'])['prediction'].rank(ascending=True)

                    price_df['is_ideal_charging'] = price_df['is_charging_period'] & (
                                price_df['price_rank'] <= no_charge_intervals)

                    aware_now = period_start + timedelta(minutes=5)
                    sub_df = price_df.loc[(price_df['start'] <= aware_now) & (price_df['end'] > aware_now),]

                    command = 'charge_start' if sub_df['is_ideal_charging'][0] is True else 'charge_stop'

            requests.get(TESLA_API + command)
            print('Issued %s command to %s' % (command, device.name))
        print('Issued commands to %s devices' % devices.count())
