from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect

def is_admin(user):
    return user.is_superuser  # solo i superuser possono accedere

# View per la pagina di login
@login_required
@user_passes_test(is_admin)
def account_management(request):
    utenti = User.objects.all()
    addestratore_group, _ = Group.objects.get_or_create(name="Addestratore")

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        user = User.objects.get(pk=user_id)
        addestratore_group.user_set.add(user)
        return redirect("account_management")

    return render(request, "account_app/account_management.html", {
        "utenti": utenti,
        "addestratore_group": addestratore_group
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

