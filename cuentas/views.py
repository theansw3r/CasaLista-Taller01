from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegistroClienteForm


def registro(request):
    """Registra un Cliente nuevo y lo deja autenticado."""
    if request.method != "POST":
        form = RegistroClienteForm()
    else:
        form = RegistroClienteForm(data=request.POST)
        if form.is_valid():
            nuevo_usuario = form.save()
            login(request, nuevo_usuario)
            return redirect("portal:inicio")
    return render(request, "registration/register.html", {"form": form})
