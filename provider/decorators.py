from django.contrib import messages
from django.shortcuts import redirect

def provider_required(function):
    """
    A decorator that checks if the logged-in user has the 'PROVIDER' role.
    Redirects to the home page with an error message if they don't.
    """
    def wrap(request, *args, **kwargs):
        # We assume @login_required is also used, so request.user is available.
        if request.user.role == 'PROVIDER':
            # If the user is a provider, execute the original view function.
            return function(request, *args, **kwargs)
        else:
            # If not, show an error and redirect them away.
            messages.error(request, "Access Denied: This page is for providers only.")
            return redirect('home')  # Or your main landing page URL name
    
    return wrap