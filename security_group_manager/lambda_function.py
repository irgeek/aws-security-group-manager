import os
import re
import logging
import boto3
import json
import vendor
import botocore.exceptions

logger = logging.getLogger()
logger.info('Lambda function startup')

ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    logger.debug(
        'Handling security manager event',
        extra = dict(
            event = event,
        )
    )

    ip_ranges = [
        cidr_ip(i)
        for i in event.get('cidrs', [])
        if ':' not in i
    ] + [
        cidr_ip('%s/32'%i)
        for i in event.get('ips', [])
        if ':' not in i
    ]

    ipv6_ranges = [
        cidr_ipv6(i)
        for i in event.get('cidrs', [])
        if ':' in i
    ] + [
        cidr_ipv6('%s/128'%i)
        for i in event.get('ips', [])
        if ':' in i
    ]

    if len(ip_ranges) + len(ipv6_ranges) == 0:
        logger.error('No entries to apply')
        return {}

    allow_ingress_by_group = parse_allowed_ingress(
        ( i.split(':') for i in os.environ['ALLOW_INGRESS'].split(',') )
    )

    logger.debug(
        'Input values',
        extra = dict(
            allow_ingress_by_group = allow_ingress_by_group,
            ip_ranges = ip_ranges,
            ipv6_ranges = ipv6_ranges,
        )
    )

    for group_id, ip_permission_list in allow_ingress_by_group.items():
        for ip_permission in ip_permission_list:
            ip_permission.update(
                IpRanges   = ip_ranges,
                Ipv6Ranges = ipv6_ranges,
            )
        logger.debug(
            'Security group details',
            extra = dict(
                group_id = group_id,
                ip_permission_list = ip_permission_list,
            )
        )
        if 'AddCidrEntries' in event:
            try:
                ec2.authorize_security_group_ingress(
                    GroupId = group_id,
                    IpPermissions = ip_permission_list,
                )
            except botocore.exceptions.ClientError as ex:
                if 'InvalidPermission.Duplicate' not in str(ex):
                    raise
        else:
            ec2.revoke_security_group_ingress(
                GroupId = group_id,
                IpPermissions = ip_permission_list,
            )

    return {
        'cidrs': [ i['CidrIp'] for i in ip_ranges ] + [ i['CidrIpv6'] for i in ipv6_ranges ],
        'delay': parse_timespan(event.get('delay', 3600)),
    }

def parse_allowed_ingress(allowed_ingress):
    allowed_ingress_by_group = {}
    for group_id, protocol, port in allowed_ingress:
        ip_permission_list = allowed_ingress_by_group.get(group_id.lower(), [])
        ip_permission_list.append({
            'IpProtocol': protocol.lower(),
            'FromPort':   int(port),
            'ToPort':     int(port),
        })
        allowed_ingress_by_group[group_id.lower()] = ip_permission_list
    return allowed_ingress_by_group

def cidr_ip(ip, key = 'CidrIp'):
    return {key: ip, 'Description': 'Added by SecurityGroupStateMachine'}

def cidr_ipv6(ipv6):
    return cidr_ip(ipv6, 'CidrIpv6')

def parse_timespan(timespan):
    """
    Parse a human-style timestamp and return a datetime.timedelta object.
    Timespans are designated by a number and unit. Any number of number+unit
    pairs may be specified.

    Supported units:
        s: Seconds (Missing units are also treated as seconds)
        m: Minutes (60 seconds)
        h: Hours (3600 seconds)
        d: Days (86400 seconds)
        w: Weeks (604800 seconds)

    Examples:
        10m  = 10 minutes (600 seconds)
        3h4m = 3 hours 4 minute (11040 seconds)
        2w1d = 2 weeks 1 day (1296000 seconds)
    """
    if isinstance(timespan, int):
        return timespan
    _multipliers = { '':1, 's':1, 'm':60, 'h':60*60, 'd':60*60*24, 'w':60*60*24*7 }
    seconds = 0
    pairs = re.findall('([0-9]+)([smhdw])?', timespan)
    if not pairs:
        return
    for number, unit in pairs:
        seconds += int(number) * _multipliers.get(unit, 0)
    return seconds

