import os
import logging
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

# Configuration
PROPERTY_ID = os.getenv('PROPERTY_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
COUNTRIES_TO_MONITOR = ['United States', 'United Kingdom', 'Canada', 'Nigeria']

def setup_analytics_client():
    logger.debug("Setting up analytics client")
    logger.debug(f"Looking for credentials file in: {os.getcwd()}")
    credentials = service_account.Credentials.from_service_account_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/analytics.readonly']
    )
    return BetaAnalyticsDataClient(credentials=credentials)

def get_visitors():
    logger.debug("Getting visitors data")
    client = setup_analytics_client()
    request = RunRealtimeReportRequest(
        property=PROPERTY_ID,
        dimensions=[Dimension(name="country")],
        metrics=[Metric(name="activeUsers")]
    )
    return client.run_realtime_report(request)

def process_data(report):
    logger.debug("Processing visitor data")
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

def send_notification(visitor_data):
    logger.debug("Sending notifications")
    if not visitor_data:
        message = f"📊 No active visitors from monitored countries at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        logger.debug(f"Sending message: {message}")
        send_telegram_message(message)
    else:
        for country, count in visitor_data.items():
            if count > 0:
                message = f"🌍 {count} active visitor(s) from {country} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                logger.debug(f"Sending message: {message}")
                send_telegram_message(message)

def main():
    try:
        logger.debug("Starting analytics monitor")
        report = get_visitors()
        current_visitors = process_data(report)
        send_notification(current_visitors)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        # Send error notification to Telegram
        send_telegram_message(f"❌ Error in analytics monitor: {str(e)}")

if __name__ == "__main__":
    main()
