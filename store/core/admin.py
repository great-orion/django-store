from django.contrib import admin
from unfold.admin import ModelAdmin
from . import models
from django.utils import timezone


class ProductAdmin(ModelAdmin):
    # Fields to show in the list view
    list_display = (
        'name',
        'category',
        'price_display',
        'discount',
        'count',
        'enabled',
        'user',
        'create_date',
        'deleted',
    )

    list_filter = (
        'enabled',
        'deleted',
        'category',
        'create_date',
        'modified_date',
    )

    search_fields = (
        'name',
        'slug',
        'description',
        'category__name',
        'user__username',
    )

    # Default ordering
    ordering = ('-create_date',)

    # Fields shown when editing a product
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'category', 'user')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'discount', 'count', 'enabled')
        }),
        ('Content', {
            'fields': ('description', 'image')
        }),
        ('System Info', {
            'fields': ('uuid', 'create_date', 'modified_date', 'deleted', 'deleted_date'),
            'classes': ('collapse',),  # Collapsible section
        }),
    )

    # Read-only fields
    readonly_fields = (
        'uuid',
        'create_date',
        'modified_date',
        'deleted_date',
    )

    # Automatically prepopulate slug from name
    prepopulated_fields = {"slug": ("name",)}

    show_facets = admin.ShowFacets.ALWAYS

    # Custom display for price
    def price_display(self, obj):
        return f"{obj.price:,} $"
    price_display.short_description = "Price"
    price_display.admin_order_field = 'price'


class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'product_count', 'deleted', 'deleted_date')
    list_filter = ('parent',)
    search_fields = ('name',)

    # Default readonly fields (always)
    readonly_fields = ('uuid', 'create_date', 'modified_date', 'deleted_date')

    show_facets = admin.ShowFacets.ALWAYS

    def get_readonly_fields(self, request, obj=None):
        # Get default readonly fields
        readonly = list(self.readonly_fields)

        # If this is a popup (e.g., from Product admin), make deleted fields readonly
        if request.GET.get('_popup'):
            readonly.extend(['deleted', 'deleted_date'])

        return readonly

    def get_fieldsets(self, request, obj=None):
        # Customize fieldsets conditionally
        if request.GET.get('_popup'):
            # Simplified fieldset for popup
            return (
                ('Basic Info', {
                    'fields': ('name', 'parent', 'user')
                }),
            )
        else:
            # Full fieldset for normal admin view
            return (
                ('Basic Info', {
                    'fields': ('name','parent', 'user')
                }),
                ('Deletion Info', {
                    'fields': ('deleted', 'deleted_date'),
                    'classes': ('collapse',),
                }),
                ('System Info', {
                    'fields': ('uuid', 'create_date', 'modified_date'),
                    'classes': ('collapse',),
                }),
            )

    def save_model(self, request, obj, form, change):
        # 🔥 Auto-assign user if not set (common in popups)
        if not obj.user_id:
            obj.user = request.user

        # Auto-set deleted_date when deleted is toggled to True
        if obj.deleted and not obj.deleted_date:
            obj.deleted_date = timezone.now()
        elif not obj.deleted:
            obj.deleted_date = None
        super().save_model(request, obj, form, change)

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"



class CommentAdmin(ModelAdmin):
    pass


class PaymentAdmin(ModelAdmin):
    list_display = ['user', 'status', 'total', 'ref']
    list_filter = ['status']
    search_fields = ['invoice__user__username', 'ref']
    fieldsets = (
        ('Payment Info', {
            'fields': ('invoice', 'total', 'status', 'ref')
        }),
        ('Gateway Details', {
            'fields': ('authority', 'description', 'user_ip')
        }),
        ('Error Handling', {
            'fields': ('error_code', 'error_message'),
            'classes': ('collapse',),  # Makes this section collapsible
        }),
    )

    readonly_fields = ('invoice', 'ref', 'total', 'authority', 'user_ip')

    show_facets = admin.ShowFacets.ALWAYS


    def user(self, obj):
        return obj.invoice.user.username if obj.invoice.user else '-'


admin.site.register(models.Product, ProductAdmin)
admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Comment, CommentAdmin)
admin.site.register(models.Payment, PaymentAdmin)
