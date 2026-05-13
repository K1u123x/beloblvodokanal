"""
Фикстуры для тестов
"""
import sys
import os
import pytest
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db as _db
from app.models import (
    User, Role, City, Service, Client,
    WorkerProfile, DispatcherProfile, RequestStatus
)


@pytest.fixture(scope='session')
def app():
    """Создание тестового приложения с БД в памяти один раз за сессию"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    return app


@pytest.fixture
def client(app):
    """Клиент для отправки HTTP-запросов без браузера"""
    return app.test_client()


@pytest.fixture
def db(app):
    """
    Чистая БД для каждого теста
    """
    with app.app_context():
        _db.create_all()

        statuses = [
            ('pending', 'Ожидает диспетчера', 'warning', 1),
            ('assigned', 'Назначен работник', 'primary', 2),
            ('in_progress', 'В работе', 'info', 3),
            ('completed', 'Выполнена', 'success', 4),
            ('rejected', 'Отклонена', 'danger', 5),
        ]
        for code, name, color, order in statuses:
            if not RequestStatus.query.filter_by(code=code).first():
                _db.session.add(RequestStatus(code=code, name_ru=name, color=color, order=order))
        _db.session.commit()

        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def roles(db):
    """Базовые роли: admin, dispatcher, worker, client"""
    data = [
        ('admin', 'Администратор'),
        ('dispatcher', 'Диспетчер'),
        ('worker', 'Работник'),
        ('client', 'Клиент'),
    ]
    result = {}
    for code, name in data:
        role = Role(code=code, name=name)
        db.session.add(role)
        result[code] = role
    db.session.commit()
    return result


@pytest.fixture
def cities(db):
    """Города обслуживания"""
    gubkin = City(name='Губкин', region='Белгородская область')
    oskol = City(name='Старый Оскол', region='Белгородская область')
    db.session.add_all([gubkin, oskol])
    db.session.commit()
    return [gubkin, oskol]


@pytest.fixture
def services(db):
    """Услуги из реального прейскуранта"""
    data = [
        ('Устранение засора канализации',
         'Механическая и гидродинамическая прочистка труб любого диаметра.',
         1200, 60, 'bi-droplet'),
        ('Ремонт и замена смесителя',
         'Замена картриджа, ремонт резьбовых соединений, полная замена смесителя.',
         800, 90, 'bi-wrench'),
        ('Регулировка напора воды',
         'Диагностика системы, замена редуктора давления.',
         900, 60, 'bi-water'),
    ]
    result = []
    for name, desc, price, dur, icon in data:
        s = Service(name=name, description=desc, price=price, duration=dur, icon=icon)
        db.session.add(s)
        result.append(s)
    db.session.commit()
    return result


@pytest.fixture
def admin_user(db, roles):
    """Администратор"""
    user = User(
        email='admin@test.com',
        last_name='Админов',
        first_name='Админ',
        role_id=roles['admin'].id,
        email_confirmed=True,
        phone_confirmed=True,
    )
    user.set_password('admin123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dispatcher_user(db, roles, cities):
    """Диспетчер"""
    user = User(
        email='disp@test.com',
        last_name='Диспетчеров',
        first_name='Дмитрий',
        role_id=roles['dispatcher'].id,
        email_confirmed=True,
        phone_confirmed=True,
    )
    user.set_password('disp123')
    db.session.add(user)
    db.session.commit()

    profile = DispatcherProfile(user_id=user.id, city_id=cities[0].id, hire_date=date.today())
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def worker_user(db, roles, cities, services):
    """Работник"""
    user = User(
        email='worker@test.com',
        last_name='Работников',
        first_name='Алексей',
        role_id=roles['worker'].id,
        email_confirmed=True,
        phone_confirmed=True,
    )
    user.set_password('worker123')
    db.session.add(user)
    db.session.commit()

    profile = WorkerProfile(user_id=user.id, city_id=cities[0].id, hire_date=date.today())
    db.session.add(profile)
    db.session.commit()

    profile.services.append(services[0])
    db.session.commit()
    return user


@pytest.fixture
def second_worker(db, roles, cities, services):
    """Второй работник"""
    user = User(
        email='worker2@test.com',
        last_name='Второй',
        first_name='Работник',
        role_id=roles['worker'].id,
        email_confirmed=True,
        phone_confirmed=True,
    )
    user.set_password('worker123')
    db.session.add(user)
    db.session.commit()

    profile = WorkerProfile(user_id=user.id, city_id=cities[0].id, hire_date=date.today())
    db.session.add(profile)
    db.session.commit()

    profile.services.append(services[0])
    db.session.commit()
    return user


@pytest.fixture
def client_user(db, roles, cities):
    """Клиент"""
    user = User(
        email='client@test.com',
        last_name='Клиентов',
        first_name='Пётр',
        role_id=roles['client'].id,
        email_confirmed=True,
        phone_confirmed=True,
    )
    user.set_password('client123')
    db.session.add(user)
    db.session.commit()

    profile = Client(
        user_id=user.id,
        city_id=cities[0].id,
        street='ул. Ленина',
        house='10',
        apartment='25',
    )
    db.session.add(profile)
    db.session.commit()
    return user