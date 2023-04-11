"""Pagination classes for hubuum."""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class HubuumFlexiblePagination(PageNumberPagination):
    """
    A custom pagination class that allows users to set their own pagination size
    with a maximum limit and a default value.
    """

    page_size = 100
    max_page_size = 200
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        """
        Return a paginated response with count, next, and previous links as headers.

        Args:
            data: The data to be paginated.

        Returns:
            rest_framework.response.Response: The paginated response.
        """
        response = Response(data)
        response["X-Total-Count"] = self.page.paginator.count
        response["Link"] = self.build_link_header()
        return response

    def build_link_header(self):
        """
        Build the Link header value with next and previous links.

        Returns:
            str: The value of the Link header.
        """
        link_header = []

        next_link = self.get_next_link()
        if next_link:
            link_header.append(f'<{next_link}>; rel="next"')

        previous_link = self.get_previous_link()
        if previous_link:
            link_header.append(f'<{previous_link}>; rel="prev"')

        return ", ".join(link_header)
