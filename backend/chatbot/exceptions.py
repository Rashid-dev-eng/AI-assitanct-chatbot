from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    status = response.status_code
    details = response.data
    code = "request_error"
    message = "The request could not be completed."
    if isinstance(details, dict) and "detail" in details:
        message = str(details["detail"])
        details = None
    elif status == 400:
        message = "The request contains invalid or missing fields."
        code = "validation_error"
    elif status == 401 or status == 403:
        message = "Authentication or permission is required for this operation."
        code = "permission_denied"
    elif status == 404:
        message = "The requested resource was not found."
        code = "not_found"
    elif status == 429:
        message = "Too many requests. Please wait and try again."
        code = "rate_limited"
    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
