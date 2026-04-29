"""
Реалистичные тестовые данные для веб-сервиса «БелОблВодоканал».
Основаны на реальных вакансиях и прейскурантах с официального сайта belwater.ru.
"""
import random
from datetime import datetime, timedelta, date, time
from app import create_app, db
from app.models import (
    User, Client, WorkerProfile, DispatcherProfile, Service,
    City, Role, RequestStatus, Request, Message, Review, News
)

app = create_app()


# ---------------------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ---------------------------------------------------------------------------

def clear_data():
    """Аккуратно очищает все таблицы перед заполнением."""
    for model in [Message, Review, Request, Service, News,
                  Client, WorkerProfile, DispatcherProfile, User, City, Role, RequestStatus]:
        db.session.query(model).delete()
    db.session.commit()
    print("🗑️ Старые данные удалены.")


# ---------------------------------------------------------------------------
# СПРАВОЧНИКИ
# ---------------------------------------------------------------------------

def create_cities():
    """Города обслуживания (реальные филиалы)."""
    cities = [
        City(name='Губкин', region='Белгородская область'),
        City(name='Старый Оскол', region='Белгородская область'),
    ]
    db.session.add_all(cities)
    db.session.commit()
    print(f"🏙️ Города созданы: {len(cities)}")
    return cities


def create_roles():
    """Роли пользователей."""
    roles_data = [
        ('admin', 'Администратор', 'Полный доступ ко всем функциям системы'),
        ('dispatcher', 'Диспетчер', 'Приём и распределение заявок'),
        ('worker', 'Работник', 'Выполнение заявок, ведение портфолио'),
        ('client', 'Клиент', 'Подача заявок на услуги'),
    ]
    roles = {}
    for code, name, desc in roles_data:
        role = Role(code=code, name=name, description=desc)
        db.session.add(role)
        db.session.flush()
        roles[code] = role
    db.session.commit()
    print(f"👥 Роли созданы: {len(roles)}")
    return roles


def create_statuses():
    """Статусы жизненного цикла заявки."""
    statuses_data = [
        ('pending',    'Ожидает диспетчера', 'warning',  1),
        ('assigned',   'Назначен работник',  'primary',  2),
        ('in_progress','В работе',           'info',     3),
        ('completed',  'Выполнена',          'success',  4),
        ('rejected',   'Отклонена',          'danger',   5),
    ]
    statuses = {}
    for code, name_ru, color, order in statuses_data:
        st = RequestStatus(code=code, name_ru=name_ru, color=color, order=order)
        db.session.add(st)
        db.session.flush()
        statuses[code] = st
    db.session.commit()
    print(f"📊 Статусы созданы: {len(statuses)}")
    return statuses


# ---------------------------------------------------------------------------
# УСЛУГИ  –  основаны на реальном прейскуранте Старооскольского филиала
# ---------------------------------------------------------------------------

def create_services():
    """
    Услуги, которые реально оказывает водоканал (взяты из прейскуранта).
    Оставлены только те, которые выполняют работники со специализацией.
    Прейскурант для Губкина взят с официального сайта (набор услуг практически
    идентичен Старооскольскому, цены совпадают).
    """
    services_data = [
        # ---------- Сантехнические работы ----------
        ('Устранение засора канализации',
         'Механическая и гидродинамическая прочистка труб любого диаметра.',
         1200, 60, 'bi-droplet'),
        ('Ремонт и замена смесителя',
         'Замена картриджа, ремонт резьбовых соединений, полная замена смесителя.',
         800, 90, 'bi-wrench'),
        ('Установка и опломбировка счётчика воды',
         'Монтаж прибора учёта, проверка герметичности, опломбировка.',
         2000, 120, 'bi-speedometer2'),
        ('Замена труб водоснабжения (до 5 м)',
         'Частичная или полная замена стальных труб на полипропилен.',
         5000, 240, 'bi-pipe'),
        ('Ремонт унитаза / сливного бачка',
         'Замена арматуры, устранение течи, регулировка поплавка.',
         1500, 90, 'bi-tools'),
        ('Регулировка напора воды',
         'Диагностика системы, замена редуктора давления.',
         900, 60, 'bi-water'),

        # ---------- Отопление ----------
        ('Замена радиатора отопления',
         'Демонтаж старого радиатора, установка нового с подключением.',
         3500, 180, 'bi-thermometer-half'),
        ('Диагностика системы отопления',
         'Проверка давления, поиск протечек, рекомендации по ремонту.',
         1000, 60, 'bi-search'),
        ('Монтаж и подключение водонагревателя',
         'Установка бойлера, подключение к электричеству и воде.',
         3000, 180, 'bi-fire'),

        # ---------- Сварочные работы ----------
        ('Сварочные работы (электрогазосварка)',
         'Сварка труб, металлоконструкций, арматуры.',
         2500, 120, 'bi-lightning-charge'),
    ]
    
    services = []
    for name, desc, price, dur, icon in services_data:
        s = Service(name=name, description=desc, price=price, duration=dur, icon=icon)
        db.session.add(s)
        services.append(s)
    db.session.commit()
    print(f"🔧 Услуги созданы: {len(services)}")
    return services


