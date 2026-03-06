# Google Pay (GMS)
# Author:  Koo de Kraker
# Date 2026-03-06
# Version: 0.4
# Note:  This module parses the Google Pay database found in com.google.android.gms/databases
#        and enriches transactions with account email from com.google.android.apps.walletnfcrel

import os
import json
import sqlite3
import xml.etree.ElementTree as ET
import blackboxprotobuf

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, open_sqlite_db_readonly


def parse_account_map(files_found):
    account_map = {}
    for f in files_found:
        f = str(f)
        if f.endswith('global_prefs.xml'):
            logfunc(f'Google Pay - global_prefs.xml gevonden: {f}')
            try:
                tree = ET.parse(f)
                root = tree.getroot()
                logfunc(f'Google Pay - XML root tag: {root.tag}, children: {[c.tag for c in root]}')
                for elem in root.iter():
                    logfunc(f'Google Pay - XML element: tag={elem.tag}, name={elem.get("name")}, text={str(elem.text)[:80]}')
                    if elem.get('name') == 'accounts':
                        accounts_json = elem.text
                        logfunc(f'Google Pay - accounts JSON raw: {str(accounts_json)[:200]}')
                        accounts = json.loads(accounts_json)
                        for account in accounts:
                            acc_id = str(account.get('id', ''))
                            acc_email = account.get('name', '')
                            logfunc(f'Google Pay - account gevonden: id={acc_id}, email={acc_email}')
                            account_map[acc_id] = acc_email
            except Exception as e:
                logfunc(f'Google Pay - failed to parse global_prefs.xml: {e}')
            break
    logfunc(f'Google Pay - account_map resultaat: {account_map}')
    return account_map



def parse_transaction_proto(blob):
    # Interpretation based on observed data:
    # Field 3.1 = currency, 3.2 = whole amount, 3.3 = decimal amount (optional)
    # Field 7    = transaction ID
    # Field 8    = merchant name
    try:
        message, _ = blackboxprotobuf.decode_message(blob)
        field3 = message.get('3', {})
        currency       = field3.get('1', b'').decode('utf-8') if isinstance(field3.get('1'), bytes) else str(field3.get('1', ''))
        whole          = field3.get('2', '')
        decimal        = field3.get('3', '')
        transaction_id = message.get('7', b'').decode('utf-8') if isinstance(message.get('7'), bytes) else str(message.get('7', ''))
        merchant       = message.get('8', b'').decode('utf-8') if isinstance(message.get('8'), bytes) else str(message.get('8', ''))
        return currency, whole, decimal, transaction_id, merchant
    except Exception as e:
        return '', '', '', '', ''


def format_amount(currency, whole, decimal):
    # Interpretation of the 'decimal' protobuf field (field 3.3):
    # The field length is variable, but the 3 leftmost digits always represent
    # a value between 0-999. Dividing by 10 and rounding gives cents (0-99).
    # Examples: 499999 -> "499" -> 49.9 -> 50 cents
    #           5000000 -> "500" -> 50.0 -> 50 cents
    # The 'whole' field (3.2) represents the full currency units (e.g. euros).
    # Note: these are assumptions based on observed data and may need revision.
    try:
        whole_int = int(whole) if whole != '' else 0
        if decimal != '':
            decimal_str = str(int(decimal))
            left3 = int(decimal_str[:3])
            cents = round(left3 / 10)
            amount = whole_int + (cents / 100)
            return f'{currency} {amount:.2f}'
        else:
            return f'{currency} {whole_int:.2f}'
    except Exception:
        return ''


def get_googlePayGMS(files_found, report_folder, seeker, wrap_text, time_offset):

    # Build account_id -> email map from global_prefs.xml
    account_map = parse_account_map(files_found)

    for file_found in files_found:
        file_found = str(file_found)
        if not file_found.endswith('pay'):
            continue

        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()

        cursor.execute('''
            SELECT
                datetime(timestamp_ms / 1000, 'unixepoch') AS "Timestamp",
                account_id,
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

            data_headers = ('Timestamp', 'Amount (interpreted)', 'Merchant', 'Account Email', 'Transaction ID', 'Currency', 'Whole', 'Decimal')
            data_list = []
            for row in all_rows:
                timestamp   = row[0]
                account_id  = str(row[1]) if row[1] else ''
                proto_blob  = row[2]
                currency, whole, decimal, transaction_id, merchant = parse_transaction_proto(proto_blob)
                amount      = format_amount(currency, whole, decimal)
                email = account_map.get(account_id, account_id)
                logfunc(f'Google Pay - account_id uit DB: "{account_id}", gevonden email: "{email}"')   
                data_list.append((timestamp, amount, merchant, email, transaction_id, currency, whole, decimal))

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
        ('*/data/data/com.google.android.gms/databases/pay',
         '*/data/data/com.google.android.apps.walletnfcrel/shared_prefs/global_prefs.xml'),
        get_googlePayGMS)
}
