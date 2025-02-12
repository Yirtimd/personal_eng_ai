from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from knox.models import AuthToken
from .models import CustomUser, Course, Task, TestResult, Lesson
from .serializers import UserSerializer, CourseSerializer, TaskSerializer, TestResultSerializer
import json
from openai import OpenAI
from decouple import config

class RegisterAPI(generics.GenericAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)  # Логируем ошибки валидации
            return Response(serializer.errors, status=400)

        user = serializer.save()

        # Создаем связанный объект TestResult
        TestResult.objects.create(user=user)

        # Генерируем токен для пользователя
        _, token = AuthToken.objects.create(user)
        print(f"User registered: {user}")
        print(f"Token: {token}")

        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token
        })

class UserAPI(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
    

class LoginAPI(generics.GenericAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        user = CustomUser.objects.filter(email=email).first()

        if user and user.check_password(password):
            token = AuthToken.objects.create(user)[1] # создаем токен с помощью knox
            print(f"User logged in: {user}")
            print(f"Token: {token}")
            return Response({
                "user": UserSerializer(user, context=self.get_serializer_context()).data,
                "token": token
            })
        return Response({'error': 'Invalid credentials'}, status=400)
    
class CoursesListAPI(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


class TasksListAPI(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        user =  self.request.user
        return Task.objects.all()
    

class SaveTestResultView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TestResultSerializer

    def get(self, request):
        user = request.user
        try:
            test_result = user.testresult
            # Проверяем, есть ли ненулевые баллы
            if test_result.total_score > 0:
                return Response({
                    "test_completed": True,
                    "total_score": test_result.total_score
                }, status=200)
            else:
                return Response({
                    "test_completed": False,
                    "message": "Тест еще не пройден."
                }, status=200)
        except TestResult.DoesNotExist:
            return Response({
                "test_completed": False,
                "message": "Тест еще не пройден."
            }, status=200)

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        # Получаем или создаем объект TestResult для пользователя
        test_result, created = TestResult.objects.get_or_create(user=user)

        # Обновляем данные
        test_result.grammar_score = data.get('grammar_score', 0)
        test_result.vocabulary_score = data.get('vocabulary_score', 0)
        test_result.reading_score = data.get('reading_score', 0)
        test_result.total_score = (
            test_result.grammar_score +
            test_result.vocabulary_score +
            test_result.reading_score
        )
        test_result.save()

        serializer = self.get_serializer(test_result)
        return Response(serializer.data, status=200)
    

class GeneratePersonalizedProgramView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        try:
            test_result = user.testresult
        except AttributeError:
            return Response({"error": "Результаты теста не найдены."}, status=400)

        # Формируем данные для запроса к LLM
        payload = {
            "grammar_score": test_result.grammar_score,
            "vocabulary_score": test_result.vocabulary_score,
            "reading_score": test_result.reading_score,
            "total_score": test_result.total_score
        }

        # Получаем API-ключ из .env
        api_key = config('API_KEY')

        # Запрос к модели Deepseek R1
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

        system_prompt = """
        Based on the user's test scores (grammar, vocabulary, reading), generate a personalized learning program.
        The program should include 1 course with 3 lessons and tasks. Each lesson should have a title, content, and tasks.
        Output the result in JSON format.
        Example JSON output:
        {
            "course": {
                "title": "English for Beginners",
                "description": "A course for beginners...",
                "lessons": [
                    {
                        "title": "Lesson 1: Basic Grammar",
                        "content": "Learn about tenses...",
                        "tasks": [
                            {"title": "Task 1", "description": "Practice tenses...", "image": "https://example.com/image1.jpg"},
                            {"title": "Task 2", "description": "Complete exercises...", "image": "https://example.com/image2.jpg"}
                        ]
                    },
                    ...
                ]
            }
        }
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload)}
        ]

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                response_format={"type": "json_object"}
            )
            print("Ответ от OpenAI:", response)  # Логируем ответ
            llm_data = json.loads(response.choices[0].message.content)
        except Exception as e:
            print("Ошибка при запросе к OpenAI:", str(e))  # Логируем ошибку
            return Response({"error": "Не удалось получить данные от OpenAI."}, status=500)

        # Сохраняем курс, уроки и задания в базу данных
        course_data = llm_data.get("course", {})
        course = Course.objects.create(
            user=user,
            title=course_data.get("title"),
            description=course_data.get("description")
        )
        print(f"Создан курс: {course.title}")  # Логируем создание курса

        lessons = []
        for lesson_data in course_data.get("lessons", [])[:3]:  # Берем первые три урока
            lesson = Lesson.objects.create(
                course=course,
                title=lesson_data.get("title"),
                content=lesson_data.get("content"),
                image=lesson_data.get("image")
            )
            lessons.append(lesson)
            print(f"Создан урок: {lesson.title}")  # Логируем создание урока

            # Сохраняем задания для каждого урока
            for task_data in lesson_data.get("tasks", []):
                task = Task.objects.create(
                    lesson=lesson,  # Передаем lesson вместо course
                    title=task_data.get("title"),
                    description=task_data.get("description"),
                    image=task_data.get("image")
                )
                print(f"Создано задание: {task.title}")  # Логируем создание задания

        # Сериализуем данные для ответа
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=200)

class GeneratedCoursesView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseSerializer

    def get_queryset(self):
        user = self.request.user
        return Course.objects.filter(user=user).prefetch_related('lessons__tasks')
    



