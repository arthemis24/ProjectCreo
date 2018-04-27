import time
import math
import os
from datetime import datetime

from django.contrib.admin import AdminSite
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.csrf import csrf_protect
# from ajaxuploader.backends.local import LocalUploadBackend
# from ajaxuploader.views.base import AjaxFileUploader
from django.core.files.base import File
from django.template.defaultfilters import slugify
from django.http import HttpResponseRedirect
from django.core import urlresolvers

# Create your views here.
import json
# import requests
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.base import TemplateView
from django.db.models import Q
from django.contrib.auth.models import User, Group
from CreolinkLocalizer import settings
# from conf import settings
from localizing.models import Device, FiberEventData, DeviceCategory, Fiber, Zone, City, Operator, UserProfile

_BOT = 'Bot'


def is_registered_member(user):
    return user.is_authenticated()


class BaseView(TemplateView):

    def get_context_data(self, **kwargs):
        context = super(BaseView, self).get_context_data(**kwargs)
        context['categories'] = DeviceCategory.objects.all()
        return context


@csrf_protect
def creoplot_login(request, *args, **kwargs):
    from django.contrib.auth.views import login
    response = login(request, *args, **kwargs)
    if request.user_agent.is_mobile:
        next_url = reverse('network')
    else:
        next_url = reverse('network')
    if request.user.is_authenticated():
        return HttpResponseRedirect(next_url)
    else:
        return response


FIBER_BLOCK_SIZE = 50
DEVICE_BLOCK_SIZE = 50


class Statistic(BaseView):
    template_name = 'localizing/statistics.html'

    def get_context_data(self, **kwargs):
        context = super(Statistic, self).get_context_data(**kwargs)
        devices_qs = Device.objects
        fibers_qs = Fiber.objects
        device_categories = DeviceCategory.objects.all()
        #  ALL
        distance = 0
        for fiber in fibers_qs.all():
            distance += fiber.distance / 1000
        context['pending_fiber_count'] = fibers_qs.filter(status=Fiber.PENDING).count()
        context['validated_fiber_count'] = fibers_qs.filter(status=Fiber.VALIDATE).count()
        context['total_fiber_count'] = fibers_qs.all().count()
        context['total_devices_count'] = devices_qs.all().count()
        context['pending_total_devices_count'] = devices_qs.filter(status=Device.PENDING).count()
        context['validated_total_devices_count'] = devices_qs.filter(status=Device.VALIDATE).count()
        context['total_fiber_len'] = distance
        # DOUALA
        dla_distance = 0
        dla_devices_qs = devices_qs.filter(city__name='Douala')
        dla_fibers = fibers_qs.filter(city__name='Douala')
        for fiber in dla_fibers:
            dla_distance += fiber.distance / 1000
        context['dla_pending_fiber_count'] = dla_fibers.filter(status=Fiber.PENDING).count()
        context['dla_validated_fiber_count'] = dla_fibers.filter(status=Fiber.VALIDATE).count()
        context['dla_total_fiber_count'] = dla_fibers.count()
        context['dla_total_devices_count'] = dla_devices_qs.count()
        context['dla_pending_total_devices_count'] = dla_devices_qs.filter(status=Device.PENDING).count()
        context['dla_validated_total_devices_count'] = dla_devices_qs.filter(status=Device.VALIDATE).count()
        context['dla_total_fiber_len'] = dla_distance
        # yde
        yde_distance = 0
        yde_devices_qs = devices_qs.filter(city__name='Yaounde')
        yde_fibers = fibers_qs.filter(city__name='Yaounde')
        for fiber in dla_fibers:
            yde_distance += fiber.distance / 1000
        context['yde_pending_fiber_count'] = yde_fibers.filter(status=Fiber.PENDING).count()
        context['yde_validated_fiber_count'] = yde_fibers.filter(status=Fiber.VALIDATE).count()
        context['yde_total_fiber_count'] = yde_fibers.count()
        context['yde_total_devices_count'] = yde_devices_qs.count()
        context['yde_pending_total_devices_count'] = yde_devices_qs.filter(status=Device.PENDING).count()
        context['yde_validated_total_devices_count'] = yde_devices_qs.filter(status=Device.VALIDATE).count()
        context['yde_total_fiber_len'] = yde_distance
        fiber_groups = []
        device_groups = []
        yde_fiber_stat = []
        yde_device_stat = []
        fiber_stat = []
        device_stat = []
        dla_fiber_stat = []
        dla_device_stat = []

        dla_devices_qs = devices_qs.filter(city__name='Douala')
        dla_fibers = fibers_qs.filter(city__name='Douala')
        yde_devices_qs = devices_qs.filter(city__name='Yaounde')
        yde_fibers = fibers_qs.filter(city__name='Yaounde')


        for category in device_categories:
            devices_count = dla_devices_qs.filter(category=category).count()
            device_stats = {'category': category, 'devices_count': devices_count}
            dla_device_stat.append(device_stats)

        context['devices'] = device_groups
        context['fibers'] = fiber_groups

        context['fiber_stats'] = fiber_stat
        context['device_stats'] = device_stat

        context['yde_fiber_stats'] = yde_fiber_stat
        context['yde_device_stats'] = yde_device_stat

        context['dla_fiber_stats'] = dla_fiber_stat
        context['dla_device_stats'] = dla_device_stat

        return context


def update_device_city():
    devices_qs = Device.objects.all()
    city = City.objects
    for device in devices_qs:
        longitude = float(device.longitude)
        if 9 <= longitude <= 10:
            c = city.get(name='Douala')
        else:
            c = city.get(name='Yaounde')
        device.city = c
        device.save()


def update_fiber_city():
    fibers_qs = Fiber.objects.all()
    for fiber in fibers_qs:
        first_event_data = FiberEventData.objects.filter(fiber=fiber)
        if first_event_data.count() <= 0:
            continue
        longitude = float(first_event_data[0].longitude)
        if longitude == "0.0":
            continue
        if 9 <= longitude <= 10:
            c = City.objects.get(name='Douala')
        else:
            c = City.objects.get(name='Yaounde')
        fiber.city = c
        fiber.save()


