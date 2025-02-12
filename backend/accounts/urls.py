from django.urls import path
from .views import RegisterAPI, UserAPI, LoginAPI, CoursesListAPI, TasksListAPI, SaveTestResultView, GeneratePersonalizedProgramView, GeneratedCoursesView

urlpatterns = [
    path('accounts/register/', RegisterAPI.as_view(), name='register'),
    path("accounts/user/", UserAPI.as_view(), name="user"),
    path('accounts/login/', LoginAPI.as_view(), name='login'),
    path("courses/", CoursesListAPI.as_view(), name="courses"),
    path("accounts/tasks/", TasksListAPI.as_view(), name="tasks"),
    path('test-result/', SaveTestResultView.as_view(), name='save-test-result'),
    path('generate-program/', GeneratePersonalizedProgramView.as_view(), name='generate-program'),
    path("generated-courses/", GeneratedCoursesView.as_view(), name="generated-courses")
]
