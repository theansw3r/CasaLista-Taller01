from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PaginacionEstandar(PageNumberPagination):

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


def respuesta_paginada(vista, request, objetos, serializer) -> Response:
    paginador = PaginacionEstandar()
    pagina = paginador.paginate_queryset(objetos, request, view=vista)
    return paginador.get_paginated_response(serializer(pagina, many=True).data)
