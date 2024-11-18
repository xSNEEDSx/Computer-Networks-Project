# AnalysisProgram.py

import datetime
import os

# Directory for logs
LOG_DIR = 'server_logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'server_operations.log')


def log_operation(event_type, details):
    """
    Log a server operation to the log file.

    :param event_type: Type of event (e.g., 'AUTH', 'UPLOAD', 'DOWNLOAD')
    :param details: Details about the event
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {event_type}: {details}\n"
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(log_entry)