# ---------------------------------------------------------------------------
# ПОЛЬЗОВАТЕЛИ И ПРОФИЛИ  –  основаны на реальных вакансиях
# ---------------------------------------------------------------------------

def create_users_and_profiles(roles, cities):
    """
    Создаёт пользователей с профилями, используя названия реальных должностей.
    """
    gubkin, oskol = cities[0], cities[1]

    # ========== АДМИНИСТРАТОР ==========
    admin_user = User(
        email='admin@example.com', phone='+7 (472) 411-00-01',
        last_name='Администраторов', first_name='Админ', patronymic='Системович',
        role_id=roles['admin'].id,
        email_confirmed=True, phone_confirmed=True,
    )
    admin_user.set_password('admin123')
    db.session.add(admin_user)
    db.session.flush()

    # ========== ДИСПЕТЧЕРЫ  (реальные должности) ==========
    dispatchers_data = [
        {'email': 'dispatcher1@example.com', 'phone': '+7 (472) 411-00-02',
         'last_name': 'Иванова', 'first_name': 'Елена', 'patronymic': 'Сергеевна',
         'hire_date': date(2021, 3, 10), 'city': gubkin},
        {'email': 'dispatcher2@example.com', 'phone': '+7 (472) 411-00-03',
         'last_name': 'Петрова', 'first_name': 'Ольга', 'patronymic': 'Александровна',
         'hire_date': date(2022, 6, 20), 'city': oskol},
    ]

    dispatchers = []
    for data in dispatchers_data:
        user = User(
            email=data['email'], phone=data['phone'],
            last_name=data['last_name'], first_name=data['first_name'],
            patronymic=data['patronymic'], role_id=roles['dispatcher'].id,
            email_confirmed=True, phone_confirmed=True,
        )
        user.set_password('disp123')
        db.session.add(user)
        db.session.flush()

        dp = DispatcherProfile(
            user_id=user.id, city_id=data['city'].id,
            hire_date=data['hire_date'],
        )
        db.session.add(dp)
        dispatchers.append(dp)

    # ========== РАБОТНИКИ  (реальные должности филиалов) ==========
    workers_data = [
        # ---------- Губкин ----------
        {'email': 'worker1@example.com', 'phone': '+7 (472) 411-10-01',
         'last_name': 'Кузнецов', 'first_name': 'Андрей', 'patronymic': 'Викторович',
         'city': gubkin, 'hire_date': date(2021, 5, 15),
         'about': 'Слесарь аварийно-восстановительных работ. Выезжаю в любое время суток. Устраняю засоры, прорывы, течи любой сложности.',
         'services': ['Устранение засора канализации', 'Замена труб водоснабжения (до 5 м)',
                      'Ремонт унитаза / сливного бачка', 'Замена радиатора отопления',
                      'Диагностика системы отопления', 'Монтаж и подключение водонагревателя',
                      'Ремонт и замена смесителя', 'Установка и опломбировка счётчика воды',
                      'Регулировка напора воды'],
        },
        {'email': 'worker2@example.com', 'phone': '+7 (472) 411-10-02',
         'last_name': 'Сидоров', 'first_name': 'Николай', 'patronymic': 'Петрович',
         'city': gubkin, 'hire_date': date(2022, 2, 1),
         'about': 'Слесарь-ремонтник 6 разряда. Ремонтирую и меняю смесители, унитазы, ванны. Даю гарантию на работу.',
         'services': ['Ремонт и замена смесителя', 'Ремонт унитаза / сливного бачка',
                      'Установка и опломбировка счётчика воды', 'Замена труб водоснабжения (до 5 м)',
                      'Регулировка напора воды', 'Замена радиатора отопления',
                      'Диагностика системы отопления', 'Монтаж и подключение водонагревателя'],
        },
        {'email': 'worker3@example.com', 'phone': '+7 (472) 411-10-03',
         'last_name': 'Морозов', 'first_name': 'Дмитрий', 'patronymic': 'Алексеевич',
         'city': gubkin, 'hire_date': date(2023, 1, 10),
         'about': 'Электрогазосварщик 6 разряда. Выполняю сварочные работы любой сложности.',
         'services': ['Сварочные работы (электрогазосварка)', 'Замена труб водоснабжения (до 5 м)',
                      'Замена радиатора отопления', 'Монтаж и подключение водонагревателя',
                      'Ремонт и замена смесителя', 'Устранение засора канализации',
                      'Диагностика системы отопления'],
        },
        {'email': 'worker8@example.com', 'phone': '+7 (472) 411-10-05',
         'last_name': 'Фёдоров', 'first_name': 'Сергей', 'patronymic': 'Николаевич',
         'city': gubkin, 'hire_date': date(2022, 8, 12),
         'about': 'Слесарь АВР 5 разряда. Специализируюсь на прочистке канализации и устранении засоров.',
         'services': ['Устранение засора канализации', 'Замена труб водоснабжения (до 5 м)',
                      'Ремонт унитаза / сливного бачка', 'Ремонт и замена смесителя',
                      'Регулировка напора воды', 'Установка и опломбировка счётчика воды'],
        },
        {'email': 'worker9@example.com', 'phone': '+7 (472) 411-10-06',
         'last_name': 'Васильев', 'first_name': 'Роман', 'patronymic': 'Олегович',
         'city': gubkin, 'hire_date': date(2023, 5, 20),
         'about': 'Специалист по установке счётчиков и прочистке канализации. Работаю с современным оборудованием.',
         'services': ['Установка и опломбировка счётчика воды', 'Устранение засора канализации',
                      'Замена труб водоснабжения (до 5 м)', 'Ремонт унитаза / сливного бачка',
                      'Ремонт и замена смесителя', 'Регулировка напора воды'],
        },

        # ---------- Старый Оскол ----------
        {'email': 'worker4@example.com', 'phone': '+7 (472) 411-20-01',
         'last_name': 'Петров', 'first_name': 'Сергей', 'patronymic': 'Иванович',
         'city': oskol, 'hire_date': date(2021, 8, 20),
         'about': 'Слесарь-ремонтник 6 разряда. 20 лет опыта. Специализируюсь на сложных ремонтах и замене оборудования.',
         'services': ['Ремонт и замена смесителя', 'Замена радиатора отопления',
                      'Монтаж и подключение водонагревателя', 'Замена труб водоснабжения (до 5 м)',
                      'Устранение засора канализации', 'Ремонт унитаза / сливного бачка',
                      'Диагностика системы отопления', 'Сварочные работы (электрогазосварка)'],
        },
        {'email': 'worker5@example.com', 'phone': '+7 (472) 411-20-02',
         'last_name': 'Волков', 'first_name': 'Алексей', 'patronymic': 'Дмитриевич',
         'city': oskol, 'hire_date': date(2022, 4, 12),
         'about': 'Электрогазосварщик 5 разряда. Универсал: сварка, сантехника, отопление.',
         'services': ['Сварочные работы (электрогазосварка)', 'Замена труб водоснабжения (до 5 м)',
                      'Монтаж и подключение водонагревателя', 'Замена радиатора отопления',
                      'Ремонт и замена смесителя', 'Устранение засора канализации',
                      'Диагностика системы отопления', 'Регулировка напора воды'],
        },
        {'email': 'worker6@example.com', 'phone': '+7 (472) 411-20-03',
         'last_name': 'Новиков', 'first_name': 'Павел', 'patronymic': 'Сергеевич',
         'city': oskol, 'hire_date': date(2023, 3, 5),
         'about': 'Слесарь АВР 5 разряда. Специалист по установке счётчиков и прочистке канализации.',
         'services': ['Установка и опломбировка счётчика воды', 'Устранение засора канализации',
                      'Замена труб водоснабжения (до 5 м)', 'Ремонт унитаза / сливного бачка',
                      'Ремонт и замена смесителя', 'Регулировка напора воды'],
        },
        {'email': 'worker7@example.com', 'phone': '+7 (472) 411-20-04',
         'last_name': 'Михайлов', 'first_name': 'Игорь', 'patronymic': 'Владимирович',
         'city': oskol, 'hire_date': date(2024, 1, 15),
         'about': 'Начинающий специалист. Выполняю простые и средние по сложности работы.',
         'services': ['Ремонт и замена смесителя', 'Регулировка напора воды',
                      'Устранение засора канализации', 'Ремонт унитаза / сливного бачка',
                      'Установка и опломбировка счётчика воды', 'Замена труб водоснабжения (до 5 м)'],
        },
        {'email': 'worker10@example.com', 'phone': '+7 (472) 411-20-05',
         'last_name': 'Зайцев', 'first_name': 'Антон', 'patronymic': 'Павлович',
         'city': oskol, 'hire_date': date(2023, 9, 1),
         'about': 'Слесарь-ремонтник 5 разряда. Специалист по отоплению и водоснабжению.',
         'services': ['Замена радиатора отопления', 'Диагностика системы отопления',
                      'Монтаж и подключение водонагревателя', 'Замена труб водоснабжения (до 5 м)',
                      'Ремонт и замена смесителя', 'Ремонт унитаза / сливного бачка',
                      'Сварочные работы (электрогазосварка)'],
        },
    ]

    workers = []
    for data in workers_data:
        user = User(
            email=data['email'], phone=data['phone'],
            last_name=data['last_name'], first_name=data['first_name'],
            patronymic=data['patronymic'], role_id=roles['worker'].id,
            email_confirmed=True, phone_confirmed=True,
        )
        user.set_password('worker123')
        db.session.add(user)
        db.session.flush()

        wp = WorkerProfile(
            user_id=user.id, city_id=data['city'].id,
            hire_date=data['hire_date'], about_me=data['about'],
        )
        db.session.add(wp)
        workers.append(wp)

    # Назначаем услуги (после того, как все WorkerProfile созданы)
    service_map = {s.name: s for s in Service.query.all()}
    for data in workers_data:
        wp = WorkerProfile.query.filter_by(user_id=User.query.filter_by(email=data['email']).first().id).first()
        for svc_name in data['services']:
            svc = service_map.get(svc_name)
            if svc and svc not in wp.services:
                wp.services.append(svc)

    # ========== КЛИЕНТЫ ==========
    client_names = [
        # Губкин
        ('Смирнов', 'Алексей', 'Игоревич', '+7 (472) 411-30-01', gubkin),
        ('Козлова', 'Татьяна', 'Владимировна', '+7 (472) 411-30-02', gubkin),
        ('Соколов', 'Иван', 'Петрович', '+7 (472) 411-30-03', gubkin),
        ('Лебедева', 'Мария', 'Алексеевна', '+7 (472) 411-30-04', gubkin),
        ('Павлов', 'Сергей', 'Николаевич', '+7 (472) 411-30-05', gubkin),
        ('Семёнова', 'Анна', 'Дмитриевна', '+7 (472) 411-30-06', gubkin),
        ('Егоров', 'Павел', 'Олегович', '+7 (472) 411-30-07', gubkin),
        ('Алексеева', 'Екатерина', 'Викторовна', '+7 (472) 411-30-08', gubkin),
        ('Фёдоров', 'Максим', 'Андреевич', '+7 (472) 411-30-09', gubkin),
        ('Николаева', 'Ольга', 'Сергеевна', '+7 (472) 411-30-10', gubkin),
        ('Григорьев', 'Артём', 'Денисович', '+7 (472) 411-30-11', gubkin),
        ('Макарова', 'Виктория', 'Александровна', '+7 (472) 411-30-12', gubkin),
        ('Орлова', 'Кристина', 'Игоревна', '+7 (472) 411-30-13', gubkin),
        ('Титов', 'Евгений', 'Владимирович', '+7 (472) 411-30-14', gubkin),
        ('Жукова', 'Людмила', 'Сергеевна', '+7 (472) 411-30-15', gubkin),
        # Старый Оскол
        ('Васильев', 'Денис', 'Павлович', '+7 (472) 411-40-01', oskol),
        ('Попова', 'Наталья', 'Игоревна', '+7 (472) 411-40-02', oskol),
        ('Зайцев', 'Роман', 'Александрович', '+7 (472) 411-40-03', oskol),
        ('Белова', 'Светлана', 'Викторовна', '+7 (472) 411-40-04', oskol),
        ('Тарасов', 'Владимир', 'Сергеевич', '+7 (472) 411-40-05', oskol),
        ('Комарова', 'Юлия', 'Андреевна', '+7 (472) 411-40-06', oskol),
        ('Орлов', 'Антон', 'Дмитриевич', '+7 (472) 411-40-07', oskol),
        ('Савельева', 'Анастасия', 'Олеговна', '+7 (472) 411-40-08', oskol),
        ('Григорьев', 'Станислав', 'Игоревич', '+7 (472) 411-40-09', oskol),
        ('Медведева', 'Ксения', 'Александровна', '+7 (472) 411-40-10', oskol),
        ('Лазарев', 'Михаил', 'Андреевич', '+7 (472) 411-40-11', oskol),
        ('Фомина', 'Алина', 'Романовна', '+7 (472) 411-40-12', oskol),
        ('Куликов', 'Илья', 'Артёмович', '+7 (472) 411-40-13', oskol),
        ('Сорокина', 'Дарья', 'Максимовна', '+7 (472) 411-40-14', oskol),
        ('Борисов', 'Никита', 'Алексеевич', '+7 (472) 411-40-15', oskol),
    ]

    streets_gubkin = ['Дзержинского', 'Советская', 'Победы', 'Комсомольская',
                      'Мира', 'Ленина', 'Гагарина', 'Строителей', 'Молодёжная', 'Парковая']
    streets_oskol = ['Ленина', 'Октябрьская', 'Пролетарская', 'Коммунистическая',
                     'Садовая', 'Центральная', 'Зелёная', 'Северная', 'Южная', 'Восточная']

    clients = []
    for i, (ln, fn, p, phone, city) in enumerate(client_names):
        user = User(
            email=f'client{i+1}@example.com', phone=phone,
            last_name=ln, first_name=fn, patronymic=p,
            role_id=roles['client'].id,
            email_confirmed=True, phone_confirmed=True,
        )
        user.set_password('client123')
        db.session.add(user)
        db.session.flush()

        street = f"ул. {random.choice(streets_gubkin if city.name == 'Губкин' else streets_oskol)}"
        house = str(random.randint(1, 80))
        apartment = str(random.randint(1, 120)) if random.random() > 0.3 else None

        client = Client(
            user_id=user.id, city_id=city.id,
            street=street, house=house, apartment=apartment,
        )
        db.session.add(client)
        clients.append(client)

    db.session.commit()
    print(f"👤 Пользователи: админ, {len(dispatchers)} disp, {len(workers)} workers, {len(clients)} clients")
    return {
        'dispatchers': dispatchers,
        'workers': workers,
        'clients': clients,
        'cities': cities,
    }


