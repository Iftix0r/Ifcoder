"""HTMX modal formalar uchun umumiy yordamchilar.

Ro'yxatlar ``hx-trigger="changed from:body"`` + ``hx-select`` bilan o'zini yangilaydi, shuning uchun
saqlash/o'chirishdan keyin faqat «changed» hodisasi yuboriladi.
"""

from django.http import HttpResponse
from django.shortcuts import render

from .htmx import add_triggers, trigger_toast


def done(message="Saqlandi.", *, event="changed", redirect=None, close=True):
    response = HttpResponse(status=204)
    if redirect:
        response["HX-Redirect"] = redirect
        return response
    events = {event: True}
    if close:
        events["modal:close"] = True
    add_triggers(response, events)
    return trigger_toast(response, message)


def form_modal(
    request,
    form_class,
    *,
    title,
    icon="plus",
    tone="tone-brand",
    subtitle="",
    instance=None,
    initial=None,
    form_kwargs=None,
    save=None,
    success=None,
    event="changed",
    redirect=None,
    delete_url=None,
    size="md",
    template="components/form_modal.html",
    extra=None,
):
    """Modal forma: GET — forma, to'g'ri POST — 204 + hodisalar.

    ``save(form)`` — maxsus saqlash (default ``form.save()``); ``redirect(obj)`` — saqlagach shu URL'ga o'tish.
    """
    form = form_class(
        request.POST or None, request.FILES or None, instance=instance, initial=initial, **(form_kwargs or {})
    )
    if request.method == "POST" and form.is_valid():
        obj = save(form) if save else form.save()
        message = success or ("Saqlandi." if instance else "Qo'shildi.")
        if redirect:
            from django.contrib import messages

            messages.success(request, message)
            return done(redirect=redirect(obj))
        return done(message, event=event)
    context = {
        "form": form,
        "title": title,
        "icon": icon,
        "tone": tone,
        "subtitle": subtitle,
        "action": request.get_full_path(),
        "delete_url": delete_url,
        "size": size,
        "multipart": form.is_multipart(),
        **(extra or {}),
    }
    return render(request, template, context)


def delete_done(obj, message="O'chirildi.", *, event="changed", redirect=None):
    obj.delete()
    if redirect:
        return done(redirect=redirect)
    return done(message, event=event)
