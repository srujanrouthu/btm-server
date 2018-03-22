# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from django.db import models


class Price(models.Model):
    start = models.DateTimeField(null=False, blank=False)
    end = models.DateTimeField(null=False, blank=False)
    node = models.CharField(null=False, blank=False, max_length=32)
    price = models.FloatField(null=False, blank=False)

    def __unicode__(self):
        return '%s - %s - %s' % (self.start, self.node, self.price)

    class Meta:
        verbose_name_plural = 'Prices'
