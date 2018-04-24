# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Node, Price


class NodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'node', 'latitude', 'longitude')

    class Meta:
        model = Node


admin.site.register(Node, NodeAdmin)


class PriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'node_id', 'start', 'end', 'price', 'prediction')

    class Meta:
        model = Price


admin.site.register(Price, PriceAdmin)

