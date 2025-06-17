from django.urls import path
from django.http import JsonResponse

def simple_test_view(request):
    return JsonResponse({"message": "Simple test works"})

urlpatterns = [
    path("simple-test/", simple_test_view, name="simple_test"),
]
