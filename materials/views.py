from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Material
from .forms import MaterialForm


class MaterialListView(ListView):
    model = Material
    template_name = 'materials/material_list.html'
    context_object_name = 'materials'
    paginate_by = 12

    def get_queryset(self):
        return Material.objects.filter(is_active=True).select_related('created_by')


class MaterialDetailView(DetailView):
    model = Material
    template_name = 'materials/material_detail.html'
    context_object_name = 'material'

    def get_queryset(self):
        return Material.objects.filter(is_active=True).select_related('created_by')


class MaterialCreateView(LoginRequiredMixin, CreateView):
    model = Material
    form_class = MaterialForm
    template_name = 'materials/material_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Material added successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class MaterialUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Material
    form_class = MaterialForm
    template_name = 'materials/material_form.html'

    def test_func(self):
        material = self.get_object()
        return self.request.user == material.created_by or self.request.user.is_staff

    def form_valid(self, form):
        messages.success(self.request, 'Material updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class MaterialDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Material
    template_name = 'materials/material_confirm_delete.html'
    success_url = reverse_lazy('materials:list')

    def test_func(self):
        material = self.get_object()
        return self.request.user == material.created_by or self.request.user.is_staff

    def form_valid(self, form):
        messages.success(self.request, 'Material deleted successfully!')
        return super().form_valid(form)