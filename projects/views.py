from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from dashboard.mixins import CSVExportMixin
from tasks.models import Task

from .forms import ProjectForm
from .models import Project, ProjectDocument, ProjectFile


class ProjectListView(LoginRequiredMixin, CSVExportMixin, ListView):
    model = Project
    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 20
    csv_filename = "loyihalar.csv"
    csv_headers = ["Nomi", "Mijoz", "Holati", "Muddat", "Yaratilgan sana"]

    def get_csv_row(self, obj):
        return [obj.name, obj.client, obj.get_status_display(), obj.deadline, obj.created_at]

    def get_queryset(self):
        qs = super().get_queryset().select_related("client")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["status_choices"] = Project.Status.choices
        return ctx


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "projects/detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tasks_by_status"] = [
            (
                status,
                label,
                self.object.tasks.filter(status=status).select_related("assigned_to"),
            )
            for status, label in Task.Status.choices
        ]
        ctx["tickets"] = self.object.tickets.select_related("client").all()[:10]
        ctx["files"] = self.object.files.select_related("uploaded_by").all()
        ctx["documents"] = self.object.documents.all()
        ctx["file_categories"] = ProjectFile.Category.choices
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/form.html"
    success_url = reverse_lazy("projects:list")


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/form.html"

    def get_success_url(self):
        return reverse("projects:detail", args=[self.object.pk])


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("projects:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.success_url
        return ctx


# ==========================================
# 5. TIJORAT TAKLIFI VA SHARTNOMA VIEWS
# ==========================================

class DocumentListView(LoginRequiredMixin, ListView):
    model = ProjectDocument
    template_name = "projects/document_list.html"
    context_object_name = "documents"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client", "project")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
        doc_type = self.request.GET.get("doc_type")
        if doc_type:
            qs = qs.filter(doc_type=doc_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["doc_type_choices"] = ProjectDocument.DocType.choices
        ctx["current_doc_type"] = self.request.GET.get("doc_type", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = ProjectDocument
    fields = ["title", "doc_type", "client", "project", "amount", "status", "content"]
    template_name = "projects/document_form.html"
    success_url = reverse_lazy("projects:document_list")

    def get_initial(self):
        initial = super().get_initial()
        template_type = self.request.GET.get("template", "contract")
        date_str = timezone.now().strftime("%d.%m.%Y")
        
        if template_type == "contract":
            initial["title"] = "Dasturiy Ta'minot Yaratish Shartnomasi"
            initial["doc_type"] = ProjectDocument.DocType.CONTRACT
            initial["content"] = f"""<h2>DASTURCHILIK VA TEXNIK XIZMAT SHARTNOMASI</h2>
<p><strong>Sana:</strong> {date_str}</p>
<p><strong>Pudratachi:</strong> "Ifcoder Software Studio"</p>
<p><strong>Mijoz:</strong> [Mijoz nomi]</p>
<hr>
<h3>1. Shartnoma Mavzusi</h3>
<p>Pudratachi Mijozning topshirig'iga binoan dasturiy ta'minotni ishlab chiqish hamda ishga tushirish majburiyatini oladi.</p>

<h3>2. Shartnoma Qiymati</h3>
<p>Shartnomaning umumiy qiymati kelishilgan miqdorda belgilanadi.</p>

<h3>3. Tomonlarning Majburiyatlari</h3>
<ul>
  <li>Pudratachi loyihani belgilangan muddatda topshirishi shart.</li>
  <li>Mijoz ishni o'z vaqtida qabul qilishi va to'lovni o'tkazishi shart.</li>
</ul>"""
        elif template_type == "proposal":
            initial["title"] = "Loyiha Bo'yicha Tijorat Taklifi va Smeta"
            initial["doc_type"] = ProjectDocument.DocType.PROPOSAL
            initial["content"] = f"""<h2>TIJORAT TAKLIFI VA LOYIHA SMETASI</h2>
<p><strong>Sana:</strong> {date_str}</p>
<hr>
<h3>Loyiha Qisqacha Tavsifi</h3>
<p>Ushbu tijorat taklifi zamonaviy web/mobile ilovani loyihalash va ishlab chiqishni o'z ichiga oladi.</p>

<h3>Bosqichlar va Smeta</h3>
<table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;margin-top:12px;">
  <thead>
    <tr style="background:#f1f5f9;"><th>Bosqich</th><th>Tavsif</th><th>Muddat</th><th>Summa</th></tr>
  </thead>
  <tbody>
    <tr><td>1. Dizayn</td><td>UI/UX Dizayn va prototip</td><td>5 kun</td><td>2,000,000 UZS</td></tr>
    <tr><td>2. Dasturlash</td><td>Frontend &amp; Backend yaratish</td><td>15 kun</td><td>6,000,000 UZS</td></tr>
    <tr><td>3. Test &amp; Deploy</td><td>Serverga o'rnatish</td><td>3 kun</td><td>1,000,000 UZS</td></tr>
  </tbody>
</table>"""
        return initial


class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = ProjectDocument
    template_name = "projects/document_detail.html"
    context_object_name = "document"


class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectDocument
    fields = ["title", "doc_type", "client", "project", "amount", "status", "content"]
    template_name = "projects/document_form.html"

    def get_success_url(self):
        return reverse("projects:document_detail", args=[self.object.pk])


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = ProjectDocument
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("projects:document_list")


class DocumentPrintView(LoginRequiredMixin, DetailView):
    model = ProjectDocument
    template_name = "projects/document_print.html"
    context_object_name = "document"


# ==========================================
# 7. LOYIHA FAYLLARI VIEWS
# ==========================================

class ProjectFileUploadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", ProjectFile.Category.OTHER)
        external_url = request.POST.get("external_url", "").strip()
        is_public = request.POST.get("is_public_to_client") == "on"
        uploaded_file = request.FILES.get("file")

        if not title:
            messages.error(request, "Fayl sarlavhasini kiriting!")
            return redirect("projects:detail", pk=project.pk)

        ProjectFile.objects.create(
            project=project,
            title=title,
            category=category,
            file=uploaded_file,
            external_url=external_url,
            is_public_to_client=is_public,
            uploaded_by=request.user,
        )
        messages.success(request, f"'{title}' fayli loyihaga qo'shildi!")
        return redirect("projects:detail", pk=project.pk)


class ProjectFileDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        file_obj = get_object_or_404(ProjectFile, pk=pk)
        project_id = file_obj.project.pk
        file_obj.delete()
        messages.success(request, "Fayl muvaffaqiyatli o'chirildi.")
        return redirect("projects:detail", pk=project_id)

