"""
Клиентские маршруты: ЛК, каталог, бронирование, чат, отзывы
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Client, Service, Request, RequestStatus, Message, Review
from app.utils import get_available_slots, calculate_worker_rating, censor_text, save_review_photo
from app.forms import EditProfileForm, RequestForm, MessageForm, ReviewForm
from datetime import datetime, timedelta

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.before_request
@login_required
def restrict_user():
    if current_user.role and current_user.role.code != 'client':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index.index'))


def get_current_client():
    return Client.query.filter_by(user_id=current_user.id).first()


@user_bp.route('/dashboard')
@login_required
def dashboard():
    """Личный кабинет с профилем и последними заявками"""
    client = get_current_client()
    if not client:
        flash('Профиль не найден', 'danger')
        return redirect(url_for('index.index'))
    requests = Request.query.filter_by(client_id=client.id).order_by(Request.created_at.desc()).all()
    return render_template('user/dashboard.html', requests=requests)


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Редактирование профиля клиента"""
    client = get_current_client()
    if not client:
        flash('Профиль не найден', 'danger')
        return redirect(url_for('index.index'))

    form = EditProfileForm(obj=current_user)
    if request.method == 'GET':
        form.phone.data = current_user.phone
        form.city_id.data = client.city_id
        form.street.data = client.street
        form.house.data = client.house
        form.apartment.data = client.apartment

    if form.validate_on_submit():
        current_user.last_name = form.last_name.data
        current_user.first_name = form.first_name.data
        current_user.patronymic = form.patronymic.data
        current_user.phone = form.phone.data
        client.city_id = form.city_id.data
        client.street = form.street.data
        client.house = form.house.data
        client.apartment = form.apartment.data
        db.session.commit()
        flash('Профиль обновлён', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html', form=form)


@user_bp.route('/catalog')
@login_required
def catalog():
    """Каталог услуг с поиском по названию"""
    search = request.args.get('search', '')
    query = Service.query
    if search:
        query = query.filter(Service.name.ilike(f'%{search}%'))
    services = query.all()
    return render_template('user/catalog.html', services=services, search=search)


@user_bp.route('/book/<int:service_id>', methods=['GET', 'POST'])
@login_required
def book(service_id):
    """Бронирование услуги с проверкой свободных слотов и дубликатов"""
    service = Service.query.get_or_404(service_id)
    client = get_current_client()
    if not client:
        flash('Профиль не найден', 'danger')
        return redirect(url_for('index.index'))

    form = RequestForm()
    form.service_id.data = service_id

    if request.method == 'GET':
        form.last_name.data = current_user.last_name
        form.first_name.data = current_user.first_name
        form.patronymic.data = current_user.patronymic
        form.city_id.data = client.city_id
        form.street.data = client.street
        form.house.data = client.house
        form.apartment.data = client.apartment

    if form.validate_on_submit():
        available = get_available_slots(service_id, form.scheduled_date.data)
        if form.scheduled_time_start.data not in available:
            flash('Выбранное время недоступно', 'warning')
            return redirect(url_for('user.book', service_id=service_id))

        pending_status = RequestStatus.query.filter_by(code='pending').first()
        assigned_status = RequestStatus.query.filter_by(code='assigned').first()
        in_progress_status = RequestStatus.query.filter_by(code='in_progress').first()

        existing = Request.query.filter(
            Request.client_id == client.id,
            Request.service_id == service_id,
            Request.status_id.in_([pending_status.id, assigned_status.id, in_progress_status.id])
        ).first()

        if existing:
            flash(f'Уже есть активная заявка на "{service.name}"', 'warning')
            return redirect(url_for('user.book', service_id=service_id))

        start_time = form.scheduled_time_start.data
        end_time = (datetime.combine(form.scheduled_date.data, start_time) +
                   timedelta(minutes=service.duration)).time()

        req = Request(
            client_id=client.id,
            service_id=service_id,
            city_id=form.city_id.data,
            street=form.street.data,
            house=form.house.data,
            apartment=form.apartment.data,
            description=form.description.data,
            status_id=pending_status.id,
            scheduled_date=form.scheduled_date.data,
            scheduled_time_start=start_time,
            scheduled_time_end=end_time
        )
        db.session.add(req)
        db.session.commit()
        flash('Заявка создана', 'success')
        return redirect(url_for('user.my_requests'))

    return render_template('user/book.html', form=form, service=service, now=datetime.now())


@user_bp.route('/request/<int:request_id>/cancel')
@login_required
def cancel_request(request_id):
    """Отмена заявки клиентом, только для pending"""
    req = Request.query.get_or_404(request_id)
    client = get_current_client()

    if not client or req.client_id != client.id:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('user.my_requests'))

    if req.status and req.status.code == 'pending':
        rejected_status = RequestStatus.query.filter_by(code='rejected').first()
        req.status_id = rejected_status.id
        req.rejection_reason = 'Отменено пользователем'
        db.session.commit()
        flash('Заявка отменена', 'success')
    elif req.status and req.status.code in ['assigned', 'in_progress']:
        flash('Заявка уже назначена работнику', 'warning')
    else:
        flash('Отмена невозможна', 'info')

    return redirect(url_for('user.request_detail', request_id=request_id))


