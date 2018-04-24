"""
    Management function to extract prices from ISO API.
    Should be run every day after 00:00 GMT.
"""


import os
from urllib.request import urlretrieve
from xml.etree import ElementTree
from zipfile import ZipFile
# from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from iso.models import Price, Node


class Command(BaseCommand):
    def handle(self, *args, **options):
        nodes = Node.objects.all()

        for node in nodes[0:1]:
            empty_records = Price.objects.filter(node=node, price__isnull=True).order_by('start')
            start_time = empty_records[0].start
            end_time = empty_records.reverse()[0].start
            # end_time = datetime(2018, 4, 24) - timedelta(days=30)
            # start_time = end_time - timedelta(days=30)
            start = start_time.strftime('%Y%m%dT%H:%M') + '-0000'
            end = end_time.strftime('%Y%m%dT%H:%M') + '-0000'

            market_run_id = 'RTM'

            base_url = "http://oasis.caiso.com/oasisapi/SingleZip?"

            url = base_url \
                + 'queryname=PRC_INTVL_LMP' \
                + '&startdatetime=' + start \
                + '&enddatetime=' + end \
                + '&market_run_id=' + market_run_id \
                + '&node=' + node.node \
                + '&version=1'

            print(start, end, url)

            file_name = '../%s.zip' % start
            urlretrieve(url, file_name)
            rows = []
            with ZipFile(file_name, 'r') as z:
                xml_name = z.namelist()[0]
                with z.open(xml_name) as f:
                    root = ElementTree.fromstring(f.read())
                    try:
                        items = root[1][0]
                        for item in items:
                            if len(item) > 1:
                                header = {}
                                for head in item:
                                    row = {}
                                    head_tag = head.tag.replace('{http://www.caiso.com/soa/OASISReport_v1.xsd}', '')
                                    for data in head:
                                        data_tag = data.tag.replace('{http://www.caiso.com/soa/OASISReport_v1.xsd}', '')
                                        if head_tag == 'REPORT_HEADER':
                                            header['HEAD_%s' % data_tag] = data.text
                                        else:
                                            row['DATA_%s' % data_tag] = data.text
                                    if head_tag != 'REPORT_HEADER':
                                        row.update(header)
                                        rows.append(row)
                    except Exception as e:
                        print(e)
            if len(rows) > 0:
                rows = list(filter(lambda d: d['DATA_DATA_ITEM'] == 'LMP_PRC', rows))
                keep = ['DATA_INTERVAL_START_GMT', 'DATA_INTERVAL_END_GMT', 'DATA_RESOURCE_NAME', 'DATA_VALUE']
                rows = [{k: v for k, v in r.items() if k in keep} for r in rows]
                for price in empty_records:
                    value = None
                    for r in rows:
                        if r['DATA_INTERVAL_START_GMT'] == price.start.strftime('%Y-%m-%dT%H:%M:%S') + '-00:00':
                            value = r['DATA_VALUE']
                            break
                    # TODO: Need to find a way to bulk update
                    if value is not None:
                        price.price = value
                        price.save()
            os.remove(file_name)