class Network(BaseView):
    template_name = 'localizing/equipments.html'

    def get_context_data(self, **kwargs):

        context = super(Network, self).get_context_data(**kwargs)
        member = self.request.user
        profile = UserProfile.objects.get(member=member)
        operator = profile.operator
        context['user_profile'] = profile
        if member.is_superuser:
            count_fibers = Fiber.objects.filter(distance__gt=0).count()
        else:
            count_fibers = Fiber.objects.filter(operator=operator, city=profile.city, distance__gt=0).count()
        fiber_blocks = int(math.ceil(float(count_fibers) / FIBER_BLOCK_SIZE))
        context['fiber_blocks'] = fiber_blocks

        member = self.request.user
        profile = UserProfile.objects.get(member=member)
        operator = profile.operator
        all_fiber_count = Fiber.objects.all().count()
        all_device_count = Device.objects.all().count()
        operator_fiber_count = Fiber.objects.filter(operator=operator).count()
        operator_device_count = Device.objects.filter(operator=operator).count()
        if member.is_superuser:
            if all_fiber_count > 0:
                context['last_fiber_id'] = (Fiber.objects.all().order_by('-id')[0]).id
        else:
            if operator_fiber_count > 0:
                context['last_fiber_id'] = (Fiber.objects.filter(operator=operator).order_by('-id')[0]).id

        if member.is_superuser:
            if all_device_count > 0:
                context['last_device_id'] = (Device.objects.all().order_by('-id')[0]).id
        else:
            if operator_device_count > 0:
                context['last_device_id'] = (Device.objects.filter(operator=operator).order_by('-id')[0]).id
        context['device_categories'] = DeviceCategory.objects.all().order_by('name')
        context['cities'] = City.objects.all()
        context['media_root'] = settings.MEDIA_URL
        context['member'] = self.request.user
        if self.request.user.is_superuser:
            device_queryset = Device.objects.all()
        else:
            techie = UserProfile.objects.get(member=member)
            device_queryset = Device.objects.filter(operator=techie.operator, city=techie.city)
        context['devices'] = device_queryset[0:DEVICE_BLOCK_SIZE]
        count_devices = device_queryset.count()
        device_blocks = int(math.ceil(float(count_devices) / DEVICE_BLOCK_SIZE))
        context['device_blocks'] = device_blocks
        if self.request.user.is_superuser:
            context['operators'] = Operator.objects.all()
            context['show_operators'] = True
        else:
            context['operators'] = operator
            context['show_operators'] = False
        return context


def change_date_to_string(date_to_stringify):
    changed_date = '%02d/%02d/%d  %02d:%02d:%02d' % (
        date_to_stringify.year, date_to_stringify.month, date_to_stringify.day, date_to_stringify.hour,
        date_to_stringify.minute, date_to_stringify.second)
    return changed_date


def retrieve_dates_from_interval(string_date):
    date_array = string_date.replace(' - ', '-')
    date_array = string_date.split('-')
    dates = []
    for d in date_array:
        d = d.replace('/', '-')
        dates.append(d.strip())
    return dates


def get_only_equipments(request, *args, **kwargs):
    member = request.user
    profile = UserProfile.objects.get(member=member)
    operator = profile.operator
    if member.is_superuser:
        equipments = Device.objects.filter(isActive=True)
    else:
        equipments = Device.objects.filter(operator=operator, isActive=True, city=profile.city)
    response = [equipment.to_dict() for equipment in equipments]
    return HttpResponse(json.dumps({'equipments': response}), 'content-type: text/json', **kwargs)


def get_only_fibers(request, *args, **kwargs):
    member = request.user
    profile = UserProfile.objects.get(member=member)
    operator = profile.operator
    if member.is_superuser:
        fiber_lines = Fiber.objects.filter(distance__gt=0)
    else:
        fiber_lines = Fiber.objects.filter(operator=operator, city=profile.city,distance__gt=0)
    lines = []
    for line in fiber_lines:
        fiber_events = FiberEventData.objects.filter(line=line)
        response = [fiber_event.to_dict() for fiber_event in fiber_events]
        lines.append(response)
    return HttpResponse(json.dumps({'lines': lines}), 'content-type: text/json', **kwargs)


def get_equipments_and_fibers(request, *args, **kwargs):
    member = request.user
    profile = UserProfile.objects.get(member=member)
    operator = profile.operator
    if member.is_superuser:
        fiber_lines = Fiber.objects.all()
    else:
        fiber_lines = Fiber.objects.filter(operator=operator, city=profile.city)
    lines = []
    for line in fiber_lines:
        fiber_events = FiberEventData.objects.filter(line=line)
        response = [fiber_event.to_dict() for fiber_event in fiber_events]
        lines.append(response)

    if member.is_superuser:
        devices = Device.objects.filter(isActive=True)
    else:
        devices = Device.objects.filter(isActive=True, operator=operator, city=profile.city)
    equipments = [device.to_dict() for device in devices]
    return HttpResponse(json.dumps({'equipments': equipments, 'lines': lines}), 'content-type: text/json', **kwargs)


@login_required
def delete_old_way(request, *args, **kwargs):
    line_id = request.GET.get('line')
    try:
        fiberline = Fiber.objects.get(pk=line_id)
        fiber_event_data = FiberEventData.objects.filter(fiber=fiberline)
        for fiber in fiber_event_data:
            fiber.delete()
    except Fiber.DoesNotExist:
        pass
    return HttpResponse(
        json.dumps({'success': True}),
        content_type='application/json'
    )


@login_required
def save_device(request, *args, **kwargs):
    description = request.GET.get('description')
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')
    category_id = request.GET.get('category')
    site_code = request.GET.get('site_code')
    client_code = request.GET.get('client_code')
    client_name = request.GET.get('client_name')
    user_profile = UserProfile.objects.get(member=request.user)
    techie = user_profile
    operator = user_profile.operator
    description = description.replace('\n', ' ')
    category = DeviceCategory.objects.get(pk=category_id)
    device_count = Device.objects.all().count()
    name = category.name + "_" + str(device_count+15000)
    device = Device(name=name, category=category,  longitude=longitude, latitude=latitude, description=description,
                    techie=techie, operator=operator, city=user_profile.city)
    if site_code:
        device.site_code = site_code
    if client_code:
        device.client_code = client_code
    if client_name:
        device.client_name = client_name

    device.save()
    try:
        device.photo = request.FILES['photo']
    except:
        pass
    device.save()
    return HttpResponse(
        json.dumps({'device': device.to_dict()}),
        content_type='application/json'
    )


