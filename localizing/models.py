from collections import defaultdict

from django.core.urlresolvers import reverse
from django.db import models
from datetime import datetime
import datetime

from django.db.models import Model
from django.forms import ModelForm, Textarea
from django.utils import translation, timezone
# Create your models here.
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from copy import deepcopy
import os
# from ikwen.core.fields import MultiImageField


def to_dict(var):
    try:
        dict_var = deepcopy(var).__dict__
    except AttributeError:
        return var
    for key in dict_var.keys():
        if key[0] == '_' or type(dict_var[key]) is datetime:
            del(dict_var[key])
        elif type(dict_var[key]) is list:
            try:
                dict_var[key] = [item.to_dict() for item in dict_var[key]]
            except AttributeError:
                dict_var[key] = [to_dict(item) for item in dict_var[key]]
        elif isinstance(dict_var[key], Model):
            try:
                dict_var[key] = dict_var[key].to_dict()
            except AttributeError:
                dict_var[key] = to_dict(dict_var[key])
    return dict_var


class City(models.Model):
    name = models.CharField(max_length=50)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Cities'


class Zone(models.Model):
    name = models.CharField(max_length=50)
    city = models.ForeignKey(City)
    geo_fancing_coords = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=50, null=True, blank=True)

    def __unicode__(self):
        return self.name

    def to_dict(self):
        var = to_dict(self)
        return var


class Operator(models.Model):
    BLUE_YDE_PARTNERS = "#417690"
    DARK_RED_DLA_PARTNERS = "#BF0072"
    RED = "#FF0000"
    GREEN = "#00FF00"
    BLUE = "#0000FF"
    BLACK = "#000000"
    YELLOW = "#FFFF00"
    AQUA = "#00FFFF"
    PINK = "#FF00FF"
    DARK_RED = "#850117"
    DARK_BLUE = "#300169"
    DARK_GREEN = "#197F5B"
    DARK = "#5b3f12"
    BROWN = "#280819"
    ORANGE = "#ff6600"
    COLOUR_CHOICES = (
        (BLUE_YDE_PARTNERS, "Blue for YDE partners"),
        (DARK_RED_DLA_PARTNERS, "Daerk red for DLA partners"),
        (RED, "Red"),
        (GREEN, "Green"),
        (BLUE, "Blue"),
        (BLACK, "Black"),
        (YELLOW, "Yellow"),
        (AQUA, "Aqua"),
        (PINK, "Pink"),
        (DARK_RED, "Dark red"),
        (DARK_BLUE, "Dark blue"),
        (DARK_GREEN, "Dark green"),
        (DARK, "Dark"),
        (BROWN, "Brown"),
        (ORANGE, "orange"),
    )
    name = models.CharField(max_length=100)
    fiber_color = models.CharField(max_length=7, choices=COLOUR_CHOICES)

    def __unicode__(self):
        return self.name


class UserProfile(models.Model):
    member = models.OneToOneField(User)
    city = models.ForeignKey(City)
    operator = models.ForeignKey(Operator)

    def __unicode__(self):
        return self.member.username


class Fiber(models.Model):
    PENDING = "Pending"
    VALIDATE = "Validate"

    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (VALIDATE, "Validate"),
    )

    start_point = models.CharField(max_length=240, blank=True)
    end_point = models.CharField(max_length=240, blank=True)
    name = models.CharField(max_length=240, blank=True)
    distance = models.FloatField(default=0.0)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=PENDING, editable=False)
    zone = models.ForeignKey(Zone, null=True, blank=True, editable=False)
    techie = models.ForeignKey(UserProfile, null=True, blank=True)
    operator = models.ForeignKey(Operator, null=True, blank=True)
    city = models.ForeignKey(City, null=True, blank=True)
    created_on = models.DateField(default=timezone.now)
    last_update = models.DateField(default=timezone.now)

    class Meta:
        unique_together = [("start_point", "end_point")]

    def __unicode__(self):
        return self.name

    def get_techie_name(self):
        if self.techie.member.first_name and self.techie.member.last_name:
            return "%s %s" % (self.techie.member.first_name, self.techie.member.last_name)
        elif self.techie.member.first_name and not self.techie.member.last_name:
            return "%s" % self.techie.member.first_name
        elif not self.techie.member.first_name and self.techie.member.last_name:
            return "%s" % self.techie.member.last_name
        elif not self.techie.member.first_name and not self.techie.member.last_name:
            return "%s" % self.techie.member.username

    def get_admin_url(self):
        return reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])

    def to_dict(self):
        # zone = self.zone.to_dict()
        # techie = self.techie.member.get_full_name()
        var = to_dict(self)
        var['admin_url'] = self.get_admin_url()
        # var['techie'] = self.self.techie.member.username
        var['created'] = to_display_date(self.created_on)
        var['display_techie_name'] = self.get_techie_name()
        del (var['zone_id'])
        del (var['created_on'])
        del (var['last_update'])
        return var

    def save(self, *args, **kwargs):
        self.name = '%s-%s' % (self.start_point, self.end_point)
        super(Fiber, self).save(*args, **kwargs)

    def get_description(self):
        return self.description.replace("\n", ' ').replace("\r", '')

    def get_display_date(self):
        return to_display_date(self.created_on)


