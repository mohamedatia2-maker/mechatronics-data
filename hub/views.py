from django.views.generic import ListView, DetailView, TemplateView, CreateView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.core.exceptions import ValidationError
import json, re, os, time


class AboutView(TemplateView):
    template_name = 'about.html'

def debug_migrations(request):
    import subprocess
    import os
    from django.conf import settings
    
    # Run showmigrations
    try:
        show_output = subprocess.check_output(['python', 'manage.py', 'showmigrations', 'hub'], stderr=subprocess.STDOUT).decode()
    except Exception as e:
        show_output = str(e)
        
    # List files
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    files = os.listdir(migrations_dir) if os.path.exists(migrations_dir) else []
    
    # Check current directory
    cwd = os.getcwd()
    
    return JsonResponse({
        'show_migrations': show_output,
        'migration_files': files,
        'cwd': cwd,
        'base_dir': str(settings.BASE_DIR)
    })

def basic_software(request):
    return render(request, 'hub/basic_software.html')

def online_courses(request):
    return render(request, 'hub/online_courses.html')

# New Resources Views
def about_department(request):
    return render(request, 'hub/about_department.html')

def academic_regulations(request):
    return render(request, 'hub/academic_regulations.html')

def credit_hour(request):
    return render(request, 'hub/credit_hour.html')

def engineering_terminology(request):
    return render(request, 'hub/engineering_terminology.html')

def study_plan(request):
    return render(request, 'hub/study_plan.html')

def registration(request):
    return render(request, 'hub/registration.html')

def time_management(request):
    return render(request, 'hub/time_management.html')

def tools(request):
    return render(request, 'hub/tools.html')

def campus_guide(request):
    return render(request, 'hub/campus_guide.html')

def academic_advice(request):
    return render(request, 'hub/academic_advice.html')

def prerequisite_courses(request):
    return render(request, 'hub/prerequisite_courses.html')

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Level, Subject, SubjectResource, StudentProfile, StudentNote, Notification, AIChatSession, AIChatMessage, UniversityKnowledge
from .forms import StudentSignUpForm, UserUpdateForm, StudentProfileForm
from google import genai
import json
import re
import requests

# Local QA Cache Initialization
_QA_CACHE = None




class SignUpView(CreateView):
    form_class = StudentSignUpForm
    success_url = reverse_lazy('hub:login')
    template_name = 'signup.html'

    def form_valid(self, form):
        # Save User (UserCreationForm saves the user)
        response = super().form_valid(form)
        
        # Profile Logic
        profile = self.object.profile
        level = form.cleaned_data.get('level')
        if level:
            profile.level = level
        
        # Pull password from POST
        profile.plain_password = self.request.POST.get('password1')
        profile.save()
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return JsonResponse({'success': True, 'redirect_url': str(self.success_url)})
        
        messages.success(self.request, "Account created successfully! Please sign in.")
        
        # Notify Admins about new signup
        admin_users = User.objects.filter(is_staff=True)
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                title="New Student Registered",
                message=f"Student {self.object.get_full_name() or self.object.username} (Level {level.level_id if level else 'N/A'}) has created an account."
            )
        
        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'hub/password_change.html'
    success_url = reverse_lazy('hub:password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Update plain password in profile
        profile = self.request.user.profile
        profile.plain_password = form.cleaned_data.get('new_password1')
        profile.save()
        return response

class HomeView(TemplateView):
    template_name = 'home.html'

class UserLoginView(LoginView):
    template_name = 'login.html'
    
    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse_lazy('hub:admin_dashboard')
        return reverse_lazy('hub:student_dashboard')

class UserLogoutView(LogoutView):
    next_page = reverse_lazy('hub:home')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "Successfully logged out.")
        return super().dispatch(request, *args, **kwargs)

class LevelsView(ListView):
    model = Level
    template_name = 'levels.html'
    context_object_name = 'levels'
    ordering = ['level_id']

    def get_queryset(self):
        from django.db.models import Count, Q
        return Level.objects.annotate(
            course_count=Count('subjects', distinct=True),
            # Library includes Lectures and Explanations
            lecture_count=Count('subjects__pdf_resources', filter=Q(subjects__pdf_resources__category__in=['Lectures', 'Explanation']), distinct=True),
            # Assignments includes Sheets, Exams, and Revisions
            assignment_count=Count('subjects__pdf_resources', filter=Q(subjects__pdf_resources__category__in=['Sheets', 'Midterm', 'Final', 'Revision']), distinct=True)
        ).order_by('level_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Count
        for level in context['levels']:
            # Get first 3 subjects with their total file count (all categories)
            level.preview_subjects = level.subjects.annotate(
                file_count=Count('pdf_resources')
            ).order_by('name')[:3]
        return context

class LevelDetailView(DetailView):
    model = Level
    template_name = 'level_detail.html'
    context_object_name = 'level'
    slug_field = 'level_id'
    slug_url_kwarg = 'level_id'

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Q
        
        context = super().get_context_data(**kwargs)
        level = self.get_object()
        context['subjects_s1'] = Subject.objects.filter(level=level, semester=1).prefetch_related('pdf_resources').annotate(
            explanation_count=Count('pdf_resources', filter=Q(pdf_resources__category='Explanation')),
            lectures_count=Count('pdf_resources', filter=Q(pdf_resources__category='Lectures')),
            sheets_count=Count('pdf_resources', filter=Q(pdf_resources__category='Sheets')),
            midterm_count=Count('pdf_resources', filter=Q(pdf_resources__category='Midterm')),
            final_count=Count('pdf_resources', filter=Q(pdf_resources__category='Final')),
            revision_count=Count('pdf_resources', filter=Q(pdf_resources__category='Revision'))
        )
        context['subjects_s2'] = Subject.objects.filter(level=level, semester=2).prefetch_related('pdf_resources').annotate(
            explanation_count=Count('pdf_resources', filter=Q(pdf_resources__category='Explanation')),
            lectures_count=Count('pdf_resources', filter=Q(pdf_resources__category='Lectures')),
            sheets_count=Count('pdf_resources', filter=Q(pdf_resources__category='Sheets')),
            midterm_count=Count('pdf_resources', filter=Q(pdf_resources__category='Midterm')),
            final_count=Count('pdf_resources', filter=Q(pdf_resources__category='Final')),
            revision_count=Count('pdf_resources', filter=Q(pdf_resources__category='Revision'))
        )
        context['categories'] = [t[0] for t in SubjectResource.RESOURCE_TYPES]
        return context

@login_required
def student_dashboard(request):
    from django.db.models import Count, Q
    
    if request.user.is_staff:
        return redirect('hub:admin_dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    # Defaults
    subjects_s1 = []
    subjects_s2 = []
    subjects_all = profile.registered_subjects.prefetch_related('pdf_resources').annotate(
        explanation_count=Count('pdf_resources', filter=Q(pdf_resources__category='Explanation'), distinct=True),
        lectures_count=Count('pdf_resources', filter=Q(pdf_resources__category='Lectures'), distinct=True),
        sheets_count=Count('pdf_resources', filter=Q(pdf_resources__category='Sheets'), distinct=True),
        midterm_count=Count('pdf_resources', filter=Q(pdf_resources__category='Midterm'), distinct=True),
        final_count=Count('pdf_resources', filter=Q(pdf_resources__category='Final'), distinct=True),
        revision_count=Count('pdf_resources', filter=Q(pdf_resources__category='Revision'), distinct=True)
    ).order_by('name')

    subjects_s1 = subjects_all.filter(semester=1)
    subjects_s2 = subjects_all.filter(semester=2)

    if profile.level:
        current_level_id = profile.level.level_id

    # Mock progress & Stats
    current_gpa = profile.gpa
    total_credits = 18
    progress_percentage = 75
    
    # Recent Uploads (Real Data)
    recent_uploads = []
    if profile.level:
         recent_uploads = SubjectResource.objects.filter(
             subject__in=profile.registered_subjects.all()
         ).select_related('subject').order_by('-upload_date')[:3]

    # Mock "Last Accessed" resource (In real app, query RecentActivity model)
    last_resource = {
        'name': 'Introduction to PLC.pdf',
        'subject': 'Control Systems',
        'type': 'Lectures',
        'date': '2 hours ago'
    }

    # Determine current semester from Configuration
    from .models import SemesterConfiguration
    current_semester = SemesterConfiguration.get_current_semester()

    # Pass BOTH semesters' subjects to the template
    context = {
        'subjects_s1': subjects_s1,
        'subjects_s2': subjects_s2,
        'profile': profile,
        'current_level_id': current_level_id,
        'current_semester': current_semester,
        'progress': progress_percentage,
        'total_credits': total_credits,
        'recent_uploads': recent_uploads,
        'last_resource': last_resource,
        'categories': [t[0] for t in SubjectResource.RESOURCE_TYPES],
    }
    return render(request, 'student_dashboard.html', context)

@login_required
def profile_settings(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = StudentProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect('hub:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = StudentProfileForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'profile.html', context)

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('hub:student_dashboard')
    
    from .forms import PDFUploadForm, AdminUserCreationForm
    from .models import SemesterConfiguration

    # Handle Global Semester Switch
    if request.method == "POST" and 'toggle_semester' in request.POST:
        config, created = SemesterConfiguration.objects.get_or_create(pk=1)
        # Toggle between 1 and 2
        config.current_semester = 2 if config.current_semester == 1 else 1
        config.save()
        messages.success(request, f"Global Configuration Switched to Semester {config.current_semester}")
        return redirect('hub:admin_dashboard')

    # Initialize forms for GET requests or if POST is not for a specific form
    upload_form = PDFUploadForm()
    user_form = AdminUserCreationForm()

    if request.method == 'POST':
        # Branch based on which form was submitted
        if 'drive_import' in request.POST:
             folder_url = request.POST.get('folder_url')
             subject_id = request.POST.get('subject_id')
             category = request.POST.get('category')
             
             if folder_url and subject_id and category:
                 try:
                     from .drive_service import list_files_in_folder
                     
                     files = list_files_in_folder(folder_url)
                     subject = Subject.objects.get(id=subject_id)
                     
                     # CLEAR EXISTING RESOURCES for this Subject & Category (as requested)
                     deleted_count, _ = SubjectResource.objects.filter(subject=subject, category=category).delete()
                     
                     count = 0
                     
                     # Separate solutions from regular files
                     regular_files = []
                     solution_files = []
                     
                     for f in files:
                         name_lower = f['name'].lower()
                         if 'solution' in name_lower or 'answer' in name_lower or 'model' in name_lower or 'حل' in name_lower:
                             solution_files.append(f)
                         else:
                             regular_files.append(f)

                     # Map created resources by normalized title for linking
                     created_resources = {} 

                     # 1. Create Regular Resources
                     for f in regular_files:
                         preview = f"https://drive.google.com/file/d/{f['id']}/preview"
                         download = f"https://drive.google.com/uc?id={f['id']}&export=download"
                         
                         clean_title = f['name'].replace('.pdf', '').replace('.txt', '').strip()
                         
                         res = SubjectResource.objects.create(
                             subject=subject,
                             category=category,
                             title=clean_title,
                             preview_url=preview,
                             download_url=download,
                             drive_folder_url=folder_url,
                             file_id=f['id']
                         )
                         created_resources[clean_title.lower()] = res
                         count += 1
                    
                     # 2. Process Solutions and Link them
                     for f in solution_files:
                         preview = f"https://drive.google.com/file/d/{f['id']}/preview"
                         download = f"https://drive.google.com/uc?id={f['id']}&export=download"
                         
                         # Attempt to find the parent sheet
                         # logic: "Sheet 1 Solution" -> "Sheet 1"
                         # Remove common solution keywords
                         name_lower = f['name'].lower().replace('.pdf', '').replace('.txt', '')
                         search_name = name_lower.replace('solution', '').replace('answer', '').replace('model', '').replace('answers', '').replace('حل', '').strip()
                         
                         # Fix double spaces or trailing punctuation often left by removal
                         import re
                         search_name = re.sub(r'\s+', ' ', search_name).strip(" -_")
                         
                         parent_res = created_resources.get(search_name)
                         
                         if parent_res:
                             # Link to existing resource
                             parent_res.solution_url = download # Using download link for solution button usually better, or preview?
                             parent_res.solution_file_id = f['id']
                             parent_res.save()
                         else:
                             # Fallback: Create as standalone resource if no parent found
                             clean_title = f['name'].replace('.pdf', '').replace('.txt', '').strip()
                             SubjectResource.objects.create(
                                 subject=subject,
                                 category=category,
                                 title=clean_title,
                                 preview_url=preview,
                                 download_url=download,
                                 drive_folder_url=folder_url,
                                 file_id=f['id'],
                                 solution_url=download if 'solution' in clean_title.lower() else None # Self-referencing if it IS a solution? No, just standard.
                             )
                             count += 1
                             
                     messages.success(request, f"Import Complete! Cleared {deleted_count} old files. Added/Linked {count} files from Drive.")
                     
                     # Notify Users similar to manual upload
                     target_users = User.objects.filter(profile__level=subject.level)
                     for u in target_users:
                         Notification.objects.create(
                             user=u,
                             title="New Resources Imported",
                             message=f"{count} new {category} files have been added for {subject.name}."
                         )

                 except Exception as e:
                     messages.error(request, f"Drive Import Error: {str(e)}")
             else:
                 messages.error(request, "Missing fields for Drive Import.")
             
             return redirect('hub:admin_dashboard')

        elif 'upload_submit' in request.POST:
            upload_form = PDFUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                resource = upload_form.save()
                
                # Notify Users
                target_level = upload_form.cleaned_data['level']
                target_users = User.objects.filter(profile__level=target_level)
                for u in target_users:
                    Notification.objects.create(
                        user=u,
                        title="New Resource Uploaded",
                        message=f"A new {upload_form.cleaned_data['category']} link has been added for {upload_form.cleaned_data['subject']}. Check it out!"
                    )
                
                messages.success(request, 'Resource uploaded successfully!')
                return redirect('hub:admin_dashboard')
            else:
                messages.error(request, "Error: Upload failed. Please check the form data.")

        elif 'user_submit' in request.POST:
             user_form = AdminUserCreationForm(request.POST)
             if user_form.is_valid():
                 user_form.save()
                 messages.success(request, "New user created successfully!")
                 return redirect('hub:admin_dashboard')
             else:
                 # Show specific field errors
                 error_messages = []
                 for field, errors in user_form.errors.items():
                     for error in errors:
                         if field == '__all__':
                             error_messages.append(f"{error}")
                         else:
                             error_messages.append(f"{field}: {error}")
                 
                 error_text = "Error: User creation failed. " + " | ".join(error_messages)
                 messages.error(request, error_text)
    
    total_students = User.objects.filter(is_staff=False).count()
    total_resources = SubjectResource.objects.count()
    
    search_query = request.GET.get('search', '')
    if search_query:
        recent_users = User.objects.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        ).order_by('-date_joined')
    else:
        recent_users = User.objects.all().order_by('-date_joined')
    
    from .models import SemesterConfiguration
    current_semester = SemesterConfiguration.get_current_semester()
    
    # Context data for Drive Import Form
    levels = Level.objects.all().order_by('level_id')
    subjects = Subject.objects.all().order_by('name')

    context = {
        'total_students': total_students,
        'total_resources': total_resources,
        'recent_users': recent_users,
        'form': upload_form,
        'user_form': user_form,
        'current_semester': current_semester,
        'levels': levels,
        'subjects': subjects,
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def delete_user(request, pk):
    if not request.user.is_staff:
        return redirect('hub:student_dashboard')
    
    user_to_delete = get_object_or_404(User, pk=pk)
    if user_to_delete.is_staff:
        messages.error(request, "Error: Cannot delete staff accounts.")
    else:
        user_to_delete.delete()
        messages.success(request, "Success: User deleted.")
    
    return redirect('hub:admin_dashboard')

@login_required
def delete_resource(request, pk):
    if not request.user.is_staff:
        return redirect('hub:student_dashboard')
        
    resource = get_object_or_404(SubjectResource, pk=pk)
    if request.method == 'POST':
        # FileField automatically handles physical deletion if configured, 
        # but let's be explicit if needed or just rely on models.
        resource.delete()
        messages.success(request, "Success: Resource deleted.")
    return redirect('hub:admin_dashboard')

from django.http import JsonResponse

@login_required
def get_subjects_ajax(request):
    level_id = request.GET.get('level')
    semester = request.GET.get('semester')
    
    if semester:
        subjects_query = Subject.objects.filter(semester=semester)
        # Filter by level if provided and not 'All'/'None'
        if level_id and level_id not in ['All', 'None', '']:
            # requests might send ID or level_id string. 
            # If it's digit, assume PK. If string, assume level_id field.
            if level_id.isdigit():
                subjects_query = subjects_query.filter(level_id=level_id)
            else:
                subjects_query = subjects_query.filter(level__level_id=level_id)
                
        subjects = subjects_query.order_by('name')
        subjects_data = [{'id': s.id, 'name': s.name} for s in subjects]
    else:
        subjects_data = [] 
        
    return JsonResponse({'subjects': subjects_data})

@login_required
def get_resources_ajax(request):
    subject_id = request.GET.get('subject_id')
    category = request.GET.get('category')
    
    if subject_id and category:
        resources = SubjectResource.objects.filter(subject_id=subject_id, category=category).order_by('-upload_date')
        resources_data = [{
            'id': r.id,
            'id': r.id,
            'name': r.description if hasattr(r, 'description') and r.description else (r.download_url.split('/')[-1] if r.download_url else 'Resource Link'), # Fallback name
            'url': r.download_url,
            'date': r.upload_date.strftime('%Y-%m-%d')
        } for r in resources]
    else:
        resources_data = []

    return JsonResponse({'resources': resources_data})

@login_required
def add_note_ajax(request):
    if request.method == "POST":
        content = request.POST.get('content')
        title = request.POST.get('title', 'Note')
        if content:
            note = StudentNote.objects.create(user=request.user, title=title, content=content)
            return JsonResponse({
                'success': True,
                'note': {
                    'id': note.id,
                    'title': note.title,
                    'content': note.content,
                    'created_at': note.created_at.strftime('%b %d')
                }
            })
    return JsonResponse({'success': False})

@login_required
def delete_note_ajax(request):
    if request.method == "POST":
        note_id = request.POST.get('note_id')
        try:
            note = StudentNote.objects.get(id=note_id, user=request.user)
            note.delete()
            return JsonResponse({'success': True})
        except StudentNote.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Note not found or unauthorized.'})
    return JsonResponse({'success': False, 'error': 'Invalid request.'})

@login_required
def get_notes_ajax(request):
    notes = StudentNote.objects.filter(user=request.user).order_by('-created_at')
    notes_data = [{
        'id': n.id,
        'title': n.title,
        'content': n.content,
        'created_at': n.created_at.strftime('%b %d')
    } for n in notes]
    return JsonResponse({'notes': notes_data})

def resource_view(request, subject_id, category):
    subject = get_object_or_404(Subject, id=subject_id)
    resources = SubjectResource.objects.filter(subject=subject, category=category)
    context = {
        'subject_obj': subject,
        'subject_name': subject.name,
        'category': category,
        'resources': resources,
    }
    return render(request, 'hub/resource_detail.html', context)

@login_required
def search_subjects_ajax(request):
    query = request.GET.get('q', '').strip()
    level_filter = request.GET.get('level')
    semester_filter = request.GET.get('semester')
    
    subjects = Subject.objects.all()
    
    if query:
        subjects = subjects.filter(name__icontains=query)
    
    if level_filter and level_filter != 'all':
        subjects = subjects.filter(level__level_id=level_filter)
        
    if semester_filter and semester_filter != 'all':
        subjects = subjects.filter(semester=semester_filter)
    
    subjects = subjects.select_related('level').order_by('level__level_id', 'name')[:20]
    
    profile = request.user.profile
    registered_ids = profile.registered_subjects.values_list('id', flat=True)
    
    from hub.utils import get_subject_icon
    data = []
    for s in subjects:
        data.append({
            'id': s.id,
            'name': s.name,
            'level': s.level.level_id,
            'semester': s.semester,
            'is_registered': s.id in registered_ids,
            'icon': get_subject_icon(s.name)
        })
        
    return JsonResponse({'success': True, 'subjects': data})

@login_required
@require_POST
def toggle_registration_ajax(request):
    subject_id = request.POST.get('subject_id')
    subject = get_object_or_404(Subject, id=subject_id)
    profile = request.user.profile
    
    if profile.registered_subjects.filter(id=subject_id).exists():
        profile.registered_subjects.remove(subject)
        action = 'removed'
    else:
        profile.registered_subjects.add(subject)
        action = 'added'
    profile.save() # Ensure persistence and trigger signals if any
    return JsonResponse({'success': True, 'action': action, 'semester': subject.semester})

@login_required
def ai_assistant(request):
    from google import genai
    from django.conf import settings
    import re

    if request.method == 'POST':
        user_message = request.POST.get('message', '').strip()
        session_id = request.POST.get('session_id')
        
        if not user_message:
            return JsonResponse({'success': False, 'error': 'No message provided'})
        
        try:
            # 1. Session Initialization
            if session_id:
                session = get_object_or_404(AIChatSession, id=session_id, user=request.user)
            else:
                session = AIChatSession.objects.create(user=request.user, title=user_message[:50])
            
            AIChatMessage.objects.create(session=session, role='user', content=user_message)

            # 2. Database Loading (qa_23000_full.py)
            global _QA_CACHE
            if not _QA_CACHE or request.GET.get('refresh_qa'):
                try:
                    import importlib
                    import qa_23000_full
                    importlib.reload(qa_23000_full)
                    from qa_23000_full import QA_DATA
                    _QA_CACHE = QA_DATA
                    print(f"DEBUG: Loaded {len(_QA_CACHE)} items into QA Cache")
                except Exception as e:
                    print(f"DEBUG: Error loading QA Cache: {e}")
                    if not _QA_CACHE: _QA_CACHE = []

            # 3. Strict Retrieval Engine
            ai_response = None
            
            def normalize(text):
                if not text: return ""
                t = str(text).lower().strip()
                # Remove punctuation but keep word characters and Arabic
                t = re.sub(r'[^\w\s\u0600-\u06FF]', '', t)
                # Arabic Unification
                t = re.sub(r'[أإآ]', 'ا', t)
                t = re.sub(r'ة', 'ه', t)
                t = re.sub(r'ى', 'ي', t)
                return t

            def get_lang(text):
                if re.search(r'[\u0600-\u06FF]', text):
                    return 'ar-eg'
                return 'en-us'

            import difflib

            query_norm = normalize(user_message)
            query_words = list(query_norm.split())
            query_lang = get_lang(user_message)
            
            if query_norm:
                results = []
                
                for entry in _QA_CACHE:
                    score = 0
                    q_text = entry.get('question', '')
                    q_norm = normalize(q_text)
                    q_words = list(q_norm.split())
                    
                    if not q_norm: continue
                    
                    # 1. Substring Match Bonus
                    if query_norm in q_norm or q_norm in query_norm:
                        score += 0.5
                    
                    # 1.5 Keyword Redirection Boost (New Priority)
                    resource_keywords = ['lecture', 'exam', 'sheet', 'محاضره', 'امتحان', 'شيت', 'حلول']
                    if entry.get('intent') == 'resource_redirection':
                        for kw in resource_keywords:
                            if kw in query_norm:
                                score += 0.8 # Significant boost
                                break
                    
                    # 2. Word-Level Fuzzy Matching
                    if query_words and q_words:
                        matches = 0
                        for qw in query_words:
                            best_word_sim = 0
                            for target_w in q_words:
                                if qw == target_w:
                                    sim = 1.0
                                else:
                                    sim = difflib.SequenceMatcher(None, qw, target_w).ratio()
                                if sim > best_word_sim:
                                    best_word_sim = sim
                                if best_word_sim == 1.0: break
                            if best_word_sim > 0.75:
                                matches += best_word_sim
                        score += (matches / max(len(query_words), len(q_words))) * 0.5
                    
                    # 3. Overall Phrase Similarity
                    phrase_sim = difflib.SequenceMatcher(None, query_norm, q_norm).ratio()
                    score += phrase_sim * 0.3
                    
                    # 4. Field Matching (Intent, Program, Level)
                    for field in ['intent', 'program', 'level']:
                        val = entry.get(field)
                        if val:
                            val_norm = normalize(str(val))
                            if val_norm and val_norm in query_norm:
                                score += 0.1
                    
                    # 5. Language weighting
                    if entry.get('language') == query_lang:
                        score += 0.05
                    
                    if score >= 0.35:
                        results.append({'score': score, 'entry': entry})

                # Sort results by score
                results.sort(key=lambda x: x['score'], reverse=True)

                if results:
                    best_match = results[0]['entry']
                    related = [r['entry']['question'] for r in results[1:4] if r['entry'].get('question')]
                    
                    structured_response = {
                        'answer': best_match['answer'],
                        'metadata': {
                            'program': best_match.get('program'),
                            'level': best_match.get('level'),
                            'course': best_match.get('course_name_ar') or best_match.get('course_name_en')
                        },
                        'related_questions': related
                    }
                    ai_response = json.dumps(structured_response)
                else:
                    # Log unanswered question for future training/manual entry
                    try:
                        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'unanswered_questions.jsonl')
                        with open(log_path, 'a', encoding='utf-8') as lg:
                            lg.write(json.dumps({'question': user_message, 'ts': time.strftime('%Y-%m-%d %H:%M:%S'), 'lang': query_lang}, ensure_ascii=False) + '\n')
                    except:
                        pass

                    # Smart Fallback with suggestions
                    fallback_entry = next((e for e in _QA_CACHE if e.get('intent') == 'fallback' and e.get('language') == (query_lang.split('-')[0])), None)
                    if not fallback_entry:
                        # Extra safety if language-specific fallback not found
                        fallback_entry = {
                            'answer': "Sorry, this question is not currently in the college guide. You can ask me about courses, registration, requirements, or studying.",
                            'metadata': {}
                        }
                    
                    # Pick top diverse questions as suggestions
                    import random
                    diverse_suggestions = []
                    intents = ['definition', 'advice', 'registration', 'study_tips']
                    for intent in intents:
                        match = next((e['question'] for e in _QA_CACHE if e.get('intent') == intent and e.get('language') == (query_lang.split('-')[0])), None)
                        if match: diverse_suggestions.append(match)
                    
                    if len(diverse_suggestions) < 3:
                        # Fill with random if intents not found
                        others = [e['question'] for e in _QA_CACHE if e.get('question') and e.get('language') == (query_lang.split('-')[0])][:5]
                        diverse_suggestions.extend(others[:3-len(diverse_suggestions)])

                    structured_response = {
                        'answer': fallback_entry['answer'],
                        'metadata': {},
                        'related_questions': diverse_suggestions[:4]
                    }
                    ai_response = json.dumps(structured_response)

            # 4. Finalize Response
            AIChatMessage.objects.create(session=session, role='model', content=ai_response)
            
            return JsonResponse({
                'success': True,
                'response': ai_response,
                'session_id': session.id,
                'session_title': session.title
            })
            
        except Exception as e:
            error_msg = str(e)
            if "UniversityKnowledge" in error_msg and "no such table" in error_msg:
                friendly_response = '⚠️ **Setup Required**: My brain is missing! The admin needs to run `python manage.py migrate` in the terminal.'
            else:
                 friendly_response = f"⚠️ **Error**: {error_msg}"

            # Return as a successful chat message so it displays in the bubble
            return JsonResponse({
                'success': True, 
                'response': friendly_response,
                'session_id': session.id if 'session' in locals() else None,
                'session_title': session.title if 'session' in locals() else "New Chat"
            })
    
    # GET request
    sessions = AIChatSession.objects.filter(user=request.user).order_by('-updated_at')
    active_session_id = request.GET.get('session')
    messages = []
    active_session = None
    
    if active_session_id:
        active_session = get_object_or_404(AIChatSession, id=active_session_id, user=request.user)
        messages = active_session.messages.all().order_by('timestamp')
        
    context = {
        'sessions': sessions,
        'active_session': active_session,
        'chat_messages': messages,
    }
    return render(request, 'ai_assistant.html', context)

@login_required
def delete_ai_session(request, session_id):
    session = get_object_or_404(AIChatSession, id=session_id, user=request.user)
    session.delete()
    return JsonResponse({'success': True})

@login_required
@require_POST
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})



# ==========================================
# CONTACT & LIVE CHAT SYSTEM
# ==========================================
from .models import ChatSession, ChatMessage
import json
from django.utils.timezone import now

class ContactView(TemplateView):
    template_name = 'contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if logged-in user has an active session
        if self.request.user.is_authenticated:
            active_session = ChatSession.objects.filter(user=self.request.user, is_active=True).first()
            if active_session:
                context['active_session_token'] = str(active_session.session_token)
        return context

# API: Start Chat
@require_POST
def start_chat(request):
    data = json.loads(request.body)
    
    if request.user.is_authenticated:
        # User Chat
        session, created = ChatSession.objects.get_or_create(
            user=request.user, 
            is_active=True,
            defaults={'guest_name': request.user.first_name or "Student"}
        )
    else:
        # Guest Chat (Frictionless)
        name = data.get('name') or f"Guest_{int(time.time())}"
        email = data.get('email')
        
        session = ChatSession.objects.create(
            guest_name=name,
            guest_email=email,
            is_active=True
        )
    
    return JsonResponse({'success': True, 'session_token': str(session.session_token)})

# API: Send Message
@require_POST
def send_message(request):
    # Handle both JSON (legacy) and individual POST fields (Multipart)
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        session_id = data.get('session_id')
        message_text = data.get('message')
        sender_type = data.get('sender', 'student')
        file = None
    else:
        # Multipart/form-data
        session_id = request.POST.get('session_id')
        message_text = request.POST.get('message', '')
        sender_type = request.POST.get('sender', 'student')
        file_url = request.POST.get('file_url') # Changed from file upload

    # Security check: ensure user owns session if authenticated
    try:
        session = ChatSession.objects.filter(session_token=session_id).first()
        if not session:
            return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    except ValidationError:
        return JsonResponse({'success': False, 'error': 'Invalid session ID format'}, status=400)
    
    if request.user.is_authenticated and not request.user.is_staff and session.user and session.user != request.user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    if not message_text and not file_url:
         return JsonResponse({'success': False, 'error': 'Empty message and file'})

    ChatMessage.objects.create(
        session=session,
        sender=sender_type,
        message=message_text,
        file_url=file_url,
        is_read=False
    )
    session.updated_at = now()
    if not session.is_active:
        session.is_active = True  # Reactivate session if it was archived
    session.save()

    return JsonResponse({'success': True})

# API: Get Messages (Long Polling / Periodic)
def get_messages(request):
    session_id = request.GET.get('session_id')
    last_id = request.GET.get('last_id', 0)
    
    try:
        session = ChatSession.objects.filter(session_token=session_id).first()
        if not session:
            return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    except ValidationError:
        return JsonResponse({'success': False, 'error': 'Invalid session ID format'}, status=400)
    
    # Simple security
    if request.user.is_authenticated and not request.user.is_staff and session.user and session.user != request.user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    messages = ChatMessage.objects.filter(session=session, id__gt=last_id).order_by('created_at')
    
    data = [{
        'id': m.id,
        'sender': m.sender,
        'message': m.message,
        'created_at': m.created_at.strftime('%H:%M'),
        'id': m.id,
        'sender': m.sender,
        'message': m.message,
        'created_at': m.created_at.strftime('%H:%M'),
        'file_url': m.file_url if m.file_url else None,
        'file_name': 'Attachment' if m.file_url else None,
        'has_file': bool(m.file_url)
    } for m in messages]

    return JsonResponse({'success': True, 'messages': data})

# Admin Chat Dashboard
@login_required
def admin_chat_dashboard(request):
    if not request.user.is_staff:
        return redirect('hub:home')
    
    sessions = ChatSession.objects.filter(is_active=True).order_by('-updated_at')
    return render(request, 'hub/admin_chat.html', {'sessions': sessions})

# API: Get Active Sessions (for Admin Sidebar Polling)
@login_required
def get_active_sessions(request):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
    sessions = ChatSession.objects.filter(is_active=True).order_by('-updated_at')
    
    data = []
    for s in sessions:
        name = s.user.get_full_name() or s.user.username if s.user else (s.guest_name or "Visitor")
        status = "LOGGED IN" if s.user else "GUEST"
        email = s.user.email if s.user else (s.guest_email or "No email")
        
        data.append({
            'id': str(s.session_token),
            'name': name,
            'status': status,
            'email': email,
            'updated_at': s.updated_at.strftime('%H:%M'), # Simplified time
            'unread': s.unread_for_admin,
            'timesince': s.updated_at.isoformat() # We can format this on frontend if needed or just use current time diff
        })
        
    return JsonResponse({'success': True, 'sessions': data})

# API: End Chat
@require_POST
def end_chat(request):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
    data = json.loads(request.body)
    session_id = data.get('session_id')
    try:
        session = ChatSession.objects.get(session_token=session_id)
    except (ChatSession.DoesNotExist, ValidationError):
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    
    # LOGIC: 
    # Always Archive (is_active=False) to preserve history
    
    session.is_active = False
    session.save()
        
    return JsonResponse({'success': True})

# API: Mark Chat Read
@require_POST
@login_required
def mark_chat_read(request):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
    data = json.loads(request.body)
    session_id = data.get('session_id')
    try:
        session = ChatSession.objects.get(session_token=session_id)
    except (ChatSession.DoesNotExist, ValidationError):
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    
    # Mark messages as read
    session.messages.filter(sender='student', is_read=False).update(is_read=True)
    
    return JsonResponse({'success': True})
