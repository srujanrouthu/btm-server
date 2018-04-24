# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid


from django.db import models
from django.contrib.auth.models import User


class Hub(models.Model):
    user = models.OneToOneField(to=User, related_name='hubs')
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Hubs'


class Device(models.Model):
    hub = models.ForeignKey(to=Hub, related_name='devices')
    name = models.CharField(max_length=64, unique=True)
    type = models.CharField(max_length=64, null=True, blank=True)
    at_default_idle_start = models.TimeField()
    at_default_idle_end = models.TimeField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Devices'


class Override(models.Model):
    device = models.ForeignKey(to=Device, null=False, blank=False, related_name='overrides')
    at_required = models.DateTimeField(null=False, blank=False)

    def __str__(self):
        return '%s - %s' % (self.device.__str__(), self.at_required)

    class Meta:
        verbose_name_plural = 'Overrides'
