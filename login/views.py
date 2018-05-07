import hashlib
import datetime
from django.shortcuts import render
from django.shortcuts import redirect
from django.core.mail import EmailMultiAlternatives
from .models import User, ConfirmString
from web import settings

from .forms import UserForm, RegisterForm

# 对密码进行加密
def hash_code(s, salt='myweb'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()

def make_confirm_string(user):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = hash_code(user.name, now)
    ConfirmString.objects.create(code=code, user=user)

    return code

def send_email(email, code):
    subject, to = "来自TTBUG的注册确认邮件", email
    text_content = "欢迎访问ttbug.win，这是我的个人博客"
    html_content = "感谢注册<a href='http://{}/confirm/?code={}' target=blank>TTBUG</a>，请点击链接激活，链接有效期为{}天".format('127.0.0.1:8000',code,settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject,text_content, settings.EMAIL_HOST_USER, [to])
    msg.attach_alternative(html_content, 'text/html')
    msg.send()


# Create your views here.
def index(request):
    pass
    return render(request, 'login/index.html')

def login(request):
    if request.session.get('is_login', None):
        return redirect('index')

    if request.method == 'POST':
        form = UserForm(request.POST)
        message = None
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            try:
                user = User.objects.get(name=username)
                if user.password != hash_code(password):
                    message = "密码错误"
                else:
                    if not user.has_confirmed:
                        message = "账户尚未激活，请先去注册邮箱激活账号"
                        return render(request, 'login/confirm.html', {'error': message})

                    request.session['is_login'] = True
                    request.session['username'] = username
                    return redirect('index')
            except:
                message = "用户不存在"

        return render(request, 'login/login.html', {'error': message, 'form':form})

    form = UserForm()
    return render(request, 'login/login.html', {'form': form})

def register(request):
    if request.session.get('is_login', None):
        return redirect('index')

    message = None
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password1 = form.cleaned_data.get('password1')
            password2 = form.cleaned_data.get('password2')
            email = form.cleaned_data.get('email')
            sex = form.cleaned_data.get('sex')

            if password1 != password2:
                message = "两次输入的密码不一致"
                return render(request, 'login/register.html', {'error':message, 'form':form})
            else:
                username_exists = User.objects.filter(name=username)
                if username_exists:
                    message = "用户名已存在"
                    return render(request, 'login/register.html', {'error': message, 'form': form})
                email_exists = User.objects.filter(email=email)
                if email_exists:
                    message = "该邮箱已注册"
                    return render(request, 'login/register.html', {'error': message, 'form': form})
            password = hash_code(password1)
            user = User.objects.create(name=username, password=password, email=email, sex=sex)

            code = make_confirm_string(user)
            send_email(email, code)
            message = "请前往邮箱激活账号"
            return render(request, 'login/confirm.html', {'error':message})
        return render(request, 'login/register.html', {'error': message, 'form': form})
    form = RegisterForm()
    return render(request, 'login/register.html', {'error':message,'form': form})

def logout(request):
    if not request.session.get('is_login', None):
        return redirect('index')
    request.session.flush()
    return redirect('index')

def confirm(request):
    code = request.GET.get('code', None)
    message = ''
    try:
        confirm = ConfirmString.objects.get(code=code)
    except:
        message = '无效的请求'
        return render(request, 'login/confirm.html', {'error':message})

    ctime = confirm.c_time
    now = datetime.datetime.now()

    if now > ctime + datetime.timedelta(settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = "激活码已经失效，请重新注册"
        return render(request, 'login/confirm.html', {'error': message})
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = '激活成功'
        return render(request, 'login/confirm.html', {'error':message})