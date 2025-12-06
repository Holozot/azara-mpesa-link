from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# 1. DEFINE THE MANAGER (Handles creating users)
class MyAccountManager(BaseUserManager):
    def create_user(self, first_name, last_name, username, email, password=None):
        if not email:
            raise ValueError('User must have an email address')
        
        if not username:
            raise ValueError('User must have an username')

        user = self.model(
            email = self.normalize_email(email), # Lowers email to standard format
            username = username,
            first_name = first_name,
            last_name = last_name,
        )

        user.set_password(password) # Encrypts the password
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, username, password):
        user = self.create_user(
            email = self.normalize_email(email),
            username = username,
            password = password,
            first_name = first_name,
            last_name = last_name,
        )
        user.is_admin = True
        user.is_active = True
        user.is_staff = True
        user.is_superadmin = True
        user.save(using=self._db)
        return user

# 2. DEFINE THE MODEL (The Database Table)
class Account(AbstractBaseUser, PermissionsMixin):
    first_name      = models.CharField(max_length=50)
    last_name       = models.CharField(max_length=50)
    username        = models.CharField(max_length=50, unique=True)
    email           = models.EmailField(max_length=100, unique=True)
    phone_number    = models.CharField(max_length=50)

    # Required Django fields
    date_joined     = models.DateTimeField(auto_now_add=True)
    last_login      = models.DateTimeField(auto_now_add=True)
    is_admin        = models.BooleanField(default=False)
    is_staff        = models.BooleanField(default=False)
    is_active       = models.BooleanField(default=False)
    is_superadmin   = models.BooleanField(default=False)

    # SET LOGIN FIELD TO EMAIL
    USERNAME_FIELD  = 'email' 
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    SECURITY_QUESTIONS = [
        ('pet', "What was the name of your first pet?"),
        ('mother', "What is your mother's maiden name?"),
        ('city', "In what city were you born?"),
        ('school', "What was the name of your first school?"),
    ]
    security_question = models.CharField(max_length=50, choices=SECURITY_QUESTIONS, default='pet')
    security_answer = models.CharField(max_length=100, default='')

    objects = MyAccountManager()

    def __str__(self):
        return self.email

    # Required methods for permissions
    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, add_label):
        return True