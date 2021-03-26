import requests


def get_info(server_url, uuid, token=""):
    return requests.get(f"{server_url}/task/{uuid}/info?token={token}")
