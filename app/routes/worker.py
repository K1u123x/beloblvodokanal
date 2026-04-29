"""
Работник: панель, заявки, выполнение работ, чат, редактирование профиля
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import WorkerProfile, Request, RequestStatus, Message
from app.utils import censor_text
from app.forms import MessageForm, EmployeeAboutForm
from datetime import datetime

worker_bp = Blueprint('worker', __name__, url_prefix='/worker')


@worker_bp.before_request
@login_required
def restrict_worker():
    if not current_user.role or current_user.role.code != 'worker':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index.index'))


def get_current_worker():
    return WorkerProfile.query.filter_by(user_id=current_user.id).first()


@worker_bp.route('/dashboard')
def dashboard():
    """Панель работника с текущими заявками и статистикой"""
    worker = get_current_worker()
    if not worker:
        flash('Профиль не найден', 'danger')
        return redirect(url_for('index.index'))

    assigned_status = RequestStatus.query.filter_by(code='assigned').first()
    in_progress_status = RequestStatus.query.filter_by(code='in_progress').first()
    completed_status = RequestStatus.query.filter_by(code='completed').first()

    my_requests = Request.query.filter_by(worker_id=worker.id).filter(
        Request.status_id.in_([assigned_status.id, in_progress_status.id])
    ).order_by(Request.scheduled_date).all()

    completed_count = Request.query.filter_by(worker_id=worker.id, status_id=completed_status.id).count()

    return render_template('worker/dashboard.html', requests=my_requests, completed_count=completed_count)


@worker_bp.route('/my_requests')
def my_requests():
    """Все заявки работника"""
    worker = get_current_worker()
    if not worker:
        return redirect(url_for('index.index'))
    all_requests = Request.query.filter_by(worker_id=worker.id).order_by(Request.created_at.desc()).all()
    return render_template('worker/my_requests.html', requests=all_requests)


@worker_bp.route('/request/<int:request_id>')
def request_detail(request_id):
    """Детали заявки работника"""
    req = Request.query.get_or_404(request_id)
    worker = get_current_worker()
    if not worker or req.worker_id != worker.id:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('worker.my_requests'))
    return render_template('worker/request_detail.html', request=req)


@worker_bp.route('/request/<int:request_id>/start')
def start_work(request_id):
    """Начать работу: статус assigned -> in_progress"""
    req = Request.query.get_or_404(request_id)
    worker = get_current_worker()
    if worker and req.worker_id == worker.id and req.status and req.status.code == 'assigned':
        in_progress_status = RequestStatus.query.filter_by(code='in_progress').first()
        req.status_id = in_progress_status.id
        db.session.commit()
        flash('Работа начата', 'success')
    return redirect(url_for('worker.request_detail', request_id=request_id))


@worker_bp.route('/request/<int:request_id>/complete')
def complete(request_id):
    """Завершить работу: статус in_progress -> completed"""
    req = Request.query.get_or_404(request_id)
    worker = get_current_worker()
    if worker and req.worker_id == worker.id and req.status and req.status.code == 'in_progress':
        completed_status = RequestStatus.query.filter_by(code='completed').first()
        req.status_id = completed_status.id
        req.completed_at = datetime.utcnow()
        db.session.commit()
        flash('Заявка выполнена', 'success')
    return redirect(url_for('worker.request_detail', request_id=request_id))


@worker_bp.route('/request/<int:request_id>/chat', methods=['GET', 'POST'])
def chat(request_id):
    """Чат с клиентом"""
    req = Request.query.get_or_404(request_id)
    worker = get_current_worker()
    if not worker or req.worker_id != worker.id:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('worker.my_requests'))

    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(
            request_id=request_id,
            author_id=current_user.id,
            content=censor_text(form.content.data)
        )
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('worker.chat', request_id=request_id))

    messages = Message.query.filter_by(request_id=request_id).order_by(Message.timestamp).all()
    return render_template('worker/chat.html', request=req, messages=messages, form=form)


@worker_bp.route('/edit-about', methods=['GET', 'POST'])
@login_required
def edit_about():
    """Редактирование раздела О себе в публичном профиле"""
    worker = get_current_worker()
    if not worker:
        flash('Профиль не найден', 'danger')
        return redirect(url_for('index.index'))

    form = EmployeeAboutForm()
    if form.validate_on_submit():
        worker.about_me = form.about_me.data
        db.session.commit()
        flash('Описание сохранено', 'success')
        return redirect(url_for('index.worker_profile', worker_id=worker.id))

    form.about_me.data = worker.about_me
    return render_template('worker/edit_about.html', form=form)