@user_bp.route('/get_slots/<int:service_id>/<string:selected_date>')
@login_required
def get_slots(service_id, selected_date):
    """API доступных слотов для AJAX на странице бронирования"""
    try:
        d = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except:
        return jsonify([])
    slots = get_available_slots(service_id, d)
    return jsonify([s.strftime('%H:%M') for s in slots])


@user_bp.route('/my_requests')
@login_required
def my_requests():
    """Все заявки клиента"""
    client = get_current_client()
    if not client:
        return redirect(url_for('index.index'))
    requests_list = Request.query.filter_by(client_id=client.id).order_by(Request.created_at.desc()).all()
    return render_template('user/my_requests.html', requests=requests_list)


@user_bp.route('/request/<int:request_id>')
@login_required
def request_detail(request_id):
    """Детали заявки клиента"""
    req = Request.query.get_or_404(request_id)
    client = get_current_client()
    if not client or req.client_id != client.id:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('user.my_requests'))
    return render_template('user/request_detail.html', request=req)


@user_bp.route('/request/<int:request_id>/chat', methods=['GET', 'POST'])
@login_required
def chat(request_id):
    """Чат с работником, AJAX-отправка и автообновление"""
    req = Request.query.get_or_404(request_id)
    client = get_current_client()
    if not client or req.client_id != client.id:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('user.my_requests'))

    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(
            request_id=request_id,
            author_id=current_user.id,
            content=censor_text(form.content.data)
        )
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('user.chat', request_id=request_id))

    messages = Message.query.filter_by(request_id=request_id).order_by(Message.timestamp).all()
    return render_template('user/chat.html', request=req, messages=messages, form=form)


@user_bp.route('/request/<int:request_id>/review', methods=['GET', 'POST'])
@login_required
def leave_review(request_id):
    """Отзыв о выполненной заявке с возможностью прикрепить фото"""
    req = Request.query.get_or_404(request_id)
    client = get_current_client()

    if not client or req.client_id != client.id:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('user.my_requests'))

    if req.status and req.status.code != 'completed':
        flash('Нельзя оставить отзыв', 'warning')
        return redirect(url_for('user.request_detail', request_id=request_id))

    if req.review:
        flash('Отзыв уже оставлен', 'info')
        return redirect(url_for('user.request_detail', request_id=request_id))

    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            request_id=request_id,
            client_id=client.id,
            worker_id=req.worker_id,
            rating=form.rating.data,
            comment=censor_text(form.comment.data)
        )
        if form.photo.data:
            review.photo = save_review_photo(form.photo.data)
        db.session.add(review)
        db.session.commit()
        calculate_worker_rating(req.worker_id)
        flash('Спасибо за отзыв', 'success')
        return redirect(url_for('user.request_detail', request_id=request_id))

    return render_template('user/leave_review.html', form=form, request=req)