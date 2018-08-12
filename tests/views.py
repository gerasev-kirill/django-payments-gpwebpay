# views.py
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from payments import get_payment_model, RedirectNeeded
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def payment_details(request, payment_id=None):
    payment = get_object_or_404(get_payment_model(), id=payment_id)
    payment.id = 1005
    payment.currency = 'CZK'
    try:
        form = payment.get_form(data=request.GET or None)
    except RedirectNeeded as redirect_to:
        return redirect(str(redirect_to))
    return TemplateResponse(request, 'payment.html',
                            {'form': form, 'payment': payment})
