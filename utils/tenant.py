from database import tenants
from utils.common import build_error
from utils.enums import HttpStatus
from utils.messages import messages

HEADER = "X-Tenant"


def from_request(request):
    """The tenant this request is for. Raises if it names none we serve."""
    subdomain = request.headers.get(HEADER)

    if not subdomain:
        raise build_error(messages["tenantHeaderMissing"], HttpStatus.badRequest)

    try:
        tenant = tenants.find(subdomain)
    except tenants.TenantError as exc:
        raise build_error(
            messages["tenantRegistryUnavailable"], HttpStatus.badGateway, exc
        ) from exc

    if tenant is None:
        raise build_error(
            messages["tenantUnknown"].format(subdomain=subdomain),
            HttpStatus.notFound,
        )

    return tenant