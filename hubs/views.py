# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime, timedelta
import pytz
import pandas as pd

from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from django.utils.timezone import make_aware

from .models import Device, Override
from iso.models import Node


@api_view(['POST'])
@authentication_classes((JSONWebTokenAuthentication, SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def override(request):
    # TODO: Write check if device belongs to the person requesting
    # TODO: Write exception checks

    device = Device.objects.get(id=request.data['device_id'])
    o = Override.objects.create(device=device, at_required=request.data['at_requested'])

    return Response({'device': device.id, 'override': o.at_required})


@api_view(['POST'])
@authentication_classes((JSONWebTokenAuthentication, SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def update_range_state(request):
    # TODO: Write check if device belongs to the person requesting
    # TODO: Write exception checks

    device = Device.objects.get(id=request.data['device_id'])
    device.in_range = request.data['range_state'] == 'in_range'
    device.save()

    return Response({'device': device.id, 'in_range': device.in_range})


@api_view(['POST'])
@authentication_classes((JSONWebTokenAuthentication, SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def charge_pattern(request):
    device = Device.objects.get(id=request.data['device_id'])

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

    duration = time_required(request.data['battery_level'])
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
    no_intervals = int(period_duration / 5)\

    price_records = node.prices.filter(start__gte=period_start, start__lt=period_end) \
        .order_by('start') \
        .values('start', 'end', 'prediction')
    price_df = pd.DataFrame.from_records(price_records)

    if no_intervals <= no_charge_intervals:
        price_df['is_ideal_charging'] = True
    else:
        if len(price_records) <= no_charge_intervals:
            price_df['is_ideal_charging'] = True
        else:
            price_df['is_charging_period'] = (price_df['start'] >= period_start) & (
                    price_df['start'] < period_end)
            price_df['price_rank'] = price_df.groupby(['is_charging_period'])['prediction'].rank(ascending=True)

            price_df['is_ideal_charging'] = price_df['is_charging_period'] & (
                    price_df['price_rank'] <= no_charge_intervals)

    aware_now = period_start + timedelta(minutes=5)

    if len(price_df.index) > 0:
        sub_df = price_df.loc[(price_df['start'] <= aware_now) | (price_df['end'] > aware_now), ]
        sub_df['start'] = sub_df['start'].dt.tz_convert('US/Pacific')
        sub_df['end'] = sub_df['end'].dt.tz_convert('US/Pacific')

        sub_json = sub_df[['start', 'end', 'is_ideal_charging']].to_dict(orient='records')
    else:
        sub_json = []

    return Response(sub_json)
