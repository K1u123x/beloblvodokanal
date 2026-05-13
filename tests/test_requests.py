"""
Тесты заявок
"""
from datetime import date, timedelta


class TestCreateRequest:
    """Создание заявок клиентом"""

    def test_create_request(self, client, client_user, services, cities, worker_user, second_worker):
        """Клиент успешно создаёт заявку на завтра"""
        client.post('/auth/login', data={
            'email': client_user.email,
            'password': 'client123',
        }, follow_redirects=True)

        service = services[0]  # Берём первую услугу
        tomorrow = date.today() + timedelta(days=1)
        response = client.post(f'/user/book/{service.id}', data={
            'last_name': client_user.last_name,
            'first_name': client_user.first_name,
            'city_id': cities[0].id,
            'street': 'ул. Дзержинского',
            'house': '15',
            'service_id': service.id,
            'scheduled_date': tomorrow.isoformat(),
            'scheduled_time_start': '08:30',  # Свободный слот для 60-минутной услуги
            'description': 'Тестовая заявка',
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'Заявка создана' in response.data.decode('utf-8')

    def test_duplicate_request_blocked(self, client, client_user, services, cities, worker_user, second_worker):
        """Нельзя создать вторую активную заявку на ту же услугу"""
        client.post('/auth/login', data={
            'email': client_user.email,
            'password': 'client123',
        }, follow_redirects=True)

        service = services[0]
        tomorrow = date.today() + timedelta(days=1)
        data = {
            'last_name': client_user.last_name,
            'first_name': client_user.first_name,
            'city_id': cities[0].id,
            'street': 'ул. Дзержинского',
            'house': '15',
            'service_id': service.id,
            'scheduled_date': tomorrow.isoformat(),
            'scheduled_time_start': '08:30',  # Свободный слот
        }
        client.post(f'/user/book/{service.id}', data=data, follow_redirects=True)
        response = client.post(f'/user/book/{service.id}', data=data, follow_redirects=True)

        assert 'активная заявка' in response.data.decode('utf-8').lower()


class TestSlots:
    """Доступные временные слоты"""

    def test_get_slots_returns_list(self, client, client_user, services, worker_user, second_worker):
        """API возвращает список слотов для авторизованного клиента"""
        client.post('/auth/login', data={
            'email': client_user.email,
            'password': 'client123',
        }, follow_redirects=True)

        service = services[0]
        tomorrow = date.today() + timedelta(days=1)
        response = client.get(f'/user/get_slots/{service.id}/{tomorrow.isoformat()}')
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)


class TestLifecycle:
    """Полный цикл заявки (заглушка)"""

    def test_lifecycle_placeholder(self):
        pass