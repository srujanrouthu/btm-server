# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid


from django.db import models
from django.contrib.auth.models import User


class Hub(models.Model):
    user = models.ForeignKey(to=User, related_name='hubs')
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    def __unicode__(self):
        return self.uuid

    class Meta:
        verbose_name_plural = 'Hubs'


class Device(models.Model):
    hub = models.ForeignKey(to=Hub, related_name='devices')
    name = models.CharField(max_length=64, unique=True)
    type = models.CharField(max_length=64, null=True, blank=True)
    at_default_idle_start = models.TimeField()
    at_default_idle_end = models.TimeField()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Devices'
