"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_dashboard_direct(request):
    response = JsonResponse({
        "num_records": 100,
        "num_listings": 500,
        "accuracy": 85.5,
        "unevaluated": 25,
        "record_of_the_day": None,
        "record_of_the_day_obj": None,
        "breakdown": {}
    })
    response['Access-Control-Allow-Origin'] = 'http://localhost:5173'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

urlpatterns = [
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
    path("api-dashboard/", api_dashboard_direct, name="api_dashboard_direct"),
    path("", include("discogs.urls")),
]
