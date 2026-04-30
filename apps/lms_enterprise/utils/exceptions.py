"""
LMS Enterprise - Custom Exception Handler
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger('lms')


def custom_exception_handler(exc, context):
    """Custom exception handler with structured error responses."""
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': _get_error_message(response),
                'details': response.data if isinstance(response.data, dict) else {'detail': response.data},
            }
        }
        response.data = custom_response
    else:
        logger.exception(f"Unhandled exception in {context.get('view', 'unknown')}: {exc}")
        response = Response(
            {
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Internal server error',
                    'details': {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _get_error_message(response):
    """Extract a human-readable error message from response."""
    status_messages = {
        400: 'Bad request',
        401: 'Authentication required',
        403: 'Permission denied',
        404: 'Resource not found',
        405: 'Method not allowed',
        409: 'Conflict',
        429: 'Too many requests',
        500: 'Internal server error',
    }
    return status_messages.get(response.status_code, 'An error occurred')
