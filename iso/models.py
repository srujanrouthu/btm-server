# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from django.db import models


class Node(models.Model):
    node = models.CharField(null=False, blank=False, max_length=32)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __unicode__(self):
        return self.node

    class Meta:
        verbose_name_plural = 'Nodes'


class Price(models.Model):
    start = models.DateTimeField(null=False, blank=False)
    end = models.DateTimeField(null=False, blank=False)
    node = models.ForeignKey(to=Node, null=False, blank=False, related_name='prices')
    price = models.FloatField(null=True, blank=True)
    prediction = models.FloatField(null=True, blank=True)

    def __unicode__(self):
        return '%s - %s - %s' % (self.start, self.node.__unicode__(), self.price)

    class Meta:
        verbose_name_plural = 'Prices'
        unique_together = ('start', 'node')
