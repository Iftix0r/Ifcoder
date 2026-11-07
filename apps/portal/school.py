"""O'qituvchi tomoni: guruhlar, davomat, uy vazifalarini tekshirish va o'quv to'lovlari."""

from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, done, form_modal
from apps.core.dates import add_months

from . import services
from .forms import GroupForm, PaymentForm, ReviewForm
from .models import Attendance, Group, Lesson, Payment, Student, Submission


def group_list(request):
    groups = Group.objects.annotate(
        student_count=Count("students", filter=Q(students__user__is_active=True), distinct=True),
        lesson_count=Count("lessons", distinct=True),
    )
    return render(
        request,
        "portal/teacher/group_list.html",
        {"nav_active": "groups", "groups": groups, "ungrouped": Student.objects.filter(group__isnull=True).count()},
    )


def group_detail(request, pk):
    group = get_object_or_404(Group, pk=pk)
    lessons = group.lessons.annotate(
        came=Count("marks", filter=~Q(marks__status=Attendance.Status.ABSENT)), total=Count("marks")
    )
    students = Student.objects.with_stats().filter(group=group).order_by("user__first_name")
    return render(
        request,
        "portal/teacher/group_detail.html",
        {
            "nav_active": "groups",
            "group": group,
            "students": students,
            "lessons": lessons[:20],
            "today": timezone.localdate().isoformat(),
        },
    )


def group_create(request):
    return form_modal(request, GroupForm, title="Yangi guruh", icon="users-round")


def group_edit(request, pk):
    group = get_object_or_404(Group, pk=pk)
    return form_modal(
        request,
        GroupForm,
        title=group.name,
        icon="pencil",
        instance=group,
        subtitle="O'chirilsa darslar, davomat va guruh e'lonlari ham o'chadi",
        delete_url=reverse("group_delete", args=[pk]),
    )


@require_POST
def group_delete(request, pk):
    return delete_done(get_object_or_404(Group, pk=pk), "Guruh o'chirildi.", redirect=reverse("group_list"))


def lesson_edit(request, pk, day):
    group = get_object_or_404(Group, pk=pk)
    try:
        lesson_date = date.fromisoformat(day)
    except ValueError:
        raise Http404 from None
    lesson = group.lessons.filter(date=lesson_date).first()
    marks = {mark.student_id: mark.status for mark in lesson.marks.all()} if lesson else {}
    # Guruhdan chiqqan o'quvchining eski belgisi ham ko'rinib tursin
    students = list(
        Student.objects.filter(Q(group=group, user__is_active=True) | Q(pk__in=marks))
        .select_related("user")
        .order_by("user__first_name")
    )
    if request.method == "POST":
        with transaction.atomic():
            lesson, _ = Lesson.objects.update_or_create(
                group=group, date=lesson_date, defaults={"topic": request.POST.get("topic", "").strip()[:200]}
            )
            for student in students:
                status = request.POST.get(f"s{student.pk}")
                if status in Attendance.Status.values:
                    Attendance.objects.update_or_create(lesson=lesson, student=student, defaults={"status": status})
        messages.success(request, "Davomat saqlandi.")
        return redirect("group_detail", pk=pk)
    for student in students:
        student.mark = marks.get(student.pk, Attendance.Status.PRESENT)
    return render(
        request,
        "portal/teacher/lesson_edit.html",
        {
            "nav_active": "groups",
            "group": group,
            "lesson": lesson,
            "day": lesson_date,
            "students": students,
            "statuses": Attendance.Status.choices,
        },
    )


def review_list(request):
    show_all = request.GET.get("show") == "all"
    rows = Submission.objects.select_related("post", "student__user").order_by("updated_at")
    waiting = rows.filter(status=Submission.Status.SUBMITTED).count()
    if show_all:
        rows = rows.order_by("-updated_at")[:100]
    else:
        rows = rows.filter(status=Submission.Status.SUBMITTED)
    return render(
        request,
        "portal/teacher/review_list.html",
        {"nav_active": "reviews", "rows": rows, "show_all": show_all, "waiting": waiting},
    )


def review_edit(request, pk):
    row = get_object_or_404(Submission.objects.select_related("post", "student__user"), pk=pk)
    return form_modal(
        request,
        ReviewForm,
        title=row.post.title,
        icon="clipboard-check",
        subtitle=row.student.full_name,
        instance=row,
        size="lg",
        success="Baholandi.",
        template="portal/teacher/review_modal.html",
        extra={"row": row},
    )


def payment_list(request):
    month = services.parse_month(request.GET.get("month"))
    rows = services.payment_rows(month)
    return render(
        request,
        "portal/teacher/payment_list.html",
        {
            "nav_active": "payments",
            "month": month,
            "previous": add_months(month, -1),
            "following": add_months(month, 1),
            "rows": rows,
            "expected": sum(row.due for row in rows),
            "collected": sum(row.paid for row in rows),
            "left": sum(row.left for row in rows),
            "unpaid": sum(row.left > 0 for row in rows),
        },
    )


def payment_create(request, pk):
    student = get_object_or_404(Student.objects.select_related("user", "group"), pk=pk)
    month = services.parse_month(request.GET.get("month"))
    fee = student.group.monthly_fee if student.group else 0
    paid = sum(
        payment.transaction.amount for payment in student.payments.filter(month=month).select_related("transaction")
    )
    return form_modal(
        request,
        PaymentForm,
        title=student.full_name,
        icon="banknote",
        tone="tone-emerald",
        subtitle=f"{month:%Y-%m} oyi uchun. Kirim-chiqimga ham yoziladi",
        initial={"amount": max(fee - paid, 0) or None, "date": timezone.localdate(), "method": "cash"},
        form_kwargs={"student": student, "month": month},
        success="To'lov yozildi.",
    )


@require_POST
def payment_delete(request, pk):
    payment = get_object_or_404(Payment.objects.select_related("transaction"), pk=pk)
    payment.transaction.delete()  # To'lov kirim bilan birga o'chadi
    return done("To'lov va kirim yozuvi o'chirildi.", close=False)