class FiberEventData(models.Model):
    fiber = models.ForeignKey(Fiber)
    longitude = models.CharField(max_length=240, default="0.0")
    latitude = models.CharField(max_length=240, default="0.0")
    created_on = models.DateField(default=timezone.now)

    def __unicode__(self):
        return self.fiber.name


class DeviceCategory(models.Model):
    name = models.CharField(max_length=240, blank=True)
    icon = models.ImageField(blank=True, upload_to="icons")
    description = models.TextField(blank=True)
    zoom = models.IntegerField(default=20)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Device categories'

    def to_dict(self):
        var = to_dict(self)
        return var


class Device(models.Model):
    PENDING = "Pending"
    VALIDATE = "Validate"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (VALIDATE, "Validate"),
    )
    category = models.ForeignKey(DeviceCategory)
    name = models.CharField(max_length=240, blank=True)
    longitude = models.CharField(max_length=240, default="0.0")
    latitude = models.CharField(max_length=240, default="0.0")
    description = models.TextField(blank=True)
    client_code = models.CharField(max_length=240, blank=True)
    site_code = models.CharField(max_length=240, blank=True)
    client_name = models.CharField(max_length=240, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=PENDING, editable=False)
    zone = models.ForeignKey(Zone, blank=True, null=True, editable=False)
    photo = models.ImageField(upload_to="device_img", null=True, blank=True)
    techie = models.ForeignKey(UserProfile, null=True, blank=True)
    operator = models.ForeignKey(Operator, null=True, blank=True)
    city = models.ForeignKey(City, null=True, blank=True)
    isActive = models.BooleanField(default=True, editable=False)
    created_on = models.DateField(default=timezone.now)
    last_update = models.DateField(default=timezone.now)

    def __unicode__(self):
        return self.name

    def get_techie_name(self):
        if self.techie.member.first_name and self.techie.member.last_name:
            return "%s %s" % (self.techie.member.first_name, self.techie.member.last_name)
        elif self.techie.member.first_name and not self.techie.member.last_name:
            return "%s" % self.techie.member.first_name
        elif not self.techie.member.first_name and self.techie.member.last_name:
            return "%s" % self.techie.member.last_name
        elif not self.techie.member.first_name and not self.techie.member.last_name:
            return "%s" % self.techie.member.username

    def get_admin_url(self):
        return reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name),
                       args=[self.id])

    def to_dict(self):
        var = to_dict(self)
        var['category'] = self.category.to_dict()
        var['image'] = self.photo.url if self.photo else None
        var['display_techie_name'] = self.get_techie_name()
        var['display_date'] = self.get_display_date()
        del (var['created_on'])
        del (var['last_update'])
        del (var['photo'])
        # del (var['techie'])
        return var

    def get_description(self):
        return self.description.replace("\n", ' ').replace("\r", '')

    def get_display_date(self):
        return to_display_date(self.created_on)


class AddDeviceForm(ModelForm):
    class Meta:
        model = Device
        widgets = {
            'description': Textarea(attrs={'cols': 80, 'rows': 50}),
        }
        fields = ['name', 'category', 'longitude', 'latitude']


def to_display_date(a_datetime):
    if translation.get_language().lower().find('en') == 0:
        display_date = '%02d/%02d, %d ' % (
            a_datetime.month, a_datetime.day, a_datetime.year
        )
    else:
        display_date = '%02d/%02d/%d' % (
            a_datetime.day, a_datetime.month, a_datetime.year
        )
    return display_date

