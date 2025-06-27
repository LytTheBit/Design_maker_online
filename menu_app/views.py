from django.shortcuts import render

# Create your views here.


def home(request):
    if request.user.is_authenticated:
        return render(request, 'menu_app/home_auth.html')
    else:
        return render(request, 'menu_app/home_anon.html')