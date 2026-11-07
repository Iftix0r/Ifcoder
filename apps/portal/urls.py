from django.urls import path

from . import school, teacher, views

urlpatterns = [
    # O'quvchi
    path("portal/", views.home, name="portal_home"),
    path("portal/login/", views.PortalLoginView.as_view(), name="portal_login"),
    path("portal/logout/", views.PortalLogoutView.as_view(), name="portal_logout"),
    path("portal/register/", views.register, name="portal_register"),
    path("portal/oyin/", views.hub, name="portal_map"),
    path("portal/oyin/o/<slug:game>/", views.game_map, name="portal_game"),
    path("portal/oyin/<slug:slug>/", views.play, name="portal_play"),
    path("portal/oyin/<slug:slug>/run/", views.run, name="portal_run"),
    path("portal/materiallar/", views.materials, name="portal_materials"),
    path("portal/vazifa/<int:pk>/", views.homework, name="portal_homework"),
    path("portal/reyting/", views.rating, name="portal_rating"),
    path("portal/profil/", views.profile, name="portal_profile"),
    # O'qituvchi
    path("students/", teacher.student_list, name="student_list"),
    path("students/<int:pk>/", teacher.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", teacher.student_edit, name="student_edit"),
    path("students/<int:pk>/password/", teacher.student_password, name="student_password"),
    path("students/<int:pk>/delete/", teacher.student_delete, name="student_delete"),
    path("students/<int:pk>/code/<slug:level>/", teacher.student_code, name="student_code"),
    path("students/groups/", school.group_list, name="group_list"),
    path("students/groups/new/", school.group_create, name="group_create"),
    path("students/groups/<int:pk>/", school.group_detail, name="group_detail"),
    path("students/groups/<int:pk>/edit/", school.group_edit, name="group_edit"),
    path("students/groups/<int:pk>/delete/", school.group_delete, name="group_delete"),
    path("students/groups/<int:pk>/lesson/<str:day>/", school.lesson_edit, name="lesson_edit"),
    path("students/reviews/", school.review_list, name="review_list"),
    path("students/reviews/<int:pk>/", school.review_edit, name="review_edit"),
    path("students/payments/", school.payment_list, name="payment_list"),
    path("students/payments/<int:pk>/new/", school.payment_create, name="payment_create"),
    path("students/payments/<int:pk>/delete/", school.payment_delete, name="payment_delete"),
    path("students/posts/", teacher.post_list, name="post_list"),
    path("students/posts/new/", teacher.post_create, name="post_create"),
    path("students/posts/<int:pk>/edit/", teacher.post_edit, name="post_edit"),
    path("students/posts/<int:pk>/delete/", teacher.post_delete, name="post_delete"),
]