# ---------------------------------------------------------------------------
# ЗАЯВКИ, ОТЗЫВЫ, СООБЩЕНИЯ
# ---------------------------------------------------------------------------

def create_requests(clients, workers, dispatchers, services, statuses, cities):
    """
    Генерирует 100 заявок с учётом занятости работников.
    """
    all_requests = []
    now = datetime.now()
    gubkin, oskol = cities

    gubkin_workers = [w for w in workers if w.city_id == gubkin.id]
    oskol_workers = [w for w in workers if w.city_id == oskol.id]
    gubkin_clients = [c for c in clients if c.city_id == gubkin.id]
    oskol_clients = [c for c in clients if c.city_id == oskol.id]

    problem_descriptions = [
        'Течёт кран на кухне, нужна срочная замена',
        'Засорился унитаз, вода не уходит',
        'Нет горячей воды, подозрение на засор',
        'Прорвало трубу в ванной, нужен срочный ремонт',
        'Слабый напор воды во всей квартире',
        'Капает смеситель в ванной',
        'Шумит труба при включении воды',
        'Запах канализации в квартире',
        'Не греет полотенцесушитель',
        'Течёт бачок унитаза',
        'Засор в кухонной мойке',
        'Нужна установка новой раковины',
        'Промерзают трубы в подвале',
        'Счётчик воды не крутится',
        'Нужна замена вентиля на стояке',
        'Сорвало кран, перекрыть воду',
    ]

    # 80 случайных заявок
    for _ in range(80):
        city = random.choice([gubkin, oskol])
        city_workers = gubkin_workers if city == gubkin else oskol_workers
        city_clients = gubkin_clients if city == gubkin else oskol_clients
        if not city_workers or not city_clients:
            continue

        client = random.choice(city_clients)
        service = random.choice(services)

        delta_days = random.randint(-90, 30)
        req_date = (now + timedelta(days=delta_days)).date()

        hour = random.randint(8, 17)
        minute = random.choice([0, 30])
        if hour == 17 and minute == 30:
            minute = 0
        time_start = time(hour, minute)
        time_end = (datetime.combine(req_date, time_start) + timedelta(minutes=service.duration)).time()

        if req_date < now.date():
            status_code = random.choice(['completed', 'completed', 'completed', 'rejected', 'rejected'])
        elif req_date == now.date():
            status_code = random.choice(['assigned', 'in_progress', 'in_progress', 'pending'])
        else:
            status_code = random.choice(['pending', 'pending', 'assigned', 'assigned'])

        worker = None
        dispatcher = random.choice(dispatchers)
        rejection_reason = None

        if status_code in ('assigned', 'in_progress', 'completed'):
            possible = [w for w in city_workers if service in w.services]
            if possible:
                worker = random.choice(possible)
            else:
                status_code = 'pending'

        if status_code == 'rejected':
            rejection_reason = random.choice([
                'Неверный адрес', 'Клиент не вышел на связь',
                'Услуга не предоставляется в данном районе', 'Клиент передумал',
            ])

        req = Request(
            client_id=client.id, service_id=service.id,
            dispatcher_id=dispatcher.id if status_code != 'pending' else None,
            worker_id=worker.id if worker else None,
            city_id=city.id,
            street=client.street, house=client.house, apartment=client.apartment,
            description=random.choice(problem_descriptions),
            status_id=statuses[status_code].id,
            scheduled_date=req_date,
            scheduled_time_start=time_start,
            scheduled_time_end=time_end,
            rejection_reason=rejection_reason,
            completed_at=datetime.now() - timedelta(days=random.randint(0, 5))
            if status_code == 'completed' else None,
        )
        db.session.add(req)
        all_requests.append(req)

    db.session.commit()
    print(f"📋 Заявки созданы: {len(all_requests)}")
    return all_requests


