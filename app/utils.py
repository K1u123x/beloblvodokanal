"""
Слоты, SVD++, загрузка фото, цензура, сброс пароля
"""
from datetime import datetime, timedelta, date
import datetime as dt
from app.models import Request, Service, WorkerProfile, Review, User, Client
from surprise import SVDpp, Dataset, Reader
from surprise.model_selection import train_test_split
import pandas as pd
from app import db, cache
import os
import secrets
from PIL import Image
from flask import current_app
from itsdangerous import URLSafeTimedSerializer
from flask import url_for

WORK_START = dt.time(8, 30)
WORK_END = dt.time(19, 0)


def generate_time_slots(service_duration=120):
    """Режет рабочий день на равные временные слоты под длительность услуги"""
    slots = []
    current = datetime.combine(date.today(), WORK_START)
    end = datetime.combine(date.today(), WORK_END)
    delta = timedelta(minutes=service_duration)
    while current + delta <= end:
        slots.append(current.time())
        current += delta
    return slots


def get_available_slots(service_id, selected_date):
    """
    Возвращает свободные слоты для услуги на дату
    Слот доступен, если хотя бы один незаблокированный работник с нужной услугой не занят
    """
    service = Service.query.get(service_id)
    if not service:
        return []

    duration = service.duration
    all_slots = generate_time_slots(duration)

    eligible_workers = WorkerProfile.query.join(User).filter(User.is_blocked == False).all()
    eligible_workers = [w for w in eligible_workers if service in w.services]

    if not eligible_workers:
        return []

    busy_requests = Request.query.filter(
        Request.scheduled_date == selected_date,
        Request.status.has(code='assigned') |
        Request.status.has(code='in_progress') |
        Request.status.has(code='completed')
    ).all()

    available = []
    for slot_start in all_slots:
        slot_end = (datetime.combine(selected_date, slot_start) + timedelta(minutes=duration)).time()
        has_free_worker = False

        for worker in eligible_workers:
            worker_busy = False
            for req in busy_requests:
                if req.worker_id == worker.id:
                    if not (slot_end <= req.scheduled_time_start or slot_start >= req.scheduled_time_end):
                        worker_busy = True
                        break
            if not worker_busy:
                has_free_worker = True
                break

        if has_free_worker:
            available.append(slot_start)

    return available


def calculate_worker_rating(worker_id):
    """Пересчитывает рейтинг работника как среднее по всем отзывам"""
    reviews = Review.query.filter_by(worker_id=worker_id).all()
    if reviews:
        avg = sum(r.rating for r in reviews) / len(reviews)
        worker = WorkerProfile.query.get(worker_id)
        if worker:
            worker.rating = avg
            db.session.commit()


def save_news_picture(form_picture):
    """Сохраняет фото новости, сжимая до 1200x800"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/uploads/news', picture_fn)
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)

    output_size = (1200, 800)
    i = Image.open(form_picture)
    i.thumbnail(output_size, Image.Resampling.LANCZOS)
    i.save(picture_path, quality=90, optimize=True)
    return picture_fn


def save_review_photo(form_photo):
    """Сохраняет фото из отзыва, сжимая до 1200x800 с качеством 85%"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_photo.filename)
    photo_fn = random_hex + f_ext
    photo_path = os.path.join(current_app.root_path, 'static/uploads/reviews', photo_fn)
    os.makedirs(os.path.dirname(photo_path), exist_ok=True)

    output_size = (1200, 800)
    i = Image.open(form_photo)
    i.thumbnail(output_size, Image.Resampling.LANCZOS)
    i.save(photo_path, quality=85, optimize=True)
    return photo_fn


from better_profanity import profanity

def censor_text(text):
    """Заменяет нецензурные слова на звёздочки через better_profanity"""
    if not text:
        return text
    return profanity.censor(text)


def generate_reset_token(email):
    """Генерирует токен для сброса пароля, действителен 1 час"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt')


def verify_reset_token(token, expiration=3600):
    """Проверяет токен сброса пароля, возвращает email или False"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except:
        return False
    return email


