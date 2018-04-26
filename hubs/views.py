# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import Device, Override


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
