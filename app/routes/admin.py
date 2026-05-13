"""
Админ-панель: пользователи, города, услуги, новости, отзывы, отчёты, экспорт
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app import db
from app.models import User, Client, WorkerProfile, DispatcherProfile, City, Role, RequestStatus, Service, Request, Review, News
from app.utils import calculate_worker_rating, save_news_picture
from app.forms import ServiceForm, UserCreateForm, ReportForm, CityForm, NewsForm
from datetime import datetime, timedelta, date
import io
import os
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
def restrict_admin():
    if not current_user.role or current_user.role.code != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index.index'))


@admin_bp.route('/dashboard')
def dashboard():
    """Панель администратора со статистикой и графиками"""
    users_count = User.query.count()
    workers_count = WorkerProfile.query.count()
    requests_count = Request.query.count()
    completed_status = RequestStatus.query.filter_by(code='completed').first()
    completed_count = Request.query.filter_by(status_id=completed_status.id).count() if completed_status else 0
    return render_template('admin/dashboard.html',
                           users=users_count, workers=workers_count,
                           requests=requests_count, completed=completed_count)


# Города

@admin_bp.route('/cities')
def cities():
    all_cities = City.query.order_by(City.name).all()
    return render_template('admin/cities.html', cities=all_cities)


@admin_bp.route('/city/create', methods=['GET', 'POST'])
def create_city():
    form = CityForm()
    if form.validate_on_submit():
        city = City(name=form.name.data, region=form.region.data, is_active=form.is_active.data)
        db.session.add(city)
        db.session.commit()
        flash('Город добавлен', 'success')
        return redirect(url_for('admin.cities'))
    return render_template('admin/city_form.html', form=form, title='Добавление города')


@admin_bp.route('/city/<int:city_id>/edit', methods=['GET', 'POST'])
def edit_city(city_id):
    city = City.query.get_or_404(city_id)
    form = CityForm(obj=city)
    if form.validate_on_submit():
        form.populate_obj(city)
        db.session.commit()
        flash('Город обновлён', 'success')
        return redirect(url_for('admin.cities'))
    return render_template('admin/city_form.html', form=form, title='Редактирование города')


@admin_bp.route('/city/<int:city_id>/delete')
def delete_city(city_id):
    city = City.query.get_or_404(city_id)
    if city.clients.count() > 0:
        flash('Нельзя удалить город с клиентами', 'danger')
    else:
        db.session.delete(city)
        db.session.commit()
        flash('Город удалён', 'success')
    return redirect(url_for('admin.cities'))


# Пользователи

@admin_bp.route('/users')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/user/<int:user_id>/block', methods=['GET', 'POST'])
def block_user(user_id):
    """Блокировка/разблокировка пользователя, нельзя заблокировать себя"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Нельзя заблокировать самого себя', 'danger')
        return redirect(url_for('admin.users'))

    if request.method == 'POST':
        reason = request.form.get('block_reason', '')
        user.is_blocked = not user.is_blocked
        user.block_reason = reason if reason else None
        db.session.commit()
        flash('Пользователь заблокирован' if user.is_blocked else 'Пользователь разблокирован', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/block_user.html', user=user)


@admin_bp.route('/user/create', methods=['GET', 'POST'])
def create_user():
    """Создание пользователя с профилем в зависимости от роли"""
    form = UserCreateForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data, phone=form.phone.data,
            last_name=form.last_name.data, first_name=form.first_name.data,
            patronymic=form.patronymic.data, role_id=form.role_id.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        role = db.session.get(Role, form.role_id.data)
        if role and role.code in ['admin', 'dispatcher', 'worker']:
            if role.code == 'worker':
                wp = WorkerProfile(user_id=user.id, hire_date=date.today())
                db.session.add(wp)
                db.session.flush()
                if form.services.data:
                    services = Service.query.filter(Service.id.in_(form.services.data)).all()
                    wp.services.extend(services)
            elif role.code == 'dispatcher':
                dp = DispatcherProfile(user_id=user.id, hire_date=date.today())
                db.session.add(dp)
        else:
            client = Client(user_id=user.id, city_id=form.city_id.data,
                            street=form.street.data, house=form.house.data,
                            apartment=form.apartment.data)
            db.session.add(client)

        db.session.commit()
        flash('Пользователь создан', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/create_user.html', form=form)


# Услуги

@admin_bp.route('/services')
def services():
    all_services = Service.query.order_by(Service.name).all()
    return render_template('admin/services.html', services=all_services)


@admin_bp.route('/service/create', methods=['GET', 'POST'])
def create_service():
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(name=form.name.data, description=form.description.data,
                          price=form.price.data, duration=form.duration.data, icon=form.icon.data)
        db.session.add(service)
        db.session.commit()
        flash('Услуга добавлена', 'success')
        return redirect(url_for('admin.services'))
    return render_template('admin/service_form.html', form=form, title='Добавление услуги')


@admin_bp.route('/service/<int:service_id>/edit', methods=['GET', 'POST'])
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    form = ServiceForm(obj=service)
    if form.validate_on_submit():
        form.populate_obj(service)
        db.session.commit()
        flash('Услуга обновлена', 'success')
        return redirect(url_for('admin.services'))
    return render_template('admin/service_form.html', form=form, title='Редактирование услуги')


@admin_bp.route('/service/<int:service_id>/delete')
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    if service.requests.count() > 0:
        flash('Нельзя удалить услугу с заявками', 'danger')
    else:
        db.session.delete(service)
        db.session.commit()
        flash('Услуга удалена', 'success')
    return redirect(url_for('admin.services'))


# Отзывы

@admin_bp.route('/reviews')
def reviews():
    page = request.args.get('page', 1, type=int)
    pagination = Review.query.order_by(Review.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('admin/reviews.html', reviews=pagination.items, pagination=pagination)


@admin_bp.route('/review/<int:review_id>/delete')
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    worker_id = review.worker_id
    db.session.delete(review)
    db.session.commit()
    calculate_worker_rating(worker_id)
    flash('Отзыв удалён', 'success')
    return redirect(url_for('admin.reviews'))


# Отчёты

@admin_bp.route('/reports', methods=['GET', 'POST'])
def reports():
    """Отчёты с фильтрами и сортировкой"""
    form = ReportForm()
    requests_list = []
    stats = {'total': 0, 'total_price': 0, 'completed': 0, 'avg_price': 0}

    if form.validate_on_submit():
        query = Request.query
        if form.start_date.data:
            query = query.filter(Request.scheduled_date >= form.start_date.data)
        if form.end_date.data:
            query = query.filter(Request.scheduled_date <= form.end_date.data)
        if form.worker_id.data and form.worker_id.data != 0:
            query = query.filter_by(worker_id=form.worker_id.data)
        if form.city_id.data and form.city_id.data != 0:
            query = query.filter_by(city_id=form.city_id.data)
        if form.status_id.data and form.status_id.data != 0:
            query = query.filter_by(status_id=form.status_id.data)
        if form.service_id.data and form.service_id.data != 0:
            query = query.filter_by(service_id=form.service_id.data)

        sort_by = form.sort_by.data
        if sort_by == 'scheduled_date_desc':
            query = query.order_by(Request.scheduled_date.desc())
        elif sort_by == 'scheduled_date_asc':
            query = query.order_by(Request.scheduled_date.asc())
        elif sort_by == 'price_desc':
            query = query.join(Service).order_by(Service.price.desc())
        elif sort_by == 'price_asc':
            query = query.join(Service).order_by(Service.price.asc())
        elif sort_by == 'status':
            query = query.join(RequestStatus).order_by(RequestStatus.order)
        else:
            query = query.order_by(Request.scheduled_date.desc())

        requests_list = query.all()
        stats['total'] = len(requests_list)
        stats['total_price'] = sum(r.service.price for r in requests_list if r.service)
        completed_status = RequestStatus.query.filter_by(code='completed').first()
        stats['completed'] = sum(1 for r in requests_list if r.status_id == completed_status.id)
        stats['avg_price'] = round(stats['total_price'] / stats['total'], 2) if stats['total'] > 0 else 0

    return render_template('admin/reports.html', form=form, requests=requests_list, stats=stats)


@admin_bp.route('/reports/export/excel')
@login_required
def export_excel():
    """Экспорт отчёта в Excel"""
    start = request.args.get('start')
    end = request.args.get('end')
    worker = request.args.get('worker', type=int)
    city = request.args.get('city', type=int)
    status = request.args.get('status', type=int)
    service = request.args.get('service', type=int)

    query = Request.query
    if start:
        query = query.filter(Request.scheduled_date >= datetime.strptime(start, '%Y-%m-%d').date())
    if end:
        query = query.filter(Request.scheduled_date <= datetime.strptime(end, '%Y-%m-%d').date())
    if worker and worker != 0:
        query = query.filter_by(worker_id=worker)
    if city and city != 0:
        query = query.filter_by(city_id=city)
    if status and status != 0:
        query = query.filter_by(status_id=status)
    if service and service != 0:
        query = query.filter_by(service_id=service)

    requests_data = query.order_by(Request.scheduled_date).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Отчёт по заявкам"
    ws.append(['ID', 'Дата', 'Время', 'Услуга', 'Клиент', 'Телефон', 'Город', 'Адрес', 'Работник', 'Статус', 'Цена'])

    for r in requests_data:
        client_phone = r.client.user.phone if r.client and r.client.user else '—'
        city_name = r.city.name if r.city else '—'
        address = f"{r.street}, д.{r.house}"
        if r.apartment:
            address += f", кв.{r.apartment}"

        ws.append([
            r.id,
            r.scheduled_date.strftime('%d.%m.%Y') if r.scheduled_date else '',
            r.scheduled_time_start.strftime('%H:%M') if r.scheduled_time_start else '',
            r.service.name if r.service else '',
            r.client.user.full_name if r.client and r.client.user else '',
            client_phone, city_name, address,
            r.worker.full_name if r.worker else '—',
            r.status_ru,
            f"{r.service.price} ₽" if r.service else ''
        ])

    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[col_letter].width = min(max_length + 2, 50)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, download_name=f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx', as_attachment=True)


@admin_bp.route('/reports/export/pdf')
@login_required
def export_pdf():
    """Экспорт отчёта в PDF (альбомная ориентация)"""
    start = request.args.get('start')
    end = request.args.get('end')
    worker = request.args.get('worker', type=int)
    city = request.args.get('city', type=int)
    status = request.args.get('status', type=int)
    service = request.args.get('service', type=int)

    query = Request.query
    if start:
        query = query.filter(Request.scheduled_date >= datetime.strptime(start, '%Y-%m-%d').date())
    if end:
        query = query.filter(Request.scheduled_date <= datetime.strptime(end, '%Y-%m-%d').date())
    if worker and worker != 0:
        query = query.filter_by(worker_id=worker)
    if city and city != 0:
        query = query.filter_by(city_id=city)
    if status and status != 0:
        query = query.filter_by(status_id=status)
    if service and service != 0:
        query = query.filter_by(service_id=service)

    requests_data = query.order_by(Request.scheduled_date).all()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    try:
        pdfmetrics.registerFont(TTFont('DejaVu', 'app/static/fonts/DejaVuSans.ttf'))
        font_name = 'DejaVu'
    except:
        font_name = 'Helvetica'

    def draw_wrapped_text(canvas_obj, text, x, y, max_width, font_size=8):
        canvas_obj.setFont(font_name, font_size)
        words = str(text).split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if canvas_obj.stringWidth(test_line, font_name, font_size) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        if not lines:
            lines = [text[:int(max_width / 4)] + '...']
        for line in lines:
            canvas_obj.drawString(x, y, line)
            y -= font_size + 3
        return y, len(lines)

    p.setFont(font_name, 12)
    p.drawString(25, height - 30, "Отчёт по заявкам Белоблводоканал")
    p.setFont(font_name, 8)
    p.drawString(25, height - 48, f"Сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    if start:
        period = f"Период: с {start}"
        if end:
            period += f" по {end}"
        p.drawString(25, height - 63, period)

    headers = ['ID', 'Дата', 'Время', 'Услуга', 'Клиент', 'Город', 'Адрес', 'Работник', 'Статус', 'Цена']
    col_widths = [22, 48, 38, 95, 90, 55, 110, 85, 60, 42]
    col_starts = [25]
    for i in range(1, len(col_widths)):
        col_starts.append(col_starts[-1] + col_widths[i-1])

    y = height - 80
    p.setFont(font_name, 7.5)
    for i, h in enumerate(headers):
        p.drawString(col_starts[i], y, h)
    p.setLineWidth(1)
    p.line(25, y - 4, col_starts[-1] + col_widths[-1], y - 4)
    y -= 16

    p.setFont(font_name, 7)
    for r in requests_data:
        if y < 60:
            p.showPage()
            p.setFont(font_name, 7.5)
            y = height - 30
            for i, h in enumerate(headers):
                p.drawString(col_starts[i], y, h)
            p.line(25, y - 4, col_starts[-1] + col_widths[-1], y - 4)
            y -= 16
            p.setFont(font_name, 7)

        city = db.session.get(City, r.city_id) if r.city_id else None
        city_name = city.name if city else ''
        address_full = f"{r.street}, д.{r.house}"
        if r.apartment:
            address_full += f", кв.{r.apartment}"

        row_data = [
            str(r.id),
            r.scheduled_date.strftime('%d.%m.%Y') if r.scheduled_date else '',
            r.scheduled_time_start.strftime('%H:%M') if r.scheduled_time_start else '',
            r.service.name if r.service else '',
            r.client.user.full_name if r.client and r.client.user else '',
            city_name, address_full,
            r.worker.full_name if r.worker else '—',
            r.status_ru,
            f"{r.service.price} ₽" if r.service else ''
        ]

        max_lines = 1
        for i, cell in enumerate(row_data):
            _, lines = draw_wrapped_text(p, cell, 0, 0, col_widths[i] - 4, 7)
            max_lines = max(max_lines, lines)

        start_y = y
        for i, cell in enumerate(row_data):
            draw_wrapped_text(p, str(cell), col_starts[i], start_y, col_widths[i] - 4, 7)

        y = start_y - (max_lines * 9) - 4
        p.setStrokeGray(0.7)
        p.setLineWidth(0.3)
        p.line(25, y + 3, col_starts[-1] + col_widths[-1], y + 3)
        p.setStrokeGray(0)
        p.setLineWidth(1)
        y -= 4

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name=f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf', as_attachment=True)


# Новости

@admin_bp.route('/news')
def news_list():
    all_news = News.query.order_by(News.created_at.desc()).all()
    return render_template('admin/news_list.html', news=all_news)


@admin_bp.route('/news/create', methods=['GET', 'POST'])
def create_news():
    form = NewsForm()
    if form.validate_on_submit():
        worker = WorkerProfile.query.filter_by(user_id=current_user.id).first()
        news = News(title=form.title.data, summary=form.summary.data, content=form.content.data,
                    is_published=form.is_published.data, author_id=worker.id if worker else None)
        if form.image.data:
            news.image_filename = save_news_picture(form.image.data)
        db.session.add(news)
        db.session.commit()
        flash('Новость создана', 'success')
        return redirect(url_for('admin.news_list'))
    return render_template('admin/news_form.html', form=form, title='Добавление новости', legend='Добавление новости')


@admin_bp.route('/news/<int:news_id>/edit', methods=['GET', 'POST'])
def edit_news(news_id):
    news = News.query.get_or_404(news_id)
    form = NewsForm(obj=news)
    if form.validate_on_submit():
        form.populate_obj(news)
        if form.image.data:
            if news.image_filename:
                old_path = os.path.join(current_app.root_path, 'static/uploads/news', news.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            news.image_filename = save_news_picture(form.image.data)
        db.session.commit()
        flash('Новость обновлена', 'success')
        return redirect(url_for('admin.news_list'))
    return render_template('admin/news_form.html', form=form, title='Редактирование новости', legend='Редактирование новости')


@admin_bp.route('/news/<int:news_id>/delete')
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    if news.image_filename:
        pic_path = os.path.join(current_app.root_path, 'static/uploads/news', news.image_filename)
        if os.path.exists(pic_path):
            os.remove(pic_path)
    db.session.delete(news)
    db.session.commit()
    flash('Новость удалена', 'success')
    return redirect(url_for('admin.news_list'))


@admin_bp.route('/chart-data')
@login_required
def chart_data():
    """JSON с данными для графиков на дашборде админа"""
    days = []
    requests_by_day = []
    today = date.today()

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days.append(day.strftime('%d.%m'))
        requests_by_day.append(Request.query.filter(Request.scheduled_date == day).count())

    statuses = RequestStatus.query.order_by('order').all()
    status_labels = [s.name_ru for s in statuses]
    status_counts = [Request.query.filter_by(status_id=s.id).count() for s in statuses]
    status_colors = []
    for s in statuses:
        if s.color == 'warning': status_colors.append('#ffc107')
        elif s.color == 'primary': status_colors.append('#0d6efd')
        elif s.color == 'info': status_colors.append('#0dcaf0')
        elif s.color == 'success': status_colors.append('#198754')
        elif s.color == 'danger': status_colors.append('#dc3545')
        else: status_colors.append('#6c757d')

    top_services = db.session.query(Service.name, func.count(Request.id).label('count'))\
        .join(Request).group_by(Service.id).order_by(func.count(Request.id).desc()).limit(5).all()
    top_services_names = [s[0] for s in top_services]
    top_services_counts = [s[1] for s in top_services]

    return jsonify({
        'days': days,
        'requests_by_day': requests_by_day,
        'status_labels': status_labels,
        'status_counts': status_counts,
        'status_colors': status_colors,
        'top_services_names': top_services_names,
        'top_services_counts': top_services_counts
    })