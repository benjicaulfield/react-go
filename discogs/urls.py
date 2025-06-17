from django.urls import path
from django.http import JsonResponse

def simple_api_test(request):
    return JsonResponse({"message": "API test works", "status": "success"})

def api_dashboard_test(request):
    return JsonResponse({
        "num_records": 100,
        "num_listings": 500,
        "accuracy": 85.5,
        "unevaluated": 25,
        "record_of_the_day": None,
        "record_of_the_day_obj": None,
        "breakdown": {}
    })

urlpatterns = [
    path("api-dashboard/", api_dashboard_test, name="api_dashboard"),
    path("simple-api-test/", simple_api_test, name="simple_api_test"),
]
