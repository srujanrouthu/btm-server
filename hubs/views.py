# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def charging_pattern(request):

    return Response({'test': 'this is a test'})
