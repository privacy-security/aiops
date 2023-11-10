# Create your views here.

from django.shortcuts import render


def index10m(request):
    return render(request, 'live_monitor_10m.html', {})


def index(request):
    return render(request, 'live_monitor_conn.html', {})
