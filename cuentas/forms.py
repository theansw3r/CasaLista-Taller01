"""Registro de usuarios. Un Cliente nuevo se crea con UserCreationForm."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from reservas.models import Cliente


class RegistroClienteForm(UserCreationForm):
    email = forms.EmailField(required=True)
    nombre = forms.CharField(max_length=120)
    telefono = forms.CharField(max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    @transaction.atomic
    def save(self, commit=True):
        usuario = super().save(commit=commit)
        Cliente.objects.create(
            usuario=usuario,
            nombre=self.cleaned_data["nombre"],
            telefono=self.cleaned_data.get("telefono", ""),
        )
        return usuario