@login_required
def save_device_position(request, *args, **kwargs):
    name = request.POST.get('name', '')
    description = request.POST.get('description')
    latitude = request.POST.get('latitude')
    longitude = request.POST.get('longitude')
    category_id = request.POST.get('category')
    user_profile = UserProfile.objects.get(member=request.user)
    techie = user_profile
    operator = user_profile.operator
    description = description.replace('\n', ' ')
    category = DeviceCategory.objects.get(pk=category_id)
    device_position = Device(category=category, name=name, longitude=longitude, latitude=latitude,
                             description=description, techie=techie, operator=operator, status=Device.VALIDATE)
    device_position.save()
    if not name:
        device_count = Device.objects.all().count()
        name = category.name + "_" + str(device_count)
        device_position.name = name
        device_position.save()
    try:
        device_position.photo = request.FILES['photo']
    except:
        pass
    device_position.save()
    return HttpResponseRedirect(reverse('home')+ "?devicePlotted=yes")


@login_required
def save_optical_fiber_position(request, *args, **kwargs):
    line_id = request.GET.get('line')
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')
    try:
        fiberline = Fiber.objects.get(pk=line_id)
    except Fiber.DoesNotExist:
        return HttpResponse(
            json.dumps({'error': "An error occured"}),
            content_type='application/json'
        )

    fiberline.save()
    fiber_event_data = FiberEventData(fiber=fiberline, latitude=latitude, longitude=longitude)
    fiber_event_data.save()
    return HttpResponse(
        json.dumps({'success': True}),
        content_type='application/json'
    )


def construct_line_coords(str_coords):
    coords_list = str_coords.split(';')
    coords_list.pop()
    coordinates = []
    for coord in coords_list:
        coord_dimensions = coord.split(',')
        final_coord = {'latitude': coord_dimensions[0], 'longitude': coord_dimensions[1]}
        coordinates.append(final_coord)
    return coordinates


@login_required
def save_live_optical_fiber_coords(request, *args, **kwargs):
    line_id = request.GET.get('line')
    str_coords = request.GET.get('strCoords')
    line_length = request.GET.get('distance')
    coordinates = construct_line_coords(str_coords)
    try:
        fiber_line = Fiber.objects.get(pk=line_id)
    except Fiber.DoesNotExist:
        return HttpResponse(
            json.dumps({'error': "An error occured"}),
            content_type='application/json'
        )
    else:
        try:
            existing_events = FiberEventData.objects.filter(fiber=fiber_line)
        except FiberEventData.DoesNotExist:
            pass
        else:
            for event in existing_events:
                event.delete()
    drawer = request.user
    drawer_profile = UserProfile.objects.get(member=drawer)
    fiber_line.techie = drawer_profile
    fiber_line.line_length = line_length
    fiber_line.distance = line_length
    fiber_line.status = Fiber.VALIDATE
    fiber_line.save()
    for coordinate in coordinates:
        fiber_event_data = FiberEventData(fiber=fiber_line, latitude=coordinate['latitude'], longitude=coordinate['longitude'])
        fiber_event_data.save()

    lines = []
    fiber_events = FiberEventData.objects.filter(fiber=fiber_line)
    line_coords = []
    for event in fiber_events:
        color = event.fiber.operator.fiber_color
        fiber_line.color = color
        if event.longitude != "0.0" and event.latitude != "0.0":
            line_point = {
                'latitude': event.latitude,
                'longitude': event.longitude,
            }
            line_coords.append(line_point)
    line = {'fiberline': fiber_line.to_dict(), 'line_coords': line_coords}
    lines.append(line)
    return HttpResponse(
        json.dumps({'success': True,  'line': line}),
        content_type='application/json'
    )


def construct_filter_params_list(params_string):
    param_list = params_string.split(',')
    param_list.pop()
    return param_list


@login_required
def filter_network_data(request, *args, **kwargs):
    techie_id = request.GET.get('techieId')
    operators = request.GET.get('operator')
    operator_ids_params = ''

    fiber_status_params = construct_filter_params_list(request.GET.get('fiberStatus'))
    device_category_ids_params = construct_filter_params_list(request.GET.get('deviceCategory'))
    device_status_params = construct_filter_params_list(request.GET.get('deviceStatus'))
    if operators:
        operator_ids_params = construct_filter_params_list(request.GET.get('operator'))

    if techie_id:
        member = User.objects.get(id=techie_id)
        techie = UserProfile.objects.get(member=member)
        equipments = Device.objects.filter(techie=techie).order_by('-id')
        fiber_lines = Fiber.objects.filter(techie=techie).order_by('-id')
    else:
        member = request.user
        techie = UserProfile.objects.get(member=member)
        operator = techie.operator
        if request.user.is_superuser:
            equipments = Device.objects.all().order_by('-id')
            fiber_lines = Fiber.objects.all().order_by('-id')
        else:
            equipments = Device.objects.filter(operator=operator).order_by('-id')
            fiber_lines = Fiber.objects.filter(operator=operator).order_by('-id')

    if len(operator_ids_params) > 0:
        operator_list = []
        for operator_id in operator_ids_params:
            operator = Operator.objects.get(id=operator_id)
            operator_list.append(operator)
        equipments = equipments.filter(operator__in=operator_list)
        fiber_lines = Fiber.objects.filter(operator__in=operator_list).order_by('-id')

    if len(device_category_ids_params) > 0:
        category_list = []
        for category_id in device_category_ids_params:
            category = DeviceCategory.objects.get(id=category_id)
            category_list.append(category)
        equipments = equipments.filter(category__in=category_list)
    # else:
    #     equipments = equipments.none()
    if len(device_status_params) > 0:
        equipments = equipments.filter(status__in=device_status_params)
    else:
        equipments = equipments.none()
    # if city_id:
    #     equipments = equipments.filter(city__id=city_id)
    devices = [equipment.to_dict() for equipment in equipments]

    if len(fiber_status_params) > 0:
        fiber_lines = fiber_lines.filter(status__in=fiber_status_params)
    else:
        fiber_lines = fiber_lines.none()
    # if city_id:
    #     fiber_lines = fiber_lines.filter(city__id=city_id)

    lines = []
    if fiber_lines.count() > 0:
        fiber_lines = fiber_lines

        fiber_list = []
        for fiber in fiber_lines:
            line = {
                'id': fiber.id,
                'color': fiber.operator.fiber_color,
            }
            fiber_list.append(line)
        lines = grab_fiberlines_data(fiber_list)
    return HttpResponse(
        json.dumps({
            'lines': lines,
            'count': len(lines),
            'devices': devices
        }),
        content_type='application/json'
    )


