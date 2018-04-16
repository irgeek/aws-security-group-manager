#!/usr/bin/env python3
import sys
import logging
import vendor.jsonlogger
from datetime import datetime, timezone

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

def setup_logging():
    logHandler = logging.StreamHandler(sys.stdout)
    logHandler.setFormatter(CustomJsonFormatter('(timestamp) (level) (name) (message)'))
    logger = logging.getLogger()
    logger.addHandler(logHandler)
    logger.setLevel(logging.DEBUG)

    for library_logger in 'botocore','boto3':
        logging.getLogger(library_logger).setLevel(logging.ERROR)

setup_logging()
