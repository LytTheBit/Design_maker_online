from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect

def is_admin(user):
    return user.is_superuser  # solo i superuser possono accedere

# View per la pagina di login
@login_required
@user_passes_test(is_admin)
@staff_member_required
def account_management(request):
    # addestratore_group = Group.objects.get_or_create(name="Addestratore")
    addestratore_group, created = Group.objects.get_or_create(name="Addestratore")

    if request.method == "POST":
        user_id = request.POST.get('user_id')
        action  = request.POST.get('action')
        try:
            utente = User.objects.get(pk=user_id)
            if action == "promote":
                utente.groups.add(addestratore_group)
            elif action == "degrade":
                utente.groups.remove(addestratore_group)
        except User.DoesNotExist:
            pass  # silenziosamente ignora
        return redirect('account_management')

    utenti = User.objects.all().order_by('username')
    return render(request, 'account_app/account_management.html', {
        'utenti': utenti,
        'addestratore_group': addestratore_group,
    })


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

