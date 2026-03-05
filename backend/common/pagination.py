from rest_framework.pagination import CursorPagination, PageNumberPagination

class StandardCursorPagination(CursorPagination):
    """
    Standard cursor pagination for large datasets.
    Provides fast pagination using a cursor instead of offset.
    """
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    ordering = "-created_at"


class StandardPageNumberPagination(PageNumberPagination):
    """
    Fallback pagination for endpoints that cannot use cursors 
    (e.g., when ordering by non-unique or dynamic fields).
    """
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
