import os
import logging
import base64
import json
import requests
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunRealtimeReportRequest,
    Dimension,
    Metric
)
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PROPERTY_ID = os.getenv('PROPERTY_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')
COUNTRIES_TO_MONITOR = ['United States', 'United Kingdom', 'Canada', 'Nigeria']

def setup_analytics_client():
    credentials_info = json.loads(base64.b64decode(GOOGLE_CREDENTIALS))
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=['https://www.googleapis.com/auth/analytics.readonly']
    )
    return BetaAnalyticsDataClient(credentials=credentials)

def get_visitors():
    client = setup_analytics_client()
    request = RunRealtimeReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="country")],
        metrics=[Metric(name="activeUsers")]
    )
    return client.run_realtime_report(request)

def process_data(report):
    visitors = {}
    for row in report.rows:
        country = row.dimension_values[0].value
        visitors[country] = int(row.metric_values[0].value)
    filtered = {k: v for k, v in visitors.items() if k in COUNTRIES_TO_MONITOR}
    logger.debug(f"Filtered visitor data: {filtered}")
    return filtered

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=data)
    if response.status_code != 200:
        logger.error(f"Failed to send Telegram message: {response.text}")
    return response.status_code == 200

def main():
    try:
        logger.debug("Starting analytics monitor")
        report = get_visitors()
        current_visitors = process_data(report)
        if not current_visitors:
            message = f"📊 No active visitors from monitored countries at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            send_telegram_message(message)
        else:
            for country, count in current_visitors.items():
                if count > 0:
                    message = f"🌍 {count} active visitor(s) from {country} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    send_telegram_message(message)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        send_telegram_message(f"❌ Error in analytics monitor: {str(e)}")

if __name__ == "__main__":
    main()
