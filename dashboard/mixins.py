import csv

from django.http import HttpResponse


class CSVExportMixin:
    """ListView'larga ?export=csv orqali joriy filtrlangan ro'yxatni CSV qilib yuklab olish imkonini beradi."""

    csv_filename = "export.csv"
    csv_headers = []

    def get_csv_row(self, obj):
        raise NotImplementedError

    def export_csv(self):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{self.csv_filename}"'
        writer = csv.writer(response)
        writer.writerow(self.csv_headers)
        for obj in self.get_queryset():
            writer.writerow(self.get_csv_row(obj))
        return response

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            return self.export_csv()
        return super().get(request, *args, **kwargs)