def find_lines(request, *args, **kwargs):
    lines = []
    keyword = request.GET.get('query')
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    fibers = Fiber.objects.filter(name__icontains=keyword, operator=operator, city=techie.city)
    for line in fibers:
        events = FiberEventData.objects.filter(fiber=line)
        if events.count() == 0:
            lines.append(line)

    # lines = Fiber.objects.filter(name__icontains=keyword, status=Fiber.PENDING, operator=operator, city=techie.city)
    suggestions = ['%s %s' % (line.id, line.name) for line in lines]
    response = {'suggestions': suggestions}
    response = json.dumps(response)
    return HttpResponse(response)


def search(request, *args, **kwargs):
    from django.db.models import Q
    keyword = request.GET.get('query')
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    techies = []
    equipment_qs = Device.objects
    if member.is_superuser:
        fiberlines = Fiber.objects.filter(name__icontains=keyword)
        line_count = fiberlines.count()
        equipments = equipment_qs.filter(Q(client_name__icontains=keyword) | Q(site_code__icontains=keyword)|
                                         Q(client_code__icontains=keyword)| Q(name__icontains=keyword))
        equipment_count = equipments.count()
    else:
        fiberlines = Fiber.objects.filter(name__icontains=keyword, operator=operator, city=techie.city)
        line_count = fiberlines.count()
        equipments = equipment_qs.filter(Q(client_name__icontains=keyword) | Q(site_code__icontains=keyword)|
                                           Q(client_code__icontains=keyword)| Q(name__icontains=keyword),
                                           operator=operator, city=techie.city)
        equipment_count = equipments.count()
    techs = User.objects.filter(username__icontains=keyword)
    lines = [line.to_dict() for line in fiberlines[:10]]
    devices = [device.to_dict() for device in equipments[:10]]
    for tech in techs:
        techicien = {
            'id': tech.id,
            'username': tech.username,
        }
        techies.append(techicien)
    response = {
        'lines': lines,
        'line_count': line_count,
        'devices': devices,
        'devices_count': equipment_count,
        'techies': techies
    }
    response = json.dumps(response)
    return HttpResponse(response)


def load_equipments_by_city(request, *args, **kwargs):
    keyword = request.GET.get('query')
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    techies = []
    if member.is_superuser:
        fiberlines = Fiber.objects.filter(name__icontains=keyword)
        line_count = fiberlines.count()
        equipments = Device.objects.filter(name__icontains=keyword)
        equipment_count = equipments.count()
    else:
        fiberlines = Fiber.objects.filter(name__icontains=keyword, operator=operator, city=techie.city)
        line_count = fiberlines.count()
        equipments = Device.objects.filter(name__icontains=keyword, operator=operator, city=techie.city)
        equipment_count = equipments.count()
    techs = User.objects.filter(username__icontains=keyword)
    lines = [line.to_dict() for line in fiberlines[:10]]
    devices = [device.to_dict() for device in equipments[:10]]
    for tech in techs:
        techicien = {
            'id': tech.id,
            'username': tech.username,
        }
        techies.append(techicien)
    response = {
        'lines': lines,
        'line_count': line_count,
        'devices': devices,
        'devices_count': equipment_count,
        'techies': techies
    }
    response = json.dumps(response)
    return HttpResponse(response)


def get_selected_device(request, *args, **kwargs):
    keyword = request.GET.get('deviceId')
    equipments = Device.objects.get(id=keyword)
    devices = equipments.to_dict()
    response = {
        'devices': devices
    }
    response = json.dumps(response)
    return HttpResponse(response)


def change_device_position(request, *args, **kwargs):
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')
    device_id = request.GET.get('deviceId')
    device = Device.objects.get(id=device_id)
    current_user = request.user
    techie = device.techie
    if current_user == techie.member or current_user.is_superuser:
        device.latitude = latitude
        device.longitude = longitude
        device.save()
        device = {
            'id': device.id,
            'lat': device.latitude,
            'lng': device.longitude,
            'icon': device.category.icon.url if device.category.icon.name else '',
            'zoom': device.category.zoom
        }
        return HttpResponse(
            json.dumps({'device': device}),
            content_type='application/json'
        )
    else:
        response = {
            'Error': "You don't have permission to update this device"
        }
    response = json.dumps(response)
    return HttpResponse(response)


def get_selected_fiber(request, *args, **kwargs):
    keyword = request.GET.get('fiberId')
    fiber_line = Fiber.objects.get(id=keyword)
    fiber_events = FiberEventData.objects.filter(fiber=fiber_line)
    lines = []
    line_coords = []
    for event in fiber_events:
        color = event.fiber.operator.fiber_color
        if event.longitude != "0.0" and event.latitude != "0.0":
            line_point = {
                'latitude': event.latitude,
                'longitude': event.longitude,
                'name': event.fiber.name,
                'description': event.fiber.description,
                'color': color,
            }
            line_coords.append(line_point)
        line = {'fiberline': fiber_line, 'line_coords': line_coords}
        lines.append(line)
    return HttpResponse(
        json.dumps({'lines': lines}),
        content_type='application/json'
    )


