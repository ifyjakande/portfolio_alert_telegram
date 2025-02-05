import os
import logging
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
import pytz

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PROPERTY_ID = os.getenv('PROPERTY_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')

def setup_analytics_client():
    try:
        credentials_info = json.loads(GOOGLE_CREDENTIALS)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        return BetaAnalyticsDataClient(credentials=credentials)
    except Exception as e:
        logger.error(f"Failed to setup client: {str(e)}")
        raise

def get_analytics_data():
    client = setup_analytics_client()
    request = RunRealtimeReportRequest(
        property=PROPERTY_ID,
        dimensions=[
            Dimension(name="country"),
            Dimension(name="eventName")
        ],
        metrics=[Metric(name="eventCount")]
    )
    return client.run_realtime_report(request)

def process_data(report):
    data = {
        'visitors': {},
        'downloads': {}
    }
    
    for row in report.rows:
        country = row.dimension_values[0].value
        event = row.dimension_values[1].value
        count = int(row.metric_values[0].value)
        
        if event == 'file_download':
            data['downloads'][country] = count
        else:
            data['visitors'][country] = count
            
    logger.debug(f"Processed data: {data}")
    return data

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
        report = get_analytics_data()
        data = process_data(report)
        
        wat = pytz.timezone('Africa/Lagos')
        timestamp = datetime.now(wat).strftime('%Y-%m-%d %I:%M %p')
        
        # Get all unique countries from both visitors and downloads
        all_countries = set(data['visitors'].keys()) | set(data['downloads'].keys())
        
        for country in all_countries:
            visitors = data['visitors'].get(country, 0)
            downloads = data['downloads'].get(country, 0)
            
            if visitors > 0 or downloads > 0:
                message = f"🌍 {country} at {timestamp}\n"
                if visitors > 0:
                    message += f"👥 {visitors} active visitor(s)\n"
                if downloads > 0:
                    message += f"📥 {downloads} file download(s)"
                send_telegram_message(message)
                
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        send_telegram_message(f"❌ Error in analytics monitor: {str(e)}")

if __name__ == "__main__":
    main()
