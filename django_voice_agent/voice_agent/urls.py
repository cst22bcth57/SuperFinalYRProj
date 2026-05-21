from django.contrib import admin
from django.urls import path
from chatbot.views import home, chat_api, reset_session

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('chat/', chat_api, name='chat_api'),
    path('reset/', reset_session, name='reset_session'),
]
