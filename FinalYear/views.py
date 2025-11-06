from django.shortcuts import redirect

def home(request):
    return redirect('login')  # Name of your login URL
