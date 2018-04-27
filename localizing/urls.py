from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import user_passes_test
from django.contrib import admin

from localizing.views import  save_optical_fiber_position, save_device_position, \
    delete_old_way, save_live_optical_fiber_coords, BaseView, filter_network_data, \
    find_lines, is_registered_member, search, get_techie_installation, get_selected_fiber, get_selected_device, \
    get_recent_equipments, Network, change_device_position, grab_fibers, grab_devices, save_device,grab_device_info, \
    update_fibers_distance, check_new_fiber, check_new_device, check_data_integrity,check_line_update, Statistic,\
    get_specific_fiber_data, get_specific_device_data, get_updated_fibers, create_user_profile, migrate_equipments

_extra_context = BaseView().get_context_data()

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^equipments$', user_passes_test(is_registered_member)(Network.as_view()), name='network'),

    url(r'^findFiberlines', find_lines, name='find_lines'),
    url(r'^statistics$', user_passes_test(is_registered_member)(Statistic.as_view()), name='statistic'),
    url(r'^save_device$', save_device, name='save_device'),
    url(r'^save_device_position$', save_device_position, name='save_device_position'),
    url(r'^save_live_optical_fiber_coords$', save_live_optical_fiber_coords, name='save_live_optical_fiber_coords'),
    url(r'^filter_network_data$', filter_network_data, name='filter_network_data'),
    url(r'^delete_old_way$', delete_old_way, name='delete_old_way'),
    url(r'^save_fiber_way$', save_optical_fiber_position, name='save_fiber_way'),
    url(r'^full_search$', search, name='search'),
    url(r'^get_selected_device$', get_selected_device, name='get_selected_device'),
    url(r'^get_selected_fiber$', get_selected_fiber, name='get_selected_fiber'),
    url(r'^change_device_position$', change_device_position, name='change_device_position'),
    url(r'^get_techie_installation$', get_techie_installation, name='get_techie_installation'),
    url(r'^get_recent_equipments$', get_recent_equipments, name='get_recent_equipments'),
    url(r'^grab_fibers$', grab_fibers, name='grab_fibers'),
    url(r'^grab_devices$', grab_devices, name='grab_devices'),
    url(r'^grab_device_info$', grab_device_info, name='grab_device_info'),
    url(r'^update_fibers_distance$', update_fibers_distance, name='update_fibers_distance'),
    url(r'^check_new_fiber$', check_new_fiber, name='check_new_fiber'),
    url(r'^check_new_device$', check_new_device, name='check_new_device'),
    url(r'^check_device_data_integrity$', check_data_integrity, name='check_data_integrity'),
    url(r'^check_line_update$', check_line_update, name='check_line_update'),
    url(r'^get_specific_fiber_data$', get_specific_fiber_data, name='get_specific_fiber_data'),
    url(r'^get_specific_device_data$', get_specific_device_data, name='get_specific_device_data'),
    url(r'^get_updated_fibers$', get_updated_fibers, name='get_updated_fibers'),
    url(r'^create_user_profile$', create_user_profile, name='create_user_profile'),
)
