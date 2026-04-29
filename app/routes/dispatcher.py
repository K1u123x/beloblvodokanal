"""
Диспетчер: панель, заявки, назначение работника с SVD++, чат
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import DispatcherProfile, Request, RequestStatus, Role, WorkerProfile, User, Message
from app.utils import get_recommended_workers_svd, censor_text
from app.forms import AssignWorkerForm, RejectRequestForm, MessageForm

dispatcher_bp = Blueprint('dispatcher', __name__, url_prefix='/dispatcher')


@dispatcher_bp.before_request
@login_required
def restrict_dispatcher():
    if not current_user.role or current_user.role.code != 'dispatcher':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index.index'))


def get_current_dispatcher():
    return DispatcherProfile.query.filter_by(user_id=current_user.id).first()


@dispatcher_bp.route('/dashboard')
def dashboard():
    """Панель диспетчера: ожидающие и активные заявки"""
    pending_status = RequestStatus.query.filter_by(code='pending').first()
    assigned_status = RequestStatus.query.filter_by(code='assigned').first()
    in_progress_status = RequestStatus.query.filter_by(code='in_progress').first()

    pending = Request.query.filter_by(status_id=pending_status.id).order_by(Request.created_at).all()
    active = Request.query.filter(
        Request.status_id.in_([assigned_status.id, in_progress_status.id])
    ).order_by(Request.scheduled_date).all()

    return render_template('dispatcher/dashboard.html', pending=pending, active=active)


@dispatcher_bp.route('/requests')
def requests_list():
    """Список заявок с фильтром по статусу"""
    status_code = request.args.get('status', 'pending')
    status_obj = RequestStatus.query.filter_by(code=status_code).first()
    if status_obj:
        requests_list = Request.query.filter_by(status_id=status_obj.id).order_by(Request.created_at.desc()).all()
    else:
        requests_list = []
    return render_template('dispatcher/requests.html', requests=requests_list, current_status=status_code)


@dispatcher_bp.route('/request/<int:request_id>')
def request_detail(request_id):
    """Детали заявки"""
    req = Request.query.get_or_404(request_id)
    return render_template('dispatcher/request_detail.html', request=req)


@dispatcher_bp.route('/request/<int:request_id>/assign', methods=['GET', 'POST'])
def assign_worker(request_id):
    """
    Назначение работника с учётом SVD++ и занятости
    Кнопка у рекомендованного вызывает этот же роут с GET-параметром worker_id
    """
    req = Request.query.get_or_404(request_id)

    if req.status and req.status.code != 'pending':
        flash('Заявка уже обработана', 'warning')
        return redirect(url_for('dispatcher.request_detail', request_id=request_id))

    recommended_workers = get_recommended_workers_svd(req)
    form = AssignWorkerForm()

    worker_role = Role.query.filter_by(code='worker').first()
    all_workers = WorkerProfile.query.join(User).filter(User.is_blocked == False).all()

    eligible_workers = []
    for wp in all_workers:
        user = User.query.get(wp.user_id)
        if user and user.role_id == worker_role.id:
            if wp.city_id == req.city_id:
                if req.service in wp.services:
                    eligible_workers.append(wp)

    recommended_ids = [w.id for w in recommended_workers]
    other_workers = [w for w in eligible_workers if w.id not in recommended_ids]
    recommended_in_eligible = [w for w in recommended_workers if w in eligible_workers]
    sorted_workers = recommended_in_eligible + sorted(other_workers, key=lambda x: x.rating or 0, reverse=True)

    form.worker_id.choices = [(w.id, f"{w.user.full_name} (рейтинг: {w.rating:.1f})") for w in sorted_workers]

    # Быстрое назначение по кнопке у рекомендованного работника
    if request.method == 'GET' and request.args.get('worker_id'):
        try:
            worker_id_from_url = int(request.args.get('worker_id'))
            worker = WorkerProfile.query.get(worker_id_from_url)
            if worker and not worker.user.is_blocked and worker in eligible_workers:
                busy = Request.query.filter(
                    Request.worker_id == worker.id,
                    Request.scheduled_date == req.scheduled_date,
                    Request.status.has(code='assigned') | Request.status.has(code='in_progress')
                ).all()

                is_busy = False
                for b in busy:
                    if not (req.scheduled_time_end <= b.scheduled_time_start or
                            req.scheduled_time_start >= b.scheduled_time_end):
                        is_busy = True
                        break

                if is_busy:
                    flash('Работник занят в это время', 'danger')
                else:
                    req.worker_id = worker.id
                    req.dispatcher_id = get_current_dispatcher().id
                    assigned_status = RequestStatus.query.filter_by(code='assigned').first()
                    req.status_id = assigned_status.id
                    db.session.commit()
                    flash(f'Работник {worker.user.full_name} назначен', 'success')
                    return redirect(url_for('dispatcher.request_detail', request_id=request_id))
            else:
                flash('Работник недоступен для этой заявки', 'warning')
        except ValueError:
            pass

    if form.validate_on_submit():
        worker = WorkerProfile.query.get(form.worker_id.data)
        if worker and not worker.user.is_blocked:
            busy = Request.query.filter(
                Request.worker_id == worker.id,
                Request.scheduled_date == req.scheduled_date,
                Request.status.has(code='assigned') | Request.status.has(code='in_progress')
            ).all()

            is_busy = False
            for b in busy:
                if not (req.scheduled_time_end <= b.scheduled_time_start or
                        req.scheduled_time_start >= b.scheduled_time_end):
                    is_busy = True
                    break

            if is_busy:
                flash('Работник занят в это время', 'danger')
                return redirect(url_for('dispatcher.assign_worker', request_id=request_id))

            req.worker_id = worker.id
            req.dispatcher_id = get_current_dispatcher().id
            assigned_status = RequestStatus.query.filter_by(code='assigned').first()
            req.status_id = assigned_status.id
            db.session.commit()
            flash(f'Работник {worker.user.full_name} назначен', 'success')
            return redirect(url_for('dispatcher.request_detail', request_id=request_id))
        else:
            flash('Работник недоступен', 'danger')

    return render_template('dispatcher/assign_worker.html',
                           request=req, form=form, recommended=recommended_in_eligible)


@dispatcher_bp.route('/request/<int:request_id>/reject', methods=['GET', 'POST'])
def reject_request(request_id):
    """Отклонение заявки с указанием причины"""
    req = Request.query.get_or_404(request_id)
    if req.status and req.status.code != 'pending':
        flash('Заявка уже обработана', 'warning')
        return redirect(url_for('dispatcher.request_detail', request_id=request_id))

    form = RejectRequestForm()
    if form.validate_on_submit():
        rejected_status = RequestStatus.query.filter_by(code='rejected').first()
        req.status_id = rejected_status.id
        req.rejection_reason = form.reason.data
        req.dispatcher_id = get_current_dispatcher().id
        db.session.commit()
        flash('Заявка отклонена', 'success')
        return redirect(url_for('dispatcher.request_detail', request_id=request_id))

    return render_template('dispatcher/reject_request.html', form=form, request=req)


@dispatcher_bp.route('/request/<int:request_id>/chat', methods=['GET', 'POST'])
def chat(request_id):
    """Чат по заявке"""
    req = Request.query.get_or_404(request_id)
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(
            request_id=request_id,
            author_id=current_user.id,
            content=censor_text(form.content.data)
        )
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('dispatcher.chat', request_id=request_id))

    messages = Message.query.filter_by(request_id=request_id).order_by(Message.timestamp).all()
    return render_template('dispatcher/chat.html', request=req, messages=messages, form=form)