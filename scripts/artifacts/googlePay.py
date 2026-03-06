# Google Pay (GMS)
# Author:  Koo de Kraker (josh@thebinaryhick.blog)
# Date 2026-03-06
# Version: 0.1
# Note:  This module only parses the Google pay database found in com.google.android.gms/databases

import os
import sqlite3
import textwrap

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, is_platform_windows, open_sqlite_db_readonly

def get_googlePayGMS(files_found, report_folder, seeker, wrap_text, time_offset):
    for file_found in files_found:
        file_found = str(file_found)
        if file_found.endswith('pay'):
            break # Skip all other files
        
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()

    cursor.execute('''
        SELECT
            datetime(timestamp_ms / 1000, 'unixepoch') AS "Timestamp"
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
        data_headers = ('Timestamp',)
        data_list = []
        for row in all_rows:
            data_list.append((row[0],))
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
                ('*'),
                get_googlePayGMS)
}