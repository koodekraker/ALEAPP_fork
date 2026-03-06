# Google Pay (GMS)
# Author:  Koo de Kraker
# Date 2026-03-06
# Version: 0.2
# Note:  This module parses the Google Pay database found in com.google.android.gms/databases

import os
import sqlite3
import blackboxprotobuf

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, open_sqlite_db_readonly


def parse_transaction_proto(blob):
    try:
        message, _ = blackboxprotobuf.decode_message(blob)
        field3 = message.get('3', {})
        currency  = field3.get('1', b'').decode('utf-8') if isinstance(field3.get('1'), bytes) else str(field3.get('1', ''))
        whole  = field3.get('2', '')
        decimal  = field3.get('3', '')

        return currency, whole, decimal
    except Exception as e:
        return '', '', ''


def get_googlePayGMS(files_found, report_folder, seeker, wrap_text, time_offset):
    for file_found in files_found:
        file_found = str(file_found)
        if not file_found.endswith('pay'):
            continue

        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()

        cursor.execute('''
            SELECT
                datetime(timestamp_ms / 1000, 'unixepoch') AS "Timestamp",
                transaction_proto
            FROM
                GpfeTransactions
            ORDER BY timestamp_ms ASC
        ''')

        all_rows = cursor.fetchall()
        usageentries = len(all_rows)

        if usageentries > 0:
            report = ArtifactHtmlReport('Google Pay (GMS)')
            report.start_artifact_report(report_folder, 'Transactions')
            report.add_script()
            data_headers = ('Timestamp', 'Currency', 'Whole', 'Decimal')
            data_list = []
            for row in all_rows:
                timestamp = row[0]
                proto_blob = row[1]
                currency, whole, decimal = parse_transaction_proto(proto_blob)
                data_list.append((timestamp, currency, whole, decimal))

            report.write_artifact_data_table(data_headers, data_list, file_found)
            report.end_artifact_report()

            tsvname = 'Google Pay (GMS) - Transactions'
            tsv(report_folder, data_headers, data_list, tsvname)

            tlactivity = 'Google Pay (GMS) - Transactions'
            timeline(report_folder, tlactivity, data_list, data_headers)
        else:
            logfunc('No Google Pay (GMS) - Transactions data available')

        db.close()


__artifacts__ = {
    "GooglePayGMS": (
        "Google Pay (GMS)",
        ('*',),
        get_googlePayGMS)
}
