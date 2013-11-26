from django.db import models
from django.conf import settings

from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager

from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify

import random


class SiteAbstract(models.Model):
    """
    Abstract model for binding the object with a given site, specified in
    django configuration.
    If the `site id` is not given, the save method get the current site id.
    """
    objects = CurrentSiteManager()
    site = models.ForeignKey("sites.Site", editable=False)

    class Meta:
        abstract = True

    def save(self, update_site=False, *args, **kwargs):
        if update_site or not self.id:
            self.site_id = Site.objects.get_current()
        super(SiteAbstract, self).save(*args, **kwargs)

    def is_displayable_for_site(self, site_id=None):
        current = Site.objects.get_current()
        return current == site_id


class SlugAbstract(models.Model):
    """
    Abstact model that implements slug and title.
    """
    title = models.CharField(_("Title"), max_length=500)
    slug = models.CharField(_("URL"), max_length=2000, blank=True, null=True,
                            help_text=_("Leave blank to have the URL auto-"
                            "generated from the title."))

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.__slugify(self.title)
        super(SlugAbstract, self).save(*args, **kwargs)

    def __slugify(self):
        """
        Generates a slug and makes shure it's unique.
        """
        model = self.__class__

        slug = slugify(self.title)

        while True:
            try:
                model.objects.get(slug=slug)
            except model.DoesNotExist:
                # The slug is unique. Let's coninue
                break
            slug = slugify("%s-%s" % self.title, random.randrange(1111, 9999))

        return slug


class AuthorAbstract(models.Model):
    """
    Abstract model for binding the object with a given user (the author).
    """
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               verbose_name=_("Author"),
                               related_name="%(class)ss")

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def is_editable(self, request):
        """
        Restrict in-line editing to the objects's owner and superusers.
        """
        return request.user.is_superuser or request.user.id == self.user_id