def get_techie_installation(request, *args, **kwargs):
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator

    techie_id = request.GET.get('techieId')

    techie = UserProfile.objects.get(id=techie_id)
    equipments = Device.objects.filter(techie=techie, operator=operator, city=techie.city)

    fiber_lines = Fiber.objects.filter(techie=techie, operator=operator, city=techie.city)
    devices = [equipment.to_dict() for equipment in equipments]
    lines = []
    if fiber_lines.count() > 0:
        fiber_list = []
        for fiber in fiber_lines:
            line = {
                'id': fiber.id,
                'color': fiber.operator.fiber_color,
            }
            fiber_list.append(line)
        lines = grab_fiberlines_data(fiber_list)

    return HttpResponse(
        json.dumps({
            'lines': lines,
            'devices': devices
        }),
        content_type='application/json'
    )


def get_recent_equipments(request, *args, **kwargs):
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator

    string_date = request.GET.get('stringDate')
    equipments = Device.objects.filter(operator=operator).order_by('-last_update')

    if request.GET.get('techieId'):
        techie_id = request.GET.get('techieId')
        techie = User.objects.get(id=techie_id)
        equipments.filter(techie=techie)
    if string_date:
        dates_list = retrieve_dates_from_interval(string_date)
        string_start_date = dates_list[0]
        string_end_date = dates_list[1]
        start_date = datetime.strptime(string_start_date, '%d-%m-%Y').date()
        end_date = datetime.strptime(string_end_date, '%d-%m-%Y').date()
        if start_date and end_date:
            equipments = equipments.filter(Q(last_update__gte=start_date) & Q(last_update__lt=end_date))
        elif start_date and not end_date:
            now = datetime.now()
            end_date = time.mktime(now.timetuple())
            equipments = equipments.filter(Q(last_update__gte=start_date) & Q(last_update__lt=end_date))
        elif end_date and not start_date:
            end_date_dtime = datetime.strptime(string_end_date, '%d-%m-%Y')
            end_date_dt = datetime(end_date_dtime.year, end_date_dtime.month, end_date_dtime.day, 0)
            start_date = int(time.mktime(end_date_dt.timetuple()))
            equipments = equipments.filter(Q(last_update__gte=start_date) & Q(last_update__lt=end_date))

    devices = [equipment.to_dict() for equipment in equipments]
    fiber_lines = Fiber.objects.filter(operator=operator).order_by('-last_update')

    if request.GET.get('techieId'):
        techie_id = request.GET.get('techieId')
        techie = User.objects.get(id=techie_id)
        fiber_lines.filter(techie=techie)
    lines = []
    if fiber_lines.count() > 0:
        if string_date:
            dates_list = retrieve_dates_from_interval(string_date)
            string_start_date = dates_list[0]
            string_end_date = dates_list[1]
            start_date = datetime.strptime(string_start_date, '%d-%m-%Y').date()
            end_date = datetime.strptime(string_end_date, '%d-%m-%Y').date()
            if start_date and end_date:
                fiber_lines = fiber_lines.filter(Q(last_update__gte=start_date) & Q(last_update__lt=end_date))
            elif start_date and not end_date:
                now = datetime.now()
                end_date = time.mktime(now.timetuple())
                fiber_lines = fiber_lines.filter(Q(last_update__gte=start_date) & Q(last_update__lt=end_date))
            elif end_date and not start_date:
                end_date_dtime = datetime.strptime(string_end_date, '%d-%m-%Y')
                end_date_dt = datetime(end_date_dtime.year, end_date_dtime.month, end_date_dtime.day, 0)
                start_date = int(time.mktime(end_date_dt.timetuple()))
                fiber_lines = fiber_lines.filter(Q(last_update__gte=start_date) & Q(last_update__lt=end_date))
        fiber_list = []
        for fiber in fiber_lines:
            line = {
                'id': fiber.id,
                'color': fiber.operator.fiber_color,
            }
            fiber_list.append(line)
        lines = grab_fiberlines_data(fiber_list)
    return HttpResponse(
        json.dumps({
            'lines': lines,
            'devices': devices
        }),
        content_type='application/json'
    )


def grab_fibers(request, *args, **kwargs):
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    start = int(request.GET.get('start', 0))
    length = 50
    limit = start + length
    fiber_list = []
    if request.user.is_superuser:
        fiber_lines = Fiber.objects.filter(distance__gt=0).order_by('-id')[start:limit]
    else:
        fiber_lines = Fiber.objects.filter(operator=operator, city=techie.city, distance__gt=0).order_by('id')[start:limit]
        # fiber_lines = Fiber.objects.filter(operator=operator).order_by('id')[start:limit]

    for fiber in fiber_lines:
        line = {
            'id': fiber.id,
            'color': fiber.operator.fiber_color,
        }
        fiber_list.append(line)

    lines = grab_fiberlines_data(fiber_list)


    return HttpResponse(
        json.dumps(lines),
        content_type='application/json'
    )


def grab_devices(request, *args, **kwargs):
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    start = int(request.GET.get('start', 0))
    length = 50
    limit = start + length
    devices = []
    if request.user.is_superuser:
        device_queryset = Device.objects.all().order_by('-id')[start:limit]
    else:
        device_queryset = Device.objects.filter(operator=operator, city=techie.city).order_by('id')[start:limit]
        # device_queryset = Device.objects.filter(operator=operator).order_by('id')[start:limit]
    for device in device_queryset:
        category = device.category
        equipment = {
            'id': device.id,
            'lat': float(device.latitude),
            'lng': float(device.longitude),
            'icon': category.icon.url if category.icon.name else '',
            'zoom': category.zoom
        }
        devices.append(equipment)

    return HttpResponse(
        json.dumps(devices),
        content_type='application/json'
    )


def grab_device_info(request, *args, **kwargs):
    device_id = request.GET.get('deviceId')
    device = Device.objects.get(pk=device_id)
    photo = device.photo.url if device.photo.name else getattr(settings, 'STATIC_URL') + 'img/no_photo.png'
    equipment = {
        'id': device.id,
        'client_code': device.client_code,
        'client_name': device.client_name,
        'site_code': device.site_code,
        'name': device.name,
        'photo': photo,
        'created_on': device.get_display_date(),
        'techie': device.get_techie_name(),
        'description': device.description,
        'admin_url': device.get_admin_url(),
        'category': device.category.name
    }
    return HttpResponse(
        json.dumps({"device": equipment}),
        content_type='application/json'
    )


