import urllib
import csv
from xml.etree import ElementTree
from zipfile import ZipFile


from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        start = '20170101T00:00-0000'
        end = '20170102T23:59-0000'
        market_run_id = 'RTM'

        active_day = start

        base_url = "http://oasis.caiso.com/oasisapi/SingleZip?"

        url = base_url \
            + 'queryname=PRC_INTVL_LMP' \
            + '&startdatetime=' + active_day \
            + '&enddatetime=' + end \
            + '&market_run_id=' + market_run_id \
            + '&grp_type=ALL_APNODES' \
            + '&version=1'

        file_name = '%s.zip' % start
        urllib.urlretrieve(url, file_name)
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
            keys = rows[0].keys()
            with open('%s.csv' % start, 'wd') as f:
                dict_writer = csv.DictWriter(f, keys)
                dict_writer.writeheader()
                dict_writer.writerows(rows)
