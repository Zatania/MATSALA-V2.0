from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse


class WebView(View):
  def get(self, request):
    if request.user.is_authenticated and getattr(request.user, "role", None) == "admin":
      return redirect(reverse("admin_dashboard"))
    elif request.user.is_authenticated and getattr(request.user, "role", None) == "beneficiary":
      return redirect(reverse("web_beneficiary_dashboard"))
    elif request.user.is_authenticated and getattr(request.user, "role", None) == "donor":
      return redirect(reverse("web_donor_dashboard"))

    return render(request, "web/web-new.html", {
      "layout_path": "layout/layout_blank.html"
    })
