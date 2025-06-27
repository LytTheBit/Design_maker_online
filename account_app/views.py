from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect

# Views per la registrazione degli utenti
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Reindirizza alla pagina di login dopo la registrazione
    else:
        form = UserCreationForm()
    return render(request, 'account_app/register.html', {'form': form})

