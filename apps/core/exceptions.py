import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A concurrent conflict occurred. The resource has changed or is no longer available."
    default_code = "conflict"


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler to standardize API error responses.
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "success": False,
            "status_code": response.status_code,
            "errors": response.data,
            "message": _extract_error_message(response.data),
        }
        response.data = custom_data
    else:
        logger.error(f"Unhandled Exception: {exc!s}", exc_info=True)
        from django.conf import settings

        detail_msg = (
            str(exc)
            if getattr(settings, "DEBUG", False)
            else "An unexpected internal error occurred. Please contact support."
        )
        response = Response(
            {
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "An internal server error occurred.",
                "errors": {"detail": detail_msg},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _extract_error_message(data):
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        elif "non_field_errors" in data:
            return str(data["non_field_errors"][0])
        else:
            first_key = next(iter(data), None)
            if first_key:
                val = data[first_key]
                if isinstance(val, list) and len(val) > 0:
                    return f"{first_key}: {val[0]}"
                return f"{first_key}: {val}"
    elif isinstance(data, list) and len(data) > 0:
        return str(data[0])
    return "Validation error"
