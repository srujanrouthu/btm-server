# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Hub, Device


class HubAdmin(admin.ModelAdmin):
    list_display = ('id', 'uuid', 'latitude', 'longitude')

    class Meta:
        model = Hub


admin.site.register(Hub, HubAdmin)


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'hub_id', 'name', 'type', 'at_default_idle_start', 'at_default_idle_end')

    class Meta:
        model = Device


admin.site.register(Device, DeviceAdmin)