def grab_fiber_info(request, *args, **kwargs):
    fiber_id = request.GET.get('fiberId')
    fiber = Fiber.objects.get(pk=fiber_id)
    fiber = {
        'id': fiber.id,
        'name': fiber.name,
        'created_on': fiber.get_display_date(),
        'techie': fiber.get_techie_name(),
        'description': fiber.get_description(),
        'admin_url': fiber.get_admin_url(),
        'distance': fiber.distance
    }
    return HttpResponse(
        json.dumps({"fiber": fiber}),
        content_type='application/json'
    )


def grab_fiberlines_data(fiber_lines):
    lines = []
    for fiber_line in fiber_lines:
        current_fiber = Fiber.objects.get(pk=fiber_line['id'])
        fiber_events = FiberEventData.objects.filter(fiber=current_fiber)
        line_coords = []
        for event in fiber_events:
            if event.longitude != "0.0" and event.latitude != "0.0":
                line_point = {
                    'latitude': event.latitude,
                    'longitude': event.longitude,
                }
                line_coords.append(line_point)
        line = {'fiberline': fiber_line, 'line_coords': line_coords}
        lines.append(line)
    return lines


def update_fibers_distance(request, *args, **kwargs):
    fiber_id = request.GET.get('fiberId')
    distance = request.GET.get('distance')
    fiber = Fiber.objects.get(pk=fiber_id)
    fiber.distance = distance
    fiber.save()
    return HttpResponse(
        json.dumps({"success": True}),
        content_type='application/json'
    )


def check_new_fiber(request, *args, **kwargs):
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    last_fiber_id = request.GET.get('lastFiberId')
    start = int(last_fiber_id)
    if not member.is_superuser:
        fiber_lines = Fiber.objects.filter(id__gt=start, operator=operator, city=techie.city).order_by('-id')
    else:
        fiber_lines = Fiber.objects.filter(id__gt=start).order_by('-id')

    fiber_list = []
    for fiber in fiber_lines:
        line = {
            'id': fiber.id,
            'color': fiber.operator.fiber_color,
        }
        fiber_list.append(line)
    lines = grab_fiberlines_data(fiber_list)
    return HttpResponse(
        json.dumps(lines),
        content_type='application/json'
    )


def get_specific_fiber_data(request, *args, **kwargs):
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    last_fiber_id = request.GET.get('lastFiberId')
    fiber_id = request.GET.get('fiberId')
    if not member.is_superuser:
        fiber_line = Fiber.objects.get(id=fiber_id, operator=operator)
    else:
        fiber_line = Fiber.objects.get(id=fiber_id)
    lines = []

    fiber_events = FiberEventData.objects.filter(fiber=fiber_line)
    line_coords = []
    for event in fiber_events:
        color = event.fiber.operator.fiber_color
        fiber_line.color = color
        if event.longitude != "0.0" and event.latitude != "0.0":
            line_point = {
                'latitude': event.latitude,
                'longitude': event.longitude,
            }
            line_coords.append(line_point)
    line = {'fiberline': fiber_line.to_dict(), 'line_coords': line_coords}
    lines.append(line)

    return HttpResponse(
        json.dumps(lines),
        content_type='application/json'
    )


def get_specific_device_data(request, *args, **kwargs):
    device_id = request.GET.get('deviceId')
    device_qs = Device.objects.get(id=device_id)
    devices = []
    category = device_qs.category
    device = {
        'id': device_qs.id,
        'desc': device_qs.description,
        'lat': float(device_qs.latitude),
        'lng': float(device_qs.longitude),
        'icon': category.icon.url if category.icon.name else '',
        'zoom': category.zoom
    }
    devices.append(device)

    return HttpResponse(
        json.dumps(devices),
        content_type='application/json'
    )


def check_new_device(request, *args, **kwargs):
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    last_device_id = request.GET.get('lastDeviceId')
    if len(last_device_id) > 0:
        start = int(last_device_id)
        devices = []
        if request.user.is_superuser:
            device_queryset = Device.objects.filter(id__gt=start).order_by('-id')
        else:
            device_queryset = Device.objects.filter(techie=techie, operator=operator, id__gt=start).order_by('-id')
        for device in device_queryset:
            category = device.category
            device = {
                'id': device.id,
                'lat': float(device.latitude),
                'lng': float(device.longitude),
                'icon': category.icon.url if category.icon.name else '',
                'zoom': category.zoom
            }
            devices.append(device)

        return HttpResponse(
            json.dumps(devices),
            content_type='application/json'
        )
    return HttpResponse(
        json.dumps({'devices': ''}),
        content_type='application/json'
    )


def check_data_integrity(request, *args, **kwargs):
    online_fiber_ids = []
    online_device_ids = []
    member = request.user
    techie = UserProfile.objects.get(member=member)
    operator = techie.operator
    if member.is_superuser:
        online_fibers = Fiber.objects.all()
        online_devices = Device.objects.all()
    else:
        online_fibers = Fiber.objects.filter(operator=operator, city=techie.city)
        online_devices = Device.objects.filter(operator=operator, city=techie.city)
    if online_devices.count() > 0:
        last_device_id = online_devices.order_by('-id')[0]
        device_table_range = list(range(1,(last_device_id.id + 1)))
        for device in online_devices:
            online_device_ids.append(device.id)
        deleted_devices = [x for x in device_table_range if x not in online_device_ids]
    else:
        deleted_devices = []
    if online_fibers.count() > 0:
        last_fiber_id = online_fibers.order_by('-id')[0]
        fiber_table_range = list(range(1,(last_fiber_id.id + 1)))
        for fiber in online_fibers:
            online_fiber_ids.append(fiber.id)
        deleted_fibers = [x for x in fiber_table_range if x not in online_fiber_ids]
    else:
        deleted_fibers = []

    return HttpResponse(
        json.dumps({
            'deleted_devices': deleted_devices,
            'deleted_fibers': deleted_fibers
        }),
        content_type='application/json'
    )


