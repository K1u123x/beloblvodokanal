"""
Тесты админ-панели
"""


class TestBlocking:
    """Блокировка и разблокировка пользователей"""

    def test_admin_can_block_user(self, client, admin_user, client_user, db):
        """Админ блокирует клиента с указанием причины"""
        client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'admin123',
        }, follow_redirects=True)

        response = client.post(f'/admin/user/{client_user.id}/block', data={
            'block_reason': 'Тестовая блокировка',
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'заблокирован' in response.data.decode('utf-8').lower()

        db.session.refresh(client_user)
        assert client_user.is_blocked is True

    def test_admin_can_unblock_user(self, client, admin_user, client_user, db):
        """Админ разблокирует ранее заблокированного клиента"""
        client_user.is_blocked = True
        client_user.block_reason = 'Была причина'
        db.session.commit()

        client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'admin123',
        }, follow_redirects=True)

        response = client.post(f'/admin/user/{client_user.id}/block', follow_redirects=True)

        assert response.status_code == 200
        assert 'разблокирован' in response.data.decode('utf-8').lower()

        db.session.refresh(client_user)
        assert client_user.is_blocked is False

    def test_admin_cannot_block_self(self, client, admin_user):
        """Админ не может заблокировать самого себя"""
        client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'admin123',
        }, follow_redirects=True)

        response = client.get(f'/admin/user/{admin_user.id}/block', follow_redirects=True)
        assert 'нельзя заблокировать самого себя' in response.data.decode('utf-8').lower()


class TestCreateUser:
    """Создание пользователей через админку"""

    def test_admin_can_create_client(self, client, admin_user, roles, cities):
        """Админ создает нового клиента с адресом"""
        client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'admin123',
        }, follow_redirects=True)

        response = client.post('/admin/user/create', data={
            'last_name': 'Новый',
            'first_name': 'Клиент',
            'email': 'newclient@test.com',
            'password': 'Password1',
            'role_id': roles['client'].id,
            'city_id': cities[0].id,
            'street': 'ул. Тестовая',
            'house': '15',
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'Пользователь создан' in response.data.decode('utf-8')


class TestAccess:
    """Контроль доступа к админ-панели"""

    def test_client_cannot_access_admin_dashboard(self, client, client_user):
        """Клиент не может зайти в админ-панель"""
        client.post('/auth/login', data={
            'email': client_user.email,
            'password': 'client123',
        }, follow_redirects=True)

        response = client.get('/admin/dashboard', follow_redirects=True)
        assert 'Доступ запрещён' in response.data.decode('utf-8')