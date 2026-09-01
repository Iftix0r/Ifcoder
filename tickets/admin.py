from django.contrib import admin
from .models import Ticket, TicketReply


class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 0
    readonly_fields = ["author", "created_at", "is_staff"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["pk", "title", "client", "status", "priority", "created_at", "reply_count"]
    list_filter = ["status", "priority"]
    search_fields = ["title", "body", "client__name"]
    inlines = [TicketReplyInline]
    readonly_fields = ["created_at", "updated_at", "created_by"]


@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ["pk", "ticket", "author", "is_staff", "created_at"]
    list_filter = ["is_staff"]