def send_password_reset_email(user):
    """Выводит ссылку для сброса пароля в консоль сервера (демо-режим)"""
    token = generate_reset_token(user.email)
    user.reset_password_token = token
    user.reset_password_expires = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    reset_url = url_for('auth.reset_password', token=token, _external=True)
    print(f"[СБРОС ПАРОЛЯ] Кому: {user.email} | Ссылка: {reset_url}")
    return token


def send_admin_reset_notification(admin_user, target_user):
    """Уведомляет админа о запросе сброса пароля сотрудником (вывод в консоль)"""
    print(f"[УВЕДОМЛЕНИЕ АДМИНУ] Сотрудник {target_user.email} запросил сброс пароля")


@cache.memoize(timeout=3600)
def get_trained_svd_model():
    """
    Обучает SVD++ на всех отзывах и кеширует на час
    При нехватке данных (< 5 отзывов) возвращает None
    """
    reviews = Review.query.all()
    if len(reviews) < 5:
        return None

    data = [[r.client_id, r.worker_id, r.rating] for r in reviews]
    df = pd.DataFrame(data, columns=['user', 'item', 'rating'])
    reader = Reader(rating_scale=(1, 5))
    dataset = Dataset.load_from_df(df[['user', 'item', 'rating']], reader)
    trainset = dataset.build_full_trainset()
    algo = SVDpp()
    algo.fit(trainset)
    return algo


def predict_rating_svd(algo, client_id, worker_id):
    """
    Предсказывает рейтинг для пары клиент-работник
    Добавляет бонус за свежие отзывы: +0.3 если < 30 дней, +0.15 если < 90 дней
    """
    try:
        pred = algo.predict(client_id, worker_id)
        base_rating = pred.est

        recent_reviews = Review.query.filter_by(
            client_id=client_id, worker_id=worker_id
        ).order_by(Review.created_at.desc()).limit(3).all()

        if recent_reviews:
            time_bonus = 0
            for i, review in enumerate(recent_reviews):
                days_old = (datetime.utcnow() - review.created_at).days
                if days_old < 30:
                    time_bonus += 0.3 * (1 - i * 0.1)
                elif days_old < 90:
                    time_bonus += 0.15 * (1 - i * 0.1)
            base_rating = min(5.0, base_rating + time_bonus)

        return base_rating
    except:
        return None


def get_recommended_workers_svd(req):
    """
    Возвращает подходящих работников, отсортированных по predicted rating
    Фильтрует по городу, услуге, блокировке и занятости на время заявки
    Итоговый score = pred * 10 - активные_заявки * 3
    """
    service = req.service
    request_city_id = req.city_id
    request_date = req.scheduled_date
    request_start = req.scheduled_time_start
    request_end = req.scheduled_time_end

    workers = WorkerProfile.query.join(User).filter(User.is_blocked == False).all()

    eligible = []
    for w in workers:
        if service not in w.services:
            continue
        if w.city_id is None or w.city_id != request_city_id:
            continue

        busy = Request.query.filter(
            Request.worker_id == w.id,
            Request.scheduled_date == request_date,
            Request.status.has(code='assigned') | Request.status.has(code='in_progress')
        ).all()

        is_busy = False
        for b in busy:
            if not (request_end <= b.scheduled_time_start or request_start >= b.scheduled_time_end):
                is_busy = True
                break

        if not is_busy:
            eligible.append(w)

    if not eligible:
        return []

    algo = get_trained_svd_model()
    client_id = req.client_id

    scored = []
    for w in eligible:
        if algo:
            pred = predict_rating_svd(algo, client_id, w.id)
            if pred is None:
                pred = w.rating
        else:
            pred = w.rating

        active = Request.query.filter_by(worker_id=w.id).filter(
            Request.status.has(code='assigned') | Request.status.has(code='in_progress')
        ).count()

        score = pred * 10 - active * 3
        scored.append((w, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [w for w, s in scored]