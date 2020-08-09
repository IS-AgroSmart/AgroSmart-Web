from push_notifications.models import APNSDevice, GCMDevice
from core.models import User

def send_notification_by_user(user_name, message):
    the_user = User.objects.get(username__iexact=user_name)
    device_fcm = GCMDevice.objects.filter(user__id__icontains=the_user.id)
    device_apns = APNSDevice.objects.filter(user__id__icontains=the_user.id)

    device = device_fcm if device_fcm.exists() else device_apns if device_apns.exists() else ""

    if device != "":
        device.send_message(message)

