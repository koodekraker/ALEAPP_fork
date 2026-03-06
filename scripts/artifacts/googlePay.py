# Google Pay (GMS)
# Author:  Koo de Kraker
# Date 2026-03-06
# Version: 0.3
# Note:  This module parses the Google Pay database found in com.google.android.gms/databases

import blackboxprotobuf

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, open_sqlite_db_readonly

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
            
            # Add explanation and assumptions to the report
            description = (
                'This module parses the <code>GpfeTransactions</code> table from the Google Pay SQLite database '
                'located at <code>com.google.android.gms/databases/pay</code>.<br><br>'
                '<b>Amount interpretation (field 3 of transaction_proto):</b><br>'
                '<ul>'
                '<li><b>Field 3.1 (Currency):</b> ISO 4217 currency code (e.g. EUR, USD).</li>'
                '<li><b>Field 3.2 (Whole):</b> The whole currency unit part of the amount (e.g. 6 for €6,50).</li>'
                '<li><b>Field 3.3 (Decimal):</b> Optional field representing the fractional part. '
                'The length of this value is variable. The 3 leftmost digits are taken, divided by 10 and rounded '
                'to obtain the number of cents (0-99).<br>'
                'Examples: <code>499999</code> → "499" → 49.9 → 50 cents &nbsp;|&nbsp; '
                '<code>5000000</code> → "500" → 50.0 → 50 cents</li>'
                '</ul>'
                '<b>Note:</b> The decimal field interpretation is based on observed data and may not cover all cases. '
                'Always verify the <i>Whole</i> and <i>Decimal</i> raw columns when in doubt.<br><br>'
            )
            report.write_minor_header('Module Description & Assumptions', 'h5')
            report.write_raw_html(description)
            
            data_headers = ('Timestamp', 'Amount (interpreted)', 'Merchant', 'Transaction ID', 'Currency', 'Whole', 'Decimal')
            data_list = []
            for row in all_rows:
                timestamp  = row[0]
                proto_blob = row[1]
                currency, whole, decimal, transaction_id, merchant = parse_transaction_proto(proto_blob)
                amount = format_amount(currency, whole, decimal)
                data_list.append((timestamp, amount, merchant, transaction_id, currency, whole, decimal))

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
        ('*/data/data/com.google.android.gms/databases/pay',),
        get_googlePayGMS)
}
