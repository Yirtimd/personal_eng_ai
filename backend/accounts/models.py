from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone



# Создание модели пользователя
class CustomUser(AbstractUser):
    current_level = models.CharField(max_length=50, blank=True, null=True)
    learning_goals = models.TextField(blank=True, null=True)
    learning_plan = models.TextField(blank=True, null=True)
    completed_tasks = models.TextField(blank=True, null=True)
    deepseek_history = models.TextField(blank=True, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',  # Уникальное имя для обратного доступа
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_set',  # Уникальное имя для обратного доступа
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )


class Course(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
    
    
class Lesson(models.Model):
    course = models.ForeignKey(Course, related_name="lessons", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.URLField(blank=True, null=True)  # Добавляем поле для изображения
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
    
class Task(models.Model):
    lesson = models.ForeignKey(Lesson, related_name='tasks', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()  
    image = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title
    

class TestResult(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='testresult')
    grammar_score = models.PositiveIntegerField(default=0)
    vocabulary_score = models.PositiveIntegerField(default=0)
    reading_score = models.PositiveIntegerField(default=0)
    total_score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} Результаты теста"
    