def create_reviews(requests_list):
    """Создаёт отзывы для 70% выполненных заявок с вероятностью фото 50%."""
    import os
    from PIL import Image, ImageDraw, ImageFont

    reviews_folder = os.path.join('app', 'static', 'uploads', 'reviews')
    os.makedirs(reviews_folder, exist_ok=True)

    def create_placeholder_image(filename, text="Отзыв"):
        img = Image.new('RGB', (600, 400), color=(0, 84, 166))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((600 - tw) // 2, (400 - th) // 2), text, fill=(255, 255, 255), font=font)
        path = os.path.join(reviews_folder, filename)
        img.save(path, 'JPEG', quality=85)
        return filename

    reviews = []
    photo_counter = 1
    for req in requests_list:
        if req.status_code != 'completed' or not req.worker_id:
            continue
        if random.random() >= 0.7:
            continue

        worker = WorkerProfile.query.get(req.worker_id)
        client = Client.query.get(req.client_id)

        rating = random.randint(4, 5) if worker and worker.rating >= 4.5 else \
                 random.randint(3, 5) if worker and worker.rating >= 4.0 else \
                 random.randint(2, 5)

        comments_pool = [
            ('Отлично, быстро и качественно!', 5),
            ('Спасибо, всё починили, приехали вовремя', 5),
            ('Хорошая работа, но немного задержались', 4),
            ('Всё хорошо, но дороговато', 3),
            ('Очень доволен, рекомендую!', 5),
            ('Приехали раньше, быстро всё сделали', 5),
            ('Вежливый мастер, объяснил причину поломки', 5),
            ('Средненько, ожидал большего', 3),
            ('Лучший сантехник! Всё починил за час', 5),
        ]
        suitable = [c for c, r in comments_pool if abs(r - rating) <= 1]
        comment = random.choice(suitable or comments_pool)

        review = Review(
            request_id=req.id, client_id=client.id if client else None,
            worker_id=req.worker_id, rating=rating, comment=comment,
            in_portfolio=random.random() > 0.5,
        )

        if random.random() < 0.5:  # 50% chance of photo
            filename = f"review_{photo_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            create_placeholder_image(filename, f"Отзыв: {req.service.name[:20]}")
            review.photo = filename
            photo_counter += 1

        db.session.add(review)
        reviews.append(review)

    db.session.commit()
    print(f"⭐ Отзывы созданы: {len(reviews)} (с фото: {photo_counter - 1})")
    return reviews


def create_messages(requests_list):
    """Создаёт сообщения в чатах для 80% активных заявок."""
    messages = []
    templates = {
        'client': [
            'Здравствуйте, когда сможете приехать?',
            'Код домофона 123',
            'Буду ждать, спасибо',
            'У вас есть с собой нужные запчасти?',
            'Сколько примерно займёт работа?',
            'Спасибо за работу!',
            'А вы уже выехали?',
            'Я дома, жду',
        ],
        'worker': [
            'Здравствуйте, буду через 30 минут',
            'Выезжаю, ориентировочно в 14:00',
            'Нужно будет заменить деталь, у меня с собой есть',
            'Работа займёт около часа',
            'Уже подъезжаю',
            'Готово, проверяйте',
            'Принял заявку, скоро буду',
            'Пробки, задержусь на 15 минут',
        ],
    }

    for req in requests_list:
        if not req.worker_id or req.status_code not in ('assigned', 'in_progress', 'completed'):
            continue
        if random.random() >= 0.8:
            continue

        current_time = req.created_at
        for i in range(random.randint(2, 8)):
            if i % 2 == 0:
                author_id = req.client.user_id if req.client else None
                msg_text = random.choice(templates['client'])
            else:
                author_id = req.worker.user_id if req.worker else None
                msg_text = random.choice(templates['worker'])

            if not author_id:
                continue
            current_time += timedelta(minutes=random.randint(3, 45))
            msg = Message(
                request_id=req.id, author_id=author_id,
                content=msg_text, timestamp=current_time,
            )
            db.session.add(msg)
            messages.append(msg)

    db.session.commit()
    print(f"💬 Сообщения созданы: {len(messages)}")


# ---------------------------------------------------------------------------
# ТОЧКА ВХОДА
# ---------------------------------------------------------------------------

def main():
    with app.app_context():
        print("=" * 60)
        print("💧 ЗАПОЛНЕНИЕ ТЕСТОВЫМИ ДАННЫМИ v6.0 (Реальные услуги и должности)")
        print("=" * 60)

        clear_data()
        cities = create_cities()
        roles = create_roles()
        statuses = create_statuses()

        profiles = create_users_and_profiles(roles, cities)
        services = create_services()

        requests_list = create_requests(
            profiles['clients'], profiles['workers'], profiles['dispatchers'],
            services, statuses, cities,
        )
        create_reviews(requests_list)
        create_messages(requests_list)

        print("\n📋 ДАННЫЕ ДЛЯ ВХОДА:")
        print("─" * 40)
        print("👑 Администратор:     admin@example.com / admin123")
        print("📞 Диспетчеры:        dispatcher1@example.com / disp123")
        print("                      dispatcher2@example.com / disp123")
        print("🔧 Работники (Губкин):   worker1@example.com – worker3@example.com")
        print("                         worker8@example.com, worker9@example.com")
        print("🔧 Работники (Ст.Оскол): worker4@example.com – worker7@example.com")
        print("                         worker10@example.com")
        print("   Пароль: worker123")
        print("👤 Клиенты: client1@example.com … client30@example.com / client123")
        print("=" * 60)


if __name__ == "__main__":
    main()