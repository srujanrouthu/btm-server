import os
from urllib.request import urlretrieve
# import csv
from xml.etree import ElementTree
from zipfile import ZipFile
from datetime import timedelta, datetime

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
# from django.utils.timezone import make_aware

from iso.models import Price


class Command(BaseCommand):
    def handle(self, *args, **options):
        nodes = ['MENLO_6_N004', 'GLENWOOD_6_N005', 'WOODSIDE_6_N004', 'BLLEHVN_6_N009', 'SARATOGA_2_N011']
        node = nodes[4]
        try:
            latest = Price.objects.filter(node=node).earliest('start')
            # end_time = make_aware(latest.end)
            end_time = latest.start
        except ObjectDoesNotExist as e:
            print(e)
            # end_time = make_aware(datetime(2018, 3, 21))
            end_time = datetime(2018, 3, 21)
        start_time = end_time - timedelta(days=30)
        end = end_time.strftime('%Y%m%dT%H:%M') + '-0000'
        start = start_time.strftime('%Y%m%dT%H:%M') + '-0000'

        market_run_id = 'RTM'
        active_day = start

        base_url = "http://oasis.caiso.com/oasisapi/SingleZip?"

        url = base_url \
            + 'queryname=PRC_INTVL_LMP' \
            + '&startdatetime=' + active_day \
            + '&enddatetime=' + end \
            + '&market_run_id=' + market_run_id \
            + '&node=' + node \
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
            prices = []
            for row in rows:
                price = Price(
                    start=row['DATA_INTERVAL_START_GMT'],
                    end=row['DATA_INTERVAL_END_GMT'],
                    node=row['DATA_RESOURCE_NAME'],
                    price=row['DATA_VALUE']
                )
                # price = {
                #     'start': row['DATA_INTERVAL_START_GMT'],
                #     'end': row['DATA_INTERVAL_END_GMT'],
                #     'node': row['DATA_RESOURCE_NAME'],
                #     'price': row['DATA_VALUE']
                # }
                prices.append(price)
            # with open('../%s.csv' % start, 'wd') as f:
            #     dict_writer = csv.DictWriter(f, prices[0].keys())
            #     dict_writer.writeheader()
            #     dict_writer.writerows(prices)
            Price.objects.bulk_create(prices)
        os.remove(file_name)