def check_line_update(request, *args, **kwargs):
    fiberIds = request.GET.get('fiberIds')
    if len(fiberIds) > 0:
        fiber_Id_list = fiberIds.split(',')
        fiberlines = []

        for id in fiber_Id_list:
            fiber = Fiber.objects.get(id=id)
            fiberlines.append(fiber)
        lines = []
        for fiber_line in fiberlines:
            fiber_events = FiberEventData.objects.filter(fiber=fiber_line)
            line_coords = []
            for event in fiber_events:
                color = event.fiber.operator.fiber_color
                fiber_line.color = color
                if event.longitude != "0.0" and event.latitude != "0.0":
                    line_point = {
                        'latitude': event.latitude,
                        'longitude': event.longitude,
                    }
                    line_coords.append(line_point)
            if len(line_coords) > 0:
                line = {'fiberline': fiber_line.to_dict(), 'line_coords': line_coords}
                lines.append(line)
        return HttpResponse(
            json.dumps(lines),
            content_type='application/json'
        )

    return HttpResponse(
        json.dumps( {'lines': ''}),
        content_type='application/json'
    )


def get_updated_fibers(request, *args, **kwargs):
    last_log_updated_id = request.GET.get('last_updated_log_id')
    fiber_content_type = ContentType.objects.get(model='fiber')
    if last_log_updated_id:
        updated_fiber_logs = LogEntry.objects.filter(content_type=fiber_content_type,
                                                     id__gt=last_log_updated_id, action_flag=2).order_by('-id')
    else:
        updated_fiber_logs = LogEntry.objects.filter(content_type=fiber_content_type, action_flag=2).order_by('-id')

    if updated_fiber_logs.count() > 0:
        last_log_updated_id = updated_fiber_logs[0].id

    updated_fibers_list = []
    updated_fibers_pk_list = set()
    for fiber_log in updated_fiber_logs:
        updated_fibers_pk_list.add(fiber_log.object_id)

    for pk in updated_fibers_pk_list:
        try:
            fiber = Fiber.objects.get(pk=pk)
        except Fiber.DoesNotExist:
            pass
        else:
            updated_fibers_list.append(fiber)
    lines = []
    for fiber_line in updated_fibers_list:
        fiber_events = FiberEventData.objects.filter(fiber=fiber_line)
        line_coords = []
        for event in fiber_events:
            color = event.fiber.operator.fiber_color
            fiber_line.color = color
            if event.longitude != "0.0" and event.latitude != "0.0":
                line_point = {
                    'latitude': event.latitude,
                    'longitude': event.longitude,
                }
                line_coords.append(line_point)
        if len(line_coords) > 0:
            line = {'fiberline': fiber_line.to_dict(), 'line_coords': line_coords}
            lines.append(line)
    return HttpResponse(
        json.dumps({
            'lines': lines,
            'last_log_updated_id': last_log_updated_id
        }),content_type='application/json'
    )


def create_user_profile(request, *args, **kwargs):
    # app_users = User.objects.all()
    # for u in app_users:
    #     try:
    #         UserProfile.objects.get(member=u)
    #     except UserProfile.DoesNotExist:
    #         operator = Operator.objects.get(pk=1)
    #         city = City.objects.get(pk=2)
    #         profile = UserProfile(member=u, operator=operator, city=city)
    #         profile.save()

    return HttpResponse(
        json.dumps({
            'Success': 'done'
        }), content_type='application/json'
    )


