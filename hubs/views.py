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

from iso.models import Node
from .models import Device, Override


@api_view(['POST'])
@authentication_classes((JSONWebTokenAuthentication, SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def charge(request):
    # TODO: Write check if device belongs to the person requesting

    def closest_node(loc):
        nodes = Node.objects.all()
        # TODO: Need to calculate closest node; before that fetch node locations
        return nodes[0]

    def inverse_charge(level):
        # TODO: Rough approximation; needs more research and regression
        # TODO: Machine learning can help battery charging patterns of a particular device
        return 300 * ((level / 100) ** 2)

    def time_required(level):
        max_level = 80  # TODO: Should come from user; should be able to override
        return inverse_charge(max_level) - inverse_charge(level)

    device = Device.objects.get(id=request.data['device_id'])
    now = datetime.now() - timedelta(minutes=5)
    period_start = make_aware(now, pytz.timezone('GMT'))    # Can also use django's default timezone
    overrides = device.overrides.filter(at_required__gt=period_start)

    location = {
        'latitude': device.hub.latitude,
        'longitude': device.hub.longitude
    }
    node = closest_node(location)

    current = request.data['current_level']
    duration = time_required(current)

    if not overrides:
        if period_start.hour >= 12:
            end_time = period_start + timedelta(days=1)
        else:
            end_time = period_start
        # TODO: Need to use the at_default_idle_end field of device; making time field aware is non-trivial
        period_end = make_aware(datetime(end_time.year, end_time.month, end_time.day, 6), pytz.timezone('US/Pacific'))
    else:
        period_end = overrides.latest('at_required').at_required

    period_duration = (period_end - period_start).seconds / 60

    if period_duration < duration:
        return Response({'charge': True})

    price_records = node.prices.filter(start__gte=period_start, start__lt=period_end) \
        .order_by('start') \
        .values('start', 'end', 'prediction')
    price_df = pd.DataFrame.from_records(price_records)

    price_df['is_charging_period'] = (price_df['start'] >= period_start) & (price_df['start'] < period_end)
    price_df['price_rank'] = price_df.groupby(['is_charging_period'])['prediction'].rank(ascending=True)

    no_intervals = int(period_duration / 5)
    price_df['is_ideal_charging'] = price_df['is_charging_period'] & (price_df['price_rank'] <= no_intervals)

    aware_now = period_start + timedelta(minutes=5)
    sub_df = price_df.loc[(price_df['start'] <= aware_now) & (price_df['end'] > aware_now), ]

    return Response({'charge': sub_df['is_ideal_charging'][0]})


@api_view(['POST'])
@authentication_classes((JSONWebTokenAuthentication, SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def override(request):
    # TODO: Write check if device belongs to the person requesting
    # TODO: Write exception checks

    device = Device.objects.get(id=request.body['device_id'])
    o = Override.objects.create(device=device, at_required=request.body['at_requested'])

    return Response({'device': device.id, 'override': o.at_requested})
