"""
Paginacion estandar de la API.

Hay una sola clase y todos los listados la usan. Que todos respondan con la
misma envoltura es lo que permite que un cliente (o el API Gateway) escriba
una sola vez la logica de "traer la siguiente pagina".

Sobre por que hace falta el ayudante `respuesta_paginada`
---------------------------------------------------------
`DEFAULT_PAGINATION_CLASS` de DRF solo se aplica sola en las vistas que
heredan de `GenericAPIView`. Este proyecto usa `APIView` a proposito, para
tener control total de la peticion, asi que la paginacion hay que invocarla
explicitamente. El ayudante evita repetir esas cuatro lineas en cada listado.
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


def respuesta_paginada(vista, request, objetos, serializer) -> Response:
    """Pagina una lista y la serializa con la envoltura estandar.

    Ningun listado de la API devuelve una coleccion sin limite: con suficientes
    reservas o profesionales, una respuesta sin paginar tumba la memoria del
    proceso y el tiempo de respuesta del cliente.
    """
    paginador = PaginacionEstandar()
    pagina = paginador.paginate_queryset(objetos, request, view=vista)
    return paginador.get_paginated_response(serializer(pagina, many=True).data)
