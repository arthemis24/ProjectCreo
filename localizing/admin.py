# -*- coding: utf-8 -*-
__author__ = 'Roddy Mbogning'

from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

from django.contrib import admin
from localizing.models import *
from import_export import resources
from import_export.admin import ImportExportMixin
from django.db.models import Q

SUPER_USER = 'mbogning'


class FiberListFilter(admin.SimpleListFilter):
    """
    Implements the filtering of ContentUpdate by member on Content Vendor website
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('drawed fiber')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'fiber_status'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('drawed', _('Drawed lines')),
            ('not_drawed', _('Undrawed lines')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == 'drawed':
            return queryset.filter(distance__gt=0)
        if self.value() == 'not_drawed':
            return queryset.filter(distance__lte=0)


def activate_devices(modeladmin, request, queryset):
    for device in queryset:
        if device.status == Device.VALIDATE:
            continue
        else:
            device.status = Device.VALIDATE
            device.save()

activate_devices.short_description = "Activate selected devices"


def activate_fibers(modeladmin, request, queryset):
    for fiber in queryset:
        if fiber.status == Fiber.VALIDATE:
            continue
        else:
            fiber.status = Fiber.VALIDATE
            fiber.save()

activate_fibers.short_description = "Activate selected fibers"


class DeviceResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        model = Device
        fields = ('id', 'category', 'name', 'longitude', 'latitude', 'description', 'status','zone', 'techie',)
        # import_id_fields = ('id',)


class FiberResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        model = Fiber
        fields = ('id','start_point', 'end_point', 'name', 'description', 'status', 'zone', 'techie')
        # import_id_fields = ('id',)


class FiberAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = FiberResource
    list_display = ('name', 'operator', 'city', 'techie', 'distance', 'created_on')
    search_fields = ('name', 'start_point', 'end_point', )
    actions = [activate_fibers, 'delete_model']

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('operator', 'start_point', 'end_point', 'description',
                    'distance', 'city', 'techie', 'created_on', 'last_update')
        return ('start_point', 'end_point', 'description',
                'distance', 'city', 'techie', 'created_on', 'last_update')

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return FiberListFilter, 'created_on', 'operator', 'city', 'techie'
        return FiberListFilter, 'created_on', 'techie'

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return 'city', 'name', 'distance', 'techie', 'created_on', 'last_update'
        return 'operator', 'city', 'name', 'techie', 'distance', 'created_on', 'last_update'

    def get_queryset(self, request):
        """
            Returns a QuerySet of all model instances that can be edited by the
            admin site. This is used by changelist_view.
            """
        member = request.user
        current_profile = UserProfile.objects.get(member=member)
        if not request.user.is_superuser:
            qs = self.model._default_manager.filter(operator=current_profile.operator, city=current_profile.city)
        else:
            qs = self.model._default_manager.all()
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def save_model(self, request, obj, form, change):
        member = request.user
        current_profile = UserProfile.objects.get(member=member)
        obj.operator = current_profile.operator
        obj.city = current_profile.city
        obj.description = obj.description.replace("\n", ' ')
        obj.techie = current_profile
        super(FiberAdmin, self).save_model(request, obj, form, change)

    def get_actions(self, request):
        actions = super(FiberAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        for o in obj.all():
            if o.status == Fiber.VALIDATE and not request.user.is_superuser:
                pass
            else:
                o.delete()

    delete_model.short_description = 'Delete selected fibers'


# class FiberEventDataAdmin(admin.ModelAdmin):
#     list_display = ('fiber', 'longitude','latitude',)


class DeviceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'icon',)


class UserProfileInline(admin.TabularInline):
    model = UserProfile
    extra = 0
    fields = ('operator', 'city')


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('member', 'operator')


class OperatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'fiber_color')


class DeviceAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = DeviceResource
    list_display = ('name', 'operator', 'city', 'techie', 'created_on')
    search_fields = ('name',)
    list_filter = ('category', 'techie', 'zone')
    actions = [activate_devices, 'delete_model']

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('name', 'description', 'category', 'photo', 'operator',
                    'city', 'techie', 'latitude', 'longitude', 'created_on', 'last_update')
        return ('name', 'description', 'category', 'photo', 'city',
                'techie', 'latitude', 'longitude', 'created_on', 'last_update')

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return 'created_on', 'operator', 'city', 'category', 'techie'
        return 'created_on', 'techie'

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return 'name', 'city', 'techie', 'latitude', 'longitude', 'created_on', 'last_update'
        return 'name', 'operator', 'city', 'techie', 'latitude', 'longitude', 'created_on', 'last_update'

    def get_queryset(self, request):
        """
            Returns a QuerySet of all model instances that can be edited by the
            admin site. This is used by changelist_view.
            """
        techie_as_user = request.user
        techie = UserProfile.objects.get(member=techie_as_user)
        if request.user.is_superuser:
            qs = self.model._default_manager.all()
        else:
            qs = self.model._default_manager.filter(techie=techie)
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def save_model(self, request, obj, form, change):
        techie_as_user = request.user
        techie = UserProfile.objects.get(member=techie_as_user)
        device_count = Device.objects.all().count()
        obj.name = obj.category.name + "_" + str(device_count)
        obj.city = techie.city
        super(DeviceAdmin, self).save_model(request, obj, form, change)

    def get_actions(self, request):
        actions = super(DeviceAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        for o in obj.all():
            if o.status == Device.VALIDATE and not request.user.is_superuser:
                pass
            else:
                o.delete()

    delete_model.short_description = 'Delete selected devices'


class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'longitude', 'latitude')


class ZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'city')


class LogEntryAdmin(admin.ModelAdmin):

    date_hierarchy = 'action_time'

    readonly_fields = LogEntry._meta.get_all_field_names()

    list_filter = [
        'user',
        'content_type',
        'action_flag'
    ]

    search_fields = [
        'object_repr',
        'change_message'
    ]


    list_display = [
        'action_time',
        'user',
        'content_type',
        'object_link',
        'action_flag',
        'change_message',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and request.method != 'POST'

    def has_delete_permission(self, request, obj=None):
        return False

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            link = u'<a href="%s">%s</a>' % (
                reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=[obj.object_id]),
                escape(obj.object_repr),
            )
        return link
    object_link.allow_tags = True
    object_link.admin_order_field = 'object_repr'
    object_link.short_description = u'object'

    def queryset(self, request):
        return super(LogEntryAdmin, self).queryset(request) \
            .prefetch_related('content_type')


class CustomUserAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = self.model._default_manager.all().exclude(username=SUPER_USER).exclude(username='default')
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(LogEntry, LogEntryAdmin)


admin.site.register(Fiber, FiberAdmin)
admin.site.register(DeviceCategory, DeviceCategoryAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(Zone, ZoneAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Operator, OperatorAdmin)
# admin.site.register(UserProfile, UserProfileAdmin)
