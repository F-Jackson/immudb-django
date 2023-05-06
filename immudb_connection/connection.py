from django.conf import settings
from immudb.client import ImmudbClient
from immudb.constants import PERMISSION_SYS_ADMIN, \
PERMISSION_ADMIN, \
PERMISSION_NONE, \
PERMISSION_R, \
PERMISSION_RW

from .exceptions import LoginError, LogoutError

def starting_db() -> ImmudbClient:
    try:
        client = ImmudbClient(settings.IMMU_URL)
        client.login(settings.IMMU_USER, settings.IMMU_PASSWORD)
    except Exception as e:
        raise LoginError(f'Error while trying to login the client, error: {str(e)}')
    else:
        return client


def finish_db(*, client: ImmudbClient) -> None:
    try:
        client.logout()
    except Exception as e:
        raise LogoutError(f'Error while trying to logout from the active client season, error: {str(e)}')
    