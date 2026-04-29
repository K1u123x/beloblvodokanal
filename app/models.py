"""
Модели базы данных: пользователи, профили, заявки, отзывы, новости
"""
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

# Связка работников и услуг (многие ко многим)
worker_services = db.Table(
    'worker_services',
    db.Column('worker_id', db.Integer, db.ForeignKey('worker_profile.id', ondelete='CASCADE'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)


class City(db.Model):
    """Города обслуживания (Губкин, Старый Оскол и др.)"""
    __tablename__ = 'city'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    region = db.Column(db.String(100), default='Белгородская область')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<City {self.name}>'


class Role(db.Model):
    """Роли: admin, dispatcher, worker, client"""
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'


class RequestStatus(db.Model):
    """Статусы заявки: pending, assigned, in_progress, completed, rejected"""
    __tablename__ = 'request_status'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name_ru = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20), default='secondary')
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    requests = db.relationship('Request', backref='status', lazy='dynamic')

    def __repr__(self):
        return f'<RequestStatus {self.name_ru}>'


class User(UserMixin, db.Model):
    """
    Базовый аккаунт для всех ролей
    Блокировка работает на уровне пользователя (is_blocked)
    Пароль хешируется через werkzeug (scrypt)
    """
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    patronymic = db.Column(db.String(64))

    is_blocked = db.Column(db.Boolean, default=False, index=True)
    block_reason = db.Column(db.Text)

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)

    email_confirmed = db.Column(db.Boolean, default=True)
    email_confirmed_at = db.Column(db.DateTime)
    phone_confirmed = db.Column(db.Boolean, default=True)
    phone_confirmed_at = db.Column(db.DateTime)

    confirmation_token = db.Column(db.String(128))
    reset_password_token = db.Column(db.String(128))
    reset_password_expires = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client_profile = db.relationship('Client', backref='user', uselist=False, cascade='all, delete-orphan')
    worker_profile = db.relationship('WorkerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    dispatcher_profile = db.relationship('DispatcherProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.patronymic or ''}".strip()

    @property
    def is_admin(self):
        return self.role.code == 'admin' if self.role else False

    @property
    def is_dispatcher(self):
        return self.role.code == 'dispatcher' if self.role else False

    @property
    def is_worker(self):
        return self.role.code == 'worker' if self.role else False

    @property
    def is_client(self):
        return self.role.code == 'client' if self.role else False

    def __repr__(self):
        return f'<User {self.email}>'


class Client(db.Model):
    """Профиль клиента с адресом, адрес копируется в заявку при создании"""
    __tablename__ = 'client'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    street = db.Column(db.String(200))
    house = db.Column(db.String(20))
    apartment = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requests = db.relationship('Request', backref='client', lazy='dynamic')
    reviews = db.relationship('Review', backref='client', lazy='dynamic')

    @property
    def full_address(self):
        if not self.city_id:
            return f"{self.street}, д. {self.house}" + (f", кв. {self.apartment}" if self.apartment else "")
        city_name = self.city.name if self.city else ""
        return f"{city_name}, {self.street}, д. {self.house}" + (f", кв. {self.apartment}" if self.apartment else "")

    def __repr__(self):
        return f'<Client {self.user.full_name if self.user else "Unknown"}>'


class DispatcherProfile(db.Model):
    """Профиль диспетчера, без рейтинга и портфолио"""
    __tablename__ = 'dispatcher_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    hire_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dispatched_requests = db.relationship('Request', backref='dispatcher', lazy='dynamic',
                                          foreign_keys='Request.dispatcher_id')

    @property
    def full_name(self):
        return self.user.full_name if self.user else "Unknown"

    def __repr__(self):
        return f'<DispatcherProfile {self.full_name}>'


class WorkerProfile(db.Model):
    """Профиль работника: рейтинг, услуги, портфолио, заявки"""
    __tablename__ = 'worker_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    rating = db.Column(db.Float, default=0.0)
    hire_date = db.Column(db.Date)
    about_me = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    services = db.relationship('Service', secondary=worker_services, backref=db.backref('workers', lazy='dynamic'))
    assigned_requests = db.relationship('Request', backref='worker', lazy='dynamic', foreign_keys='Request.worker_id')
    reviews_received = db.relationship('Review', backref='worker', lazy='dynamic', foreign_keys='Review.worker_id')
    news_created = db.relationship('News', backref='author', lazy='dynamic')

    @property
    def full_name(self):
        return self.user.full_name if self.user else "Unknown"

    @property
    def experience_years(self):
        if self.hire_date:
            return (date.today() - self.hire_date).days // 365
        return 0

    def get_portfolio_photos(self, limit=6):
        """Возвращает фото из отзывов, отмеченных для портфолио"""
        reviews_with_photos = Review.query.filter_by(worker_id=self.id, in_portfolio=True)\
            .filter(Review.photo.isnot(None))\
            .order_by(Review.created_at.desc())\
            .limit(limit).all()
        return [r.photo for r in reviews_with_photos]

    def __repr__(self):
        return f'<WorkerProfile {self.full_name} (rating: {self.rating})>'


class Service(db.Model):
    """Услуги из прейскуранта водоканала"""
    __tablename__ = 'service'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer, default=120)
    icon = db.Column(db.String(50), default='bi-droplet-half')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requests = db.relationship('Request', backref='service', lazy='dynamic')

    def __repr__(self):
        return f'<Service {self.name}>'


class Request(db.Model):
    """
    Заявка на услугу
    Адрес дублируется из профиля клиента для сохранения истории
    """
    __tablename__ = 'request'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    dispatcher_id = db.Column(db.Integer, db.ForeignKey('dispatcher_profile.id'), nullable=True, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker_profile.id'), nullable=True, index=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    street = db.Column(db.String(200))
    house = db.Column(db.String(20))
    apartment = db.Column(db.String(20))
    description = db.Column(db.Text)
    status_id = db.Column(db.Integer, db.ForeignKey('request_status.id'), nullable=False, default=1)
    scheduled_date = db.Column(db.Date, nullable=False, index=True)
    scheduled_time_start = db.Column(db.Time, nullable=False)
    scheduled_time_end = db.Column(db.Time, nullable=False)
    completed_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship('Message', backref='request', lazy='dynamic', cascade='all, delete-orphan')
    review = db.relationship('Review', backref='request', uselist=False, cascade='all, delete-orphan')

    @property
    def full_address(self):
        city_name = self.city.name if self.city else ""
        address = f"{self.street}, д. {self.house}"
        if self.apartment:
            address += f", кв. {self.apartment}"
        return f"{city_name}, {address}" if city_name else address

    @property
    def status_ru(self):
        return self.status.name_ru if self.status else None

    @property
    def status_code(self):
        return self.status.code if self.status else None

    def __repr__(self):
        return f'<Request #{self.id} [{self.status_code}]>'


class Message(db.Model):
    """Сообщение в чате заявки"""
    __tablename__ = 'message'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id', ondelete='CASCADE'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<Message #{self.id}>'


class Review(db.Model):
    """Отзыв клиента о работе, может содержать фото и флаг для портфолио"""
    __tablename__ = 'review'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id', ondelete='CASCADE'), nullable=False, unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker_profile.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    photo = db.Column(db.String(200))
    in_portfolio = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Review #{self.id} - {self.rating}>'


class News(db.Model):
    """Новость компании, может быть скрыта (is_published=False)"""
    __tablename__ = 'news'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(300))
    image_filename = db.Column(db.String(100))
    author_id = db.Column(db.Integer, db.ForeignKey('worker_profile.id'), nullable=True)
    is_published = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<News {self.title}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))