def migrate_equipments(request, *args, **kwargs):
    categories = DeviceCategory.objects.all()
    devices = Device.objects.all()
    fibers = Fiber.objects.all()
    fiber_events = FiberEventData.objects.all()
    operators = Operator.objects.all()
    groups = Group.objects.all()
    users = User.objects.all()
    zones = Zone.objects.all()
    cities = City.objects.all()
    profiles = UserProfile.objects.all()
    # for user in users:
    #     password = user.password
    #     last_login = user.last_login
    #     is_superuser = user.is_superuser
    #     username = user.username
    #     first_name = user.first_name
    #     last_name = user.last_name
    #     is_staff = user.is_staff
    #     is_active = user.is_active
    #     date_joined = user.date_joined
    #     c = User(password=password,last_login=last_login,is_superuser=is_superuser,username=username,first_name=first_name,last_name=last_name,is_staff=is_staff,is_active=is_active,date_joined=date_joined)
    #     c.save(using='maps')
    #
    # for op in operators:
    #     name = op.name
    #     color = op.fiber_color
    #     o = Operator(name=name, fiber_color=color)
    #     o.save(using='maps')
    #
    # for cit in cities:
    #     name = cit.name
    #     latitude = cit.latitude
    #     longitude = cit.longitude
    #     ctiy = City(name=name, latitude=latitude,longitude=longitude)
    #     ctiy.save(using='maps')
    #
    # for profile in profiles:
    #     city = profile.city
    #     mongo_city = City.objects.using('maps').get(name=city.name)
    #     member = profile.member
    #     mongo_member = User.objects.using('maps').get(username=member.username)
    #     operator = profile.operator
    #     mongo_operator = Operator.objects.using('maps').get(name=operator.name)
    #     prof = UserProfile(city=mongo_city, member=mongo_member,operator=mongo_operator)
    #     prof.save(using='maps')

    # for group in groups:
    #     name = group.name
    #     c = Group(name=name)
    #     c.save(using='maps')
    # for cat in categories:
    #     name = cat.name
    #     icon = cat.icon
    #     description = cat.description
    #     c = DeviceCategory(name=name, icon=icon,description=description)
    #     c.save(using='maps')
    #
    # for op in zones:
    #     name = op.name
    #     city = op.city
    #     mongo_city = City.objects.using('maps').get(name=city.name)
    #     o = Zone(name=name, city=mongo_city)
    #     o.save(using='maps')
    #
    # users = User.objects.using('maps').all()
    # for u in users:
    #     try:
    #         UserProfile.objects.using('maps').get(member=u)
    #     except UserProfile.DoesNotExist:
    #         operator = Operator.objects.using('maps').all()[0]
    #         city = City.objects.using('maps').all()[1]
    #         up = UserProfile(member=u,operator=operator, city=city)
    #         up.save(using='maps')
    #     else:
    #         pass
    # operator = Operator.objects.using('maps').get(pk=1)
    # city = City.objects.using('maps').get(pk=1)
    # for fiber in fibers:
    #     description = fiber.description
    #     distance = fiber.distance
    #     name = fiber.name
    #     start_point = fiber.start_point
    #     end_point = fiber.end_point
    #     created_on = fiber.created_on
    #     last_update = fiber.last_update
    #     status = fiber.status
    #     operator = operator
    #     city = city
    #     try:
    #         Fiber.objects.using('maps').get(name=name)
    #     except Fiber.DoesNotExist:
    #         fib = Fiber(description=description, status=status, distance=distance, name=name, start_point=start_point,
    #                     end_point=end_point, created_on=created_on, last_update=last_update)
    #         fib.save(using='maps')
    #         if fiber.techie:
    #             techie = fiber.techie
    #             profil = User.objects.using('maps').get(username=techie.member.username)
    #             mongo_techie = UserProfile.objects.using('maps').get(member=profil)
    #             fib.techie=mongo_techie
    #             fib.save(using='maps')
    #         if city:
    #             mongo_city = City.objects.using('maps').get(name=city.name)
    #             fib.city = mongo_city
    #             fib.save(using='maps')
    #         if operator:
    #             mongo_operator = Operator.objects.using('maps').get(name=operator.name)
    #             fib.operator = mongo_operator
    #             fib.save(using='maps')
    #
    # for device in devices:
    #     name = device.name
    #     longitude = device.longitude
    #     latitude = device.latitude
    #     description = device.description
    #     status = device.status
    #     photo = device.photo
    #     is_active = device.isActive
    #     created_on = device.created_on
    #     last_update = device.last_update
    #     category = device.category
    #     operator = device.operator
    #     city = device.city
    #     techie = device.techie
    #     mongo_cat = DeviceCategory.objects.using('maps').get(name=category.name)
    #     dev = Device(name=name,longitude=longitude, latitude=latitude, description=description, status=status,
    #                              photo=photo, isActive=is_active, created_on=created_on, last_update=last_update, category=mongo_cat)
    #     dev.save(using='maps')
    #     if techie:
    #         profil = User.objects.using('maps').get(username=techie.member.username)
    #         mongo_techie = UserProfile.objects.using('maps').get(member=profil)
    #         dev.techie=mongo_techie
    #         dev.save(using='maps')
    #     if city:
    #         mongo_city = City.objects.using('maps').get(name=city.name)
    #         dev.city = mongo_city
    #         dev.save(using='maps')
    #     if operator:
    #         mongo_operator = Operator.objects.using('maps').get(name=operator.name)
    #         dev.operator = mongo_operator
    #         dev.save(using='maps')

    for event in fiber_events:
        latitude = event.latitude
        longitude = event.longitude
        created_on = event.created_on
        fiber = event.fiber
        try:
            mongo_fiber = Fiber.objects.using('maps').get(name=fiber.name)
        except Fiber.MultipleObjectsReturned:
            fs = Fiber.objects.using('maps').filter(name=fiber.name)
            for f in fs:
                techie = f.techie
                if techie.member.username == 'default':
                    f.delete(using='maps')
        else:
            mongo_fiber = Fiber.objects.using('maps').get(name=fiber.name)
        ev = FiberEventData(latitude=latitude, longitude=longitude, created_on=created_on, fiber=mongo_fiber)
        ev.save(using='maps')


    return HttpResponse(
        json.dumps({
            'Success': True,
        }), content_type='application/json'
    )


def update_equipments_city(request, *args, **kwargs):
    devices = Device.objects.all()
    fibers = Fiber.objects.all()
    for device in devices:
        if device.techie.city:
            device.city = device.techie.city
        else:
            city = City.objects.get(name='Yaounde')
            device.city = city
        device.save()

    for fiber in fibers:
        if fiber.techie and fiber.techie.city:
            fiber.city = fiber.techie.city
        else:
            city = City.objects.get(name='Yaounde')
            fiber.city = city
        fiber.save()

    return HttpResponse(
        json.dumps({
            'Success': True,
        }), content_type='application/json'
    )


def update_equips(request, *args, **kwargs):
    devices = Device.objects.all()
    fibers = Fiber.objects.all()
    for device in devices:
        techie = device.techie
        device.profile = UserProfile.objects.get(member=techie)
        device.save()

    for fiber in fibers:
        techie = fiber.techie
        fiber.profile = UserProfile.objects.get(member=techie)
        fiber.save()

    return HttpResponse(
        json.dumps({
            'Success': True,
        }), content_type='application/json'
    )


def update_equi(request, *args, **kwargs):
    devices = Device.objects.all()
    operator = Operator.objects.all()[0]
    for device in devices:
        device.operator = operator
        device.save()
    return HttpResponse(
        json.dumps({
            'Success': True,
        }), content_type='application/json'
    )


def update_device_city(request, *args, **kwargs):
    devices_qs = Device.objects.all()
    city = City.objects
    for device in devices_qs:
        longitude = float(device.longitude)
        latitude = float(device.latitude)
        if 9.00 < longitude < 10.0 and 3.0 < latitude <= 5.0 :
            c = city.get(name='Douala')
            device.city = c
            device.save()
    return HttpResponse(
        json.dumps({
            'Success': True,
        }), content_type='application/json'
    )


def update_fiber_city(request, *args, **kwargs):
    fibers_qs = Fiber.objects.all()
    for fiber in fibers_qs:
        first_event_data = FiberEventData.objects.filter(fiber=fiber)
        if first_event_data.count() <= 0:
            continue
        longitude = float(first_event_data[0].longitude)
        latitude = float(first_event_data[0].latitude)
        if longitude == "0.0":
            continue
        if 9 <= longitude < 10 and 3 <= latitude <= 5 :
            c = City.objects.get(name='Douala')
            fiber.city = c
            fiber.save()
        elif 11 <= longitude < 12 and 3 <= latitude <= 5 :
            c = City.objects.get(name='Yaounde')
            fiber.city = c
            fiber.save()
    return HttpResponse(
        json.dumps({
            'Success': True,
        }), content_type='application/json'
    )


