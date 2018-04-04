# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals


import couchdb
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def charging_pattern(request):
    couch = couchdb.Server('https://admin:f3f28f363581@couchdb-597ada.smileupps.com')
    db = couch['overrides']
    for row in db.view('_all_docs', include_docs=True):
        print(row.id, row.doc)
    # Call AI process
    return Response({'charge': True})
