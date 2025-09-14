from django.contrib import admin
from unfold.admin import ModelAdmin
from . import models

class UserAdmin(ModelAdmin):
    # Define fieldsets to include your custom fields
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',),}),
    )

    # 👇 Add custom method to combine first_name and last_name
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "—"

    full_name.short_description = "Full Name"  # Column header in admin

    # Fields to display in the list view
    list_display = ('username', 'email', 'phone', 'full_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    ordering = ('username',)

    readonly_fields = ('date_joined', 'last_login')

    show_facets = admin.ShowFacets.ALWAYS

    def get_readonly_fields(self, request, obj=None):
        # Start with default readonly fields
        readonly = list(super().get_readonly_fields(request, obj) or [])

        # If editing an existing user → make username & password read-only
        if obj:  # obj exists → editing
            readonly.extend(['username', 'password'])

        return readonly


admin.site.register(models.User, UserAdmin)


