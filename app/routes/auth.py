"""
Аутентификация: вход, выход, регистрация, сброс пароля
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User, Client, Role
from app.utils import send_password_reset_email, verify_reset_token, send_admin_reset_notification
from app.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Вход в систему
    Проверяет блокировку, редиректит в ЛК по роли
    """
    if current_user.is_authenticated:
        return redirect(url_for('index.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль', 'danger')
            return redirect(url_for('auth.login'))

        if user.is_blocked:
            reason = user.block_reason or 'не указана'
            flash(f'Аккаунт заблокирован: {reason}', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember.data)

        next_page = request.args.get('next')
        if not next_page:
            role_code = user.role.code if user.role else 'client'
            if role_code == 'admin':
                next_page = url_for('admin.dashboard')
            elif role_code == 'dispatcher':
                next_page = url_for('dispatcher.dashboard')
            elif role_code == 'worker':
                next_page = url_for('worker.dashboard')
            else:
                next_page = url_for('user.dashboard')
        return redirect(next_page)

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Регистрация клиента
    Создаёт User + Client, почта и телефон считаются подтверждёнными сразу
    """
    if current_user.is_authenticated:
        return redirect(url_for('index.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        client_role = Role.query.filter_by(code='client').first()
        if not client_role:
            flash('Ошибка конфигурации системы', 'danger')
            return redirect(url_for('auth.register'))

        user = User(
            email=form.email.data,
            phone=form.phone.data,
            last_name=form.last_name.data,
            first_name=form.first_name.data,
            patronymic=form.patronymic.data,
            role_id=client_role.id,
            email_confirmed=True,
            phone_confirmed=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        client = Client(
            user_id=user.id,
            city_id=form.city_id.data,
            street=form.street.data,
            house=form.house.data,
            apartment=form.apartment.data
        )
        db.session.add(client)
        db.session.commit()

        flash('Регистрация успешна', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Запрос сброса пароля
    Клиентам — ссылка на email, сотрудникам — уведомление админу
    """
    if current_user.is_authenticated:
        return redirect(url_for('index.index'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if user.role and user.role.code == 'client':
                send_password_reset_email(user)
                flash('Инструкция по сбросу пароля отправлена на email', 'success')
            else:
                admin_role = Role.query.filter_by(code='admin').first()
                admins = User.query.filter_by(role_id=admin_role.id).all() if admin_role else []
                for admin in admins:
                    send_admin_reset_notification(admin, user)
                flash('Запрос отправлен администратору', 'info')
        else:
            flash('Если указанный email зарегистрирован, инструкция отправлена', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Установка нового пароля для клиента
    Токен действителен 1 час
    """
    if current_user.is_authenticated:
        return redirect(url_for('index.index'))

    email = verify_reset_token(token)
    if not email:
        flash('Ссылка недействительна или истекла', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_password_token = None
        user.reset_password_expires = None
        db.session.commit()
        flash('Пароль успешно изменён', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)