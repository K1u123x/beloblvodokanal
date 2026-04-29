"""
Формы ввода и валидации: вход, регистрация, заявки, админка
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, FloatField, IntegerField, DateField, TimeField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange, ValidationError
from app.models import User, Service, City, Role, WorkerProfile
from flask_wtf.file import FileField, FileAllowed, FileRequired
import re


def validate_phone(form, field):
    """Проверяет, что номер содержит 11 цифр и начинается с 7 или 8"""
    if field.data:
        phone_clean = re.sub(r'\D', '', field.data)
        if len(phone_clean) != 11:
            raise ValidationError('Номер телефона должен содержать 11 цифр')
        if not phone_clean.startswith(('7', '8')):
            raise ValidationError('Номер должен начинаться с +7 или 8')


def validate_password_strength(form, field):
    """Пароль: минимум 8 символов, хотя бы одна цифра и одна буква"""
    password = field.data
    if len(password) < 8:
        raise ValidationError('Пароль должен быть не менее 8 символов')
    if not re.search(r'\d', password):
        raise ValidationError('Пароль должен содержать хотя бы одну цифру')
    if not re.search(r'[a-zA-Zа-яА-Я]', password):
        raise ValidationError('Пароль должен содержать хотя бы одну букву')


def validate_name(form, field):
    """Имя/фамилия: только буквы, пробел и дефис, минимум 2 символа"""
    value = field.data.strip()
    if len(value) < 2:
        raise ValidationError('Минимум 2 символа')
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z\- ]+$', value):
        raise ValidationError('Допустимы только буквы, пробел и дефис')


class LoginForm(FlaskForm):
    """Вход в систему"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    """Регистрация нового клиента с адресом"""
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(min=2, max=64), validate_name])
    first_name = StringField('Имя', validators=[DataRequired(), Length(min=2, max=64), validate_name])
    patronymic = StringField('Отчество', validators=[Optional(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(message='Введите корректный email'), Length(max=120)])
    phone = StringField('Телефон', validators=[DataRequired(message='Телефон обязателен'), Length(min=11, max=20), validate_phone])
    city_id = SelectField('Город', coerce=int, validators=[DataRequired(message='Выберите город')])
    street = StringField('Улица', validators=[DataRequired(), Length(min=2, max=200)])
    house = StringField('Дом', validators=[DataRequired(), Length(min=1, max=20)])
    apartment = StringField('Квартира', validators=[Optional(), Length(max=20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=8, max=64), validate_password_strength])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password', message='Пароли должны совпадать')])
    submit = SubmitField('Зарегистрироваться')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city_id.choices = [(c.id, c.name) for c in City.query.filter_by(is_active=True).all()]

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('Этот email уже используется')

    def validate_phone(self, phone):
        if phone.data and User.query.filter_by(phone=phone.data).first():
            raise ValidationError('Этот телефон уже используется')


class EditProfileForm(FlaskForm):
    """Редактирование профиля клиента"""
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(max=64)])
    first_name = StringField('Имя', validators=[DataRequired(), Length(max=64)])
    patronymic = StringField('Отчество', validators=[Optional(), Length(max=64)])
    phone = StringField('Телефон', validators=[Optional(), Length(max=20)])
    city_id = SelectField('Город', coerce=int, validators=[DataRequired()])
    street = StringField('Улица', validators=[DataRequired(), Length(max=200)])
    house = StringField('Дом', validators=[DataRequired(), Length(max=20)])
    apartment = StringField('Квартира', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city_id.choices = [(c.id, c.name) for c in City.query.filter_by(is_active=True).all()]


class RequestForm(FlaskForm):
    """Форма бронирования услуги"""
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(max=64)])
    first_name = StringField('Имя', validators=[DataRequired(), Length(max=64)])
    patronymic = StringField('Отчество', validators=[Optional(), Length(max=64)])
    city_id = SelectField('Город', coerce=int, validators=[DataRequired()])
    street = StringField('Улица', validators=[DataRequired(), Length(max=200)])
    house = StringField('Дом', validators=[DataRequired(), Length(max=20)])
    apartment = StringField('Квартира', validators=[Optional(), Length(max=20)])
    description = TextAreaField('Описание проблемы', validators=[Optional(), Length(max=500)])
    service_id = SelectField('Услуга', coerce=int, validators=[DataRequired()])
    scheduled_date = DateField('Дата', format='%Y-%m-%d', validators=[DataRequired()])
    scheduled_time_start = TimeField('Время начала', format='%H:%M', validators=[DataRequired()])
    submit = SubmitField('Забронировать')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city_id.choices = [(c.id, c.name) for c in City.query.filter_by(is_active=True).all()]
        self.service_id.choices = [(s.id, f"{s.name} - {s.price} руб.") for s in Service.query.all()]


class AssignWorkerForm(FlaskForm):
    """Назначение работника: только незаблокированные с ролью worker"""
    worker_id = SelectField('Работник', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Назначить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        worker_role = Role.query.filter_by(code='worker').first()
        workers = WorkerProfile.query.join(User).filter(
            User.is_blocked == False, User.role_id == worker_role.id
        ).all()
        self.worker_id.choices = [(w.id, f"{w.full_name} (рейтинг: {w.rating:.1f})") for w in workers]


class RejectRequestForm(FlaskForm):
    """Отклонение заявки с обязательной причиной"""
    reason = TextAreaField('Причина отклонения', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Отклонить заявку')


class MessageForm(FlaskForm):
    """Сообщение в чате"""
    content = TextAreaField('Сообщение', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Отправить')


class ReviewForm(FlaskForm):
    """Отзыв о выполненной заявке, можно прикрепить фото"""
    rating = SelectField('Оценка', choices=[(5, '5'), (4, '4'), (3, '3'), (2, '2'), (1, '1')], coerce=int, validators=[DataRequired()])
    comment = TextAreaField('Комментарий', validators=[Optional(), Length(max=500)])
    photo = FileField('Фото результата', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения')])
    submit = SubmitField('Оставить отзыв')


class ServiceForm(FlaskForm):
    """Создание/редактирование услуги"""
    name = StringField('Название услуги', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Описание', validators=[Optional(), Length(max=500)])
    price = FloatField('Цена (руб.)', validators=[DataRequired(), NumberRange(min=0)])
    duration = IntegerField('Длительность (минут)', validators=[DataRequired(), NumberRange(min=30, max=480)])
    icon = SelectField('Иконка', choices=[
        ('bi-droplet-half', 'Капля'), ('bi-wrench', 'Гаечный ключ'), ('bi-tools', 'Инструменты'),
        ('bi-thermometer-half', 'Термометр'), ('bi-speedometer2', 'Счётчик'), ('bi-water', 'Вода'),
        ('bi-pipe', 'Труба'), ('bi-fire', 'Огонь'), ('bi-search', 'Поиск'), ('bi-gear', 'Шестерня'),
    ], default='bi-droplet-half')
    submit = SubmitField('Сохранить')


class UserCreateForm(FlaskForm):
    """Создание пользователя админом"""
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(max=64)])
    first_name = StringField('Имя', validators=[DataRequired(), Length(max=64)])
    patronymic = StringField('Отчество', validators=[Optional(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Телефон', validators=[Optional(), Length(max=20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    role_id = SelectField('Роль', coerce=int, validators=[DataRequired()])
    city_id = SelectField('Город', coerce=int, validators=[Optional()])
    street = StringField('Улица', validators=[Optional(), Length(max=200)])
    house = StringField('Дом', validators=[Optional(), Length(max=20)])
    apartment = StringField('Квартира', validators=[Optional(), Length(max=20)])
    services = SelectMultipleField('Услуги (для работника)', coerce=int, validators=[Optional()])
    submit = SubmitField('Создать пользователя')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_id.choices = [(r.id, r.name) for r in Role.query.all()]
        self.city_id.choices = [(c.id, c.name) for c in City.query.filter_by(is_active=True).all()]
        self.services.choices = [(s.id, s.name) for s in Service.query.all()]

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('Этот email уже используется')


class ReportForm(FlaskForm):
    """Фильтры для отчётов"""
    start_date = DateField('Дата начала', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('Дата окончания', format='%Y-%m-%d', validators=[Optional()])
    worker_id = SelectField('Работник', coerce=int, validators=[Optional()])
    city_id = SelectField('Город', coerce=int, validators=[Optional()])
    status_id = SelectField('Статус', coerce=int, validators=[Optional()])
    service_id = SelectField('Услуга', coerce=int, validators=[Optional()])
    sort_by = SelectField('Сортировка', choices=[
        ('scheduled_date_desc', 'Дата (новые)'), ('scheduled_date_asc', 'Дата (старые)'),
        ('price_desc', 'Цена (дорогие)'), ('price_asc', 'Цена (дешёвые)'), ('status', 'По статусу'),
    ], validators=[Optional()])
    submit = SubmitField('Сформировать отчёт')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import City, RequestStatus, Service
        worker_role = Role.query.filter_by(code='worker').first()
        workers = WorkerProfile.query.join(User).filter(
            User.is_blocked == False, User.role_id == worker_role.id
        ).all()
        self.worker_id.choices = [(0, 'Все работники')] + [(w.id, w.full_name) for w in workers]
        self.city_id.choices = [(0, 'Все города')] + [(c.id, c.name) for c in City.query.filter_by(is_active=True).all()]
        self.status_id.choices = [(0, 'Все статусы')] + [(s.id, s.name_ru) for s in RequestStatus.query.order_by('order').all()]
        self.service_id.choices = [(0, 'Все услуги')] + [(s.id, s.name) for s in Service.query.all()]


class CityForm(FlaskForm):
    """Добавление/редактирование города"""
    name = StringField('Название города', validators=[DataRequired(), Length(max=100)])
    region = StringField('Регион', validators=[DataRequired(), Length(max=100)], default='Белгородская область')
    is_active = BooleanField('Активен', default=True)
    submit = SubmitField('Сохранить')


class NewsForm(FlaskForm):
    """Создание/редактирование новости"""
    title = StringField('Заголовок', validators=[DataRequired(), Length(max=200)])
    summary = TextAreaField('Краткое описание', validators=[Optional(), Length(max=300)])
    content = TextAreaField('Полный текст', validators=[DataRequired()])
    image = FileField('Фотография', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения')])
    is_published = BooleanField('Опубликовать сразу', default=True)
    submit = SubmitField('Сохранить')


class ForgotPasswordForm(FlaskForm):
    """Запрос сброса пароля"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Отправить инструкцию')


class ResetPasswordForm(FlaskForm):
    """Установка нового пароля"""
    password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Сохранить пароль')


class EmployeeAboutForm(FlaskForm):
    """Редактирование раздела О себе в профиле работника"""
    about_me = TextAreaField('О себе', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Сохранить')