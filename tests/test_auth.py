"""
Тесты аутентификации
"""


class TestRegistration:
    """Регистрация новых пользователей"""

    def test_register_new_client(self, client, roles, cities):
        """Успешная регистрация клиента с валидными данными"""
        response = client.post('/auth/register', data={
            'last_name': 'Петров',
            'first_name': 'Пётр',
            'email': 'petr@example.com',
            'phone': '+79515340005',
            'city_id': cities[0].id,
            'street': 'Мира',
            'house': '5',
            'password': 'Password1',
            'password2': 'Password1',
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'Регистрация успешна' in response.data.decode('utf-8')

    def test_register_existing_email(self, client, client_user):
        """Регистрация с занятым email отклоняется"""
        response = client.post('/auth/register', data={
            'last_name': 'Дубль',
            'first_name': 'Клиент',
            'email': client_user.email,
            'phone': '+79000000006',
            'city_id': 1,
            'street': 'Мира',
            'house': '5',
            'password': 'Password1',
            'password2': 'Password1',
        }, follow_redirects=True)

        assert 'Этот email уже используется' in response.data.decode('utf-8')


class TestLogin:
    """Вход в систему"""

    def test_login_with_valid_credentials(self, client, client_user):
        """Вход с правильным email и паролем"""
        response = client.post('/auth/login', data={
            'email': client_user.email,
            'password': 'client123',
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'Личный кабинет' in response.data.decode('utf-8')

    def test_login_with_wrong_password(self, client, client_user):
        """Вход с неверным паролем"""
        response = client.post('/auth/login', data={
            'email': client_user.email,
            'password': 'wrongpassword',
        }, follow_redirects=True)

        assert 'Неверный email или пароль' in response.data.decode('utf-8')

    def test_blocked_user_cannot_login(self, client, client_user, db):
        """Заблокированный пользователь не может войти"""
        client_user.is_blocked = True
        client_user.block_reason = 'Нарушение правил'
        db.session.commit()

        response = client.post('/auth/login', data={
            'email': client_user.email,
            'password': 'client123',
        }, follow_redirects=True)

        assert 'заблокирован' in response.data.decode('utf-8').lower()


class TestLogout:
    """Выход из системы"""

    def test_user_can_logout(self, client, client_user):
        """Пользователь может выйти из аккаунта"""
        client.post('/auth/login', data={
            'email': client_user.email,
            'password': 'client123',
        }, follow_redirects=True)

        response = client.get('/auth/logout', follow_redirects=True)
        assert 'Войти' in response.data.decode('utf-8')