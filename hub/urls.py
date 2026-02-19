from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'hub'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('resource/delete/<int:pk>/', views.delete_resource, name='delete_resource'),
    path('user/delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('ajax/get-subjects/', views.get_subjects_ajax, name='get_subjects_ajax'),
    path('ajax/add-note/', views.add_note_ajax, name='add_note_ajax'),
    path('ajax/delete-note/', views.delete_note_ajax, name='delete_note_ajax'),
    path('ajax/get-notes/', views.get_notes_ajax, name='get_notes_ajax'),
    path('ajax/notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('ajax/search-subjects/', views.search_subjects_ajax, name='search_subjects_ajax'),
    path('ajax/toggle-registration/', views.toggle_registration_ajax, name='toggle_registration_ajax'),
    path('levels/', views.LevelsView.as_view(), name='levels'),
    path('level/<str:level_id>/', views.LevelDetailView.as_view(), name='level_detail'),
    path('subject/<int:subject_id>/<str:category>/', views.resource_view, name='resource_detail'),
    path('profile/', views.profile_settings, name='profile'),
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
    path('ai-assistant/delete/<int:session_id>/', views.delete_ai_session, name='delete_ai_session'),
    
    # New Homepage Resources
    path('resource/basic-software/', views.basic_software, name='basic_software'),
    path('resource/online-courses/', views.online_courses, name='online_courses'),
    path('resource/about-department/', views.about_department, name='about_department'),
    path('resource/academic-regulations/', views.academic_regulations, name='academic_regulations'),
    path('resource/credit-hour/', views.credit_hour, name='credit_hour'),
    path('resource/terminology/', views.engineering_terminology, name='engineering_terminology'),
    path('resource/study-plan/', views.study_plan, name='study_plan'),
    path('resource/registration/', views.registration, name='registration'),
    path('resource/time-management/', views.time_management, name='time_management'),
    path('resource/tools/', views.tools, name='tools'),
    path('resource/campus-guide/', views.campus_guide, name='campus_guide'),
    path('resource/academic-advice/', views.academic_advice, name='academic_advice'),
    path('resource/prerequisite-courses/', views.prerequisite_courses, name='prerequisite_courses'),

    
    # Contact & Chat
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('chat/start/', views.start_chat, name='chat_start'),
    path('chat/send/', views.send_message, name='chat_send'),
    path('chat/get/', views.get_messages, name='chat_get'),
    path('chat/sessions/', views.get_active_sessions, name='chat_sessions'),
    path('chat/end/', views.end_chat, name='chat_end'),
    path('chat/read/', views.mark_chat_read, name='chat_mark_read'),
    path('dashboard/admin/chat/', views.admin_chat_dashboard, name='admin_chat'),

    path('password-change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='hub/password_change_done.html'
    ), name='password_change_done'),

    # PWA Assets
    path('manifest.json', views.serve_manifest, name='manifest_json'),
    path('sw.js', views.serve_sw, name='service_worker'),
]
