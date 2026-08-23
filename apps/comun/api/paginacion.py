"""
Paginacion estandar de la API.

Se define una sola clase y se aplica por defecto a todos los listados. Que
todos los listados respondan con la misma envoltura es lo que permite que un
cliente (o el Gateway) escriba una sola vez la logica de "traer la siguiente
pagina".
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PaginacionEstandar(PageNumberPagination):
    """20 elementos por pagina, ampliable hasta 100 con ?tamano=."""

    page_size = 20
    page_size_query_param = "tamano"
    page_query_param = "pagina"
    max_page_size = 100

    def get_paginated_response(self, data) -> Response:
        return Response(
            {
                "total": self.page.paginator.count,
                "pagina": self.page.number,
                "paginas": self.page.paginator.num_pages,
                "resultados": data,
            }
        )
