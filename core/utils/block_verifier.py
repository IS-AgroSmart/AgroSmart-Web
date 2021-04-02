import re

from core.models import BlockCriteria
from django.db.models import Q


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', None)
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def user_verifier(user, request):
    user_name = user['username']
    user_email = user['email']
    user_domain = re.search(r'@[\w.]+', user['email']).group()[1::]
    user_ip = get_client_ip(request)
    if user_ip:
        block_criteria = BlockCriteria.objects.filter(
            Q(value=user_email) | Q(value=user_domain) | Q(value=user_name)
            | Q(ip=user_ip))
        if block_criteria:
            return True
    else:
        block_criteria = BlockCriteria.objects.filter(
            Q(value=user_email) | Q(value=user_domain) | Q(value=user_name))
        if block_criteria:
            return True
    return False
