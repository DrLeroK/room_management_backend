from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User, UserRole


class UserManagementAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="test_admin", email="admin@test.com", password="password123", role=UserRole.ADMIN
        )
        self.owner = User.objects.create_user(
            username="test_owner",
            email="owner@test.com",
            password="password123",
            role=UserRole.OWNER,
            first_name="Owner",
            last_name="User",
        )
        self.manager = User.objects.create_user(
            username="test_manager",
            email="manager@test.com",
            password="password123",
            role=UserRole.MANAGER,
            first_name="Manager",
            last_name="User",
        )
        self.receptionist = User.objects.create_user(
            username="test_receptionist",
            email="receptionist@test.com",
            password="password123",
            role=UserRole.RECEPTIONIST,
            first_name="Receptionist",
            last_name="User",
            phone_number="+251900112233",
        )

    def test_login_api_returns_jwt_and_role_payload(self):
        url = reverse("token_obtain_pair")
        payload = {"username": "test_receptionist", "password": "password123"}
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], "test_receptionist")
        self.assertEqual(response.data["user"]["role"], UserRole.RECEPTIONIST)

    def test_user_profile_me_api(self):
        url = reverse("user_profile")
        self.client.force_authenticate(user=self.receptionist)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "test_receptionist")
        self.assertEqual(response.data["phone_number"], "+251900112233")

    def test_change_password_api(self):
        url = reverse("user_change_password")
        self.client.force_authenticate(user=self.receptionist)
        # 1. Weak password must be rejected by StrongPasswordValidator
        weak_payload = {
            "old_password": "password123",
            "new_password": "weakpassword",
            "new_password_confirm": "weakpassword",
        }
        res_weak = self.client.post(url, data=weak_payload, format="json")
        self.assertEqual(res_weak.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Compliant strong password succeeds
        strong_password = "NewSecurePass@2026!"
        payload = {
            "old_password": "password123",
            "new_password": strong_password,
            "new_password_confirm": strong_password,
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify new password works
        self.client.logout()
        login_response = self.client.post(
            reverse("token_obtain_pair"), {"username": "test_receptionist", "password": strong_password}
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_owner_create_new_staff_user(self):
        url = reverse("user-list")
        self.client.force_authenticate(user=self.owner)
        payload = {
            "username": "new_receptionist",
            "email": "newrec@test.com",
            "password": "SecurePass2026!Str0ng",
            "password_confirm": "SecurePass2026!Str0ng",
            "role": UserRole.RECEPTIONIST,
            "first_name": "New",
            "last_name": "Rec",
            "phone_number": "+251988776655",
            "employee_id": "EMP-NEW-99",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="new_receptionist").exists())

    def test_owner_create_staff_weak_password_rejected(self):
        url = reverse("user-list")
        self.client.force_authenticate(user=self.owner)
        payload = {
            "username": "weak_user",
            "email": "weak@test.com",
            "password": "simplepassword",
            "password_confirm": "simplepassword",
            "role": UserRole.RECEPTIONIST,
            "first_name": "Weak",
            "last_name": "User",
            "phone_number": "+251911009988",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="weak_user").exists())

    def test_user_list_role_filter(self):
        url = f"{reverse('user-list')}?role=RECEPTIONIST"
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["role"], UserRole.RECEPTIONIST)

    def test_owner_toggle_user_active_status(self):
        url = reverse("user-toggle-active", kwargs={"pk": self.receptionist.pk})
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.receptionist.refresh_from_db()
        self.assertFalse(self.receptionist.is_active)

    def test_receptionist_cannot_create_staff_users(self):
        url = reverse("user-list")
        self.client.force_authenticate(user=self.receptionist)
        payload = {
            "username": "unauthorized_user",
            "email": "unauth@test.com",
            "password": "SecurePass2026!Str0ng",
            "password_confirm": "SecurePass2026!Str0ng",
            "role": UserRole.RECEPTIONIST,
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_receptionist(self):
        url = reverse("user-list")
        self.client.force_authenticate(user=self.manager)
        payload = {
            "username": "manager_created_rec",
            "email": "mgr_rec@test.com",
            "password": "SecurePass2026!Str0ng",
            "password_confirm": "SecurePass2026!Str0ng",
            "role": UserRole.RECEPTIONIST,
            "first_name": "Front",
            "last_name": "Desk",
            "phone_number": "+251977001122",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="manager_created_rec").exists())

    def test_manager_cannot_create_owner(self):
        url = reverse("user-list")
        self.client.force_authenticate(user=self.manager)
        payload = {
            "username": "illegal_owner",
            "email": "ill_owner@test.com",
            "password": "SecurePass2026!Str0ng",
            "password_confirm": "SecurePass2026!Str0ng",
            "role": UserRole.OWNER,
            "first_name": "Illegal",
            "last_name": "Owner",
            "phone_number": "+251977009900",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(username="illegal_owner").exists())
