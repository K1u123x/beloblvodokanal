"""
Публичные страницы: главная, новости, контакты, профили работников
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from app import db
from app.models import Service, Review, News, WorkerProfile, Request, RequestStatus
from sqlalchemy import func

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def index():
    """Главная страница с популярными услугами, отзывами и новостями"""
    services = Service.query.limit(6).all()
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(5).all()
    news_items = News.query.filter_by(is_published=True).order_by(News.created_at.desc()).limit(3).all()
    return render_template('index.html', services=services, reviews=recent_reviews, news_items=news_items)


@index_bp.route('/about/history')
def about_history():
    return render_template('about/history.html')


@index_bp.route('/about/management')
def about_management():
    return render_template('about/management.html')


@index_bp.route('/about/vacancies')
def about_vacancies():
    return render_template('about/vacancies.html')


@index_bp.route('/clients/tariffs')
def clients_tariffs():
    return render_template('clients/tariffs.html')


@index_bp.route('/clients/meter-readings')
def clients_meter_readings():
    return render_template('clients/meter_readings.html')


@index_bp.route('/clients/faq')
def clients_faq():
    return render_template('clients/faq.html')


@index_bp.route('/contacts')
def contacts():
    return render_template('contacts.html')


@index_bp.route('/news/<int:news_id>')
def news_detail(news_id):
    """Детальная страница новости с блоком других новостей"""
    news = News.query.get_or_404(news_id)
    other_news = News.query.filter(
        News.id != news_id,
        News.is_published == True
    ).order_by(News.created_at.desc()).limit(3).all()
    return render_template('news_detail.html', news=news, other_news=other_news)


@index_bp.route('/worker/<int:worker_id>')
def worker_profile(worker_id):
    """
    Публичный профиль работника
    Показывает рейтинг, выполненные заявки, портфолио и топ-3 услуги по популярности
    """
    worker = WorkerProfile.query.get_or_404(worker_id)

    if worker.user and worker.user.role and worker.user.role.code != 'worker':
        flash('Профиль не найден', 'danger')
        return redirect(url_for('index.index'))

    completed_status = RequestStatus.query.filter_by(code='completed').first()
    completed_requests = Request.query.filter_by(
        worker_id=worker.id,
        status_id=completed_status.id
    ).count() if completed_status else 0

    portfolio = worker.get_portfolio_photos(limit=6)

    # Топ услуг по количеству выполненных заявок
    popular_services = db.session.query(
        Service, func.count(Request.id).label('count')
    ).join(Request).filter(
        Request.worker_id == worker.id,
        Request.status_id == completed_status.id
    ).group_by(Service.id).order_by(func.count(Request.id).desc()).all()

    all_services = list(worker.services)
    popular_ids = [s.id for s, _ in popular_services]
    sorted_services = [s for s, _ in popular_services if s in all_services]
    sorted_services += [s for s in all_services if s.id not in popular_ids]

    top_services = sorted_services[:3]
    remaining_count = len(sorted_services) - 3

    recent_reviews = Review.query.filter_by(worker_id=worker.id).order_by(
        Review.created_at.desc()
    ).limit(4).all()

    return render_template('worker/public_profile.html',
                           worker=worker,
                           completed_requests=completed_requests,
                           portfolio=portfolio,
                           top_services=top_services,
                           remaining_count=remaining_count,
                           recent_reviews=recent_reviews)