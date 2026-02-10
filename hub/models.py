import os
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

class Level(models.Model):
    level_id = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=200)
    icon_name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.level_id} - {self.title}"

class Subject(models.Model):
    name = models.CharField(max_length=200)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='subjects')
    semester = models.IntegerField(choices=[(1, 'Semester 1'), (2, 'Semester 2')])

    def __str__(self):
        return f"{self.name} (LV {self.level.level_id})"




def get_resource_upload_path(instance, filename):
    level_id = instance.subject.level.level_id
    semester = instance.subject.semester
    term_name = "First Term" if semester == 1 else "Second Term"
    
    # Structure match user's manual organization:
    # resources/Level{ID}/Level {ID} {Term}/Subject/Category/filename
    # This logic is deprecated for file storage but kept if needed for path generation logic elsewhere, 
    # though it will likely be unused with URL fields.
    return os.path.join(
        'resources', 
        f'Level{level_id}', 
        f'Level {level_id} {term_name}', 
        instance.subject.name, 
        instance.category, 
        filename
    )


class SubjectResource(models.Model):
    RESOURCE_TYPES = [
        ('Explanation', 'Explanation'),
        ('Lectures', 'Lectures'),
        ('Sheets', 'Sheets'),
        ('Midterm', 'Midterm'),
        ('Final', 'Final'),
        ('Revision', 'Revision'),
    ]
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='pdf_resources')
    title = models.CharField(max_length=255, blank=True, null=True, help_text="Specific resource name (e.g. 'Lecture 1')")
    category = models.CharField(max_length=50, choices=RESOURCE_TYPES)
    # file = models.FileField(upload_to=get_resource_upload_path) # DEPRECATED
    preview_url = models.URLField(max_length=500, blank=True, null=True, help_text="Google Drive Embed URL")
    download_url = models.URLField(max_length=500, blank=True, null=True, help_text="Google Drive Download URL")
    
    # Drive API Integration Fields
    drive_folder_url = models.URLField(max_length=500, blank=True, null=True, help_text="Source Folder URL (if imported)")
    file_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Drive File ID")
    
    # Solution Linking
    solution_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for the solution file")
    solution_file_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Drive File ID for Solution")

    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject.name} - {self.category} - {self.preview_url or 'No URL'}"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    # profile_picture = models.ImageField(upload_to='profiles/', default='profiles/default.png') # DEPRECATED
    profile_picture_url = models.URLField(max_length=500, default="https://ui-avatars.com/api/?background=random", help_text="Image URL")
    plain_password = models.CharField(max_length=128, blank=True, null=True)
    registered_subjects = models.ManyToManyField(Subject, blank=True, related_name='registered_students')

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def unread_count(self):
        return self.user.notifications.filter(is_read=False).count()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        StudentProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        StudentProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=StudentProfile)
def auto_register_level_subjects(sender, instance, created, **kwargs):
    """
    Automatically adds all subjects from the student's current level 
    to their registered_subjects when the level is first set or changed.
    """
    if instance.level:
        # Get all subjects for the assigned level
        from .models import Subject
        level_subjects = Subject.objects.filter(level=instance.level)
        
        # Add them to registered_subjects
        # ManyToManyField.add() handles duplicates automatically
        instance.registered_subjects.add(*level_subjects)

class StudentNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=100, default="Note")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username} - {self.title}"


class SemesterConfiguration(models.Model):
    current_semester = models.IntegerField(choices=[(1, 'Semester 1'), (2, 'Semester 2')], default=1)

    def save(self, *args, **kwargs):
        # Implement Singleton pattern: always use pk=1
        self.pk = 1
        super(SemesterConfiguration, self).save(*args, **kwargs)

    @classmethod
    def get_current_semester(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj.current_semester

    def __str__(self):
        return f"System Configuration: Semester {self.current_semester}"



import uuid

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_sessions')
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    guest_email = models.EmailField(blank=True, null=True)
    session_token = models.UUIDField(default=uuid.uuid4, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Chat with {self.user.username}"
        return f"Chat with {self.guest_name or 'Guest'}"

    @property
    def unread_for_admin(self):
        return self.messages.filter(sender='student', is_read=False).count()

class ChatMessage(models.Model):
    SENDER_CHOICES = [
        ('student', 'Student/Guest'),
        ('support', 'Support/Admin'),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    # file = models.FileField(upload_to='chat_uploads/', blank=True, null=True) # DEPRECATED
    file_url = models.URLField(max_length=500, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class AIChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_chat_sessions')
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

class AIChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('model', 'AI'),
    ]
    session = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

class UniversityKnowledge(models.Model):
    CATEGORY_CHOICES = [
        ('rules', 'Academic Rules'),
        ('faq', 'FAQ'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    question = models.TextField(blank=True, null=True, help_text="Question for FAQs")
    answer = models.TextField(help_text="The detailed answer or rule content")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"[{self.category}] {self.question if self.question else self.answer[:50]}..."

    class Meta:
        verbose_name_plural = "University Knowledge"
