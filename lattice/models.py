from django.db import models
from django.conf import settings

from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.contrib.sites.managers import CurrentSiteManager

from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify, truncatewords_html
from django.utils.html import strip_tags

import settings as app_settings
import random
from PIL import Image


class SiteAbstract(models.Model):
    """
    Abstract model for binding the object with a given site, specified in
    django configuration.
    If the `site id` is not given, the save method get the current site id.
    """
    objects = CurrentSiteManager()
    site = models.ForeignKey(Site, editable=False)

    class Meta:
        abstract = True

    def save(self, update_site=False, *args, **kwargs):
        if update_site or not self.id:
            self.site = Site.objects.get_current()
        super(SiteAbstract, self).save(*args, **kwargs)

    def is_displayable_for_site(self, site_id=None):
        current = Site.objects.get_current()
        return current == site_id


class SlugAbstract(models.Model):
    """
    Abstract model that implements slug and title.
    """
    title = models.CharField(_("Title"), max_length=500)
    slug = models.CharField(_("URL"), max_length=2000, blank=True, null=True,
                            help_text=_("Leave blank to have the URL auto-"
                            "generated from the title."))

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.__slugify()
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
            slug = slugify("%s-%s" % (self.title,
                           random.randrange(1111, 9999)))

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

    def is_editable(self, request):
        """
        Restrict in-line editing to the objects's owner and superusers.
        """
        return request.user.is_superuser or request.user.id == self.user_id


class ThumbnailAbstract(models.Model):
    """
    Abstract model that implements the upload of an image as thumbnail
    """
    thumbnail = models.ImageField(upload_to='img/thumbnails/%Y/%m/%d')

    class Meta:
        abstract = True


def crop_image(sender, instance, created, **kwargs):
    def _crop_image(path, size, crop_type='top'):
        """
        Resize and crop an image to fit the specified size.
        args:
            img_path: path for the image to resize.
            modified_path: path to store the modified image.
            size: `(width, height)` tuple.
            crop_type: can be 'top', 'middle' or 'bottom', depending on this
                value, the image will cropped getting the 'top/left', 'midle'
                or 'bottom/rigth' of the image to fit the size.
        raises:
            Exception: if can not open the file in img_path of there is
                problems in saving the image.
            ValueError: if an invalid `crop_type` is provided.
        """
        # If height is higher we resize vertically, if not we resize
        # horizontally
        img = Image.open(path)
        # Get current and desired ratio for the images
        img_ratio = img.size[0] / float(img.size[1])
        ratio = size[0] / float(size[1])
        # The image is scaled/cropped vertically or horizontally depending on
        # the ratio
        if ratio > img_ratio:
            img = img.resize((size[0], size[0] * img.size[1] / img.size[0]),
                             Image.ANTIALIAS)
            # Crop in the top, middle or bottom
            if crop_type == 'top':
                box = (0, 0, img.size[0], size[1])
            elif crop_type == 'middle':
                box = (0, (img.size[1] - size[1]) / 2, img.size[0],
                       (img.size[1] + size[1]) / 2)
            elif crop_type == 'bottom':
                box = (0, img.size[1] - size[1], img.size[0], img.size[1])
            else:
                raise ValueError('ERROR: invalid value for crop_type')
            img = img.crop(box)
        elif ratio < img_ratio:
            img = img.resize((size[1] * img.size[0] / img.size[1], size[1]),
                             Image.ANTIALIAS)
            # Crop in the top, middle or bottom
            if crop_type == 'top':
                box = (0, 0, size[0], img.size[1])
            elif crop_type == 'middle':
                box = ((img.size[0] - size[0]) / 2, 0, (img.size[0] + size[0])
                       / 2, img.size[1])
            elif crop_type == 'bottom':
                box = (img.size[0] - size[0], 0, img.size[0], img.size[1])
            else:
                raise ValueError('ERROR: invalid value for crop_type')
            img = img.crop(box)
        else:
            img = img.resize((size[0], size[1]), Image.ANTIALIAS)
            # If the scale is the same, we do not need to crop
        img.save(path)

    # Let's check if the sender model extends the ThumbnailAbstract model
    if not issubclass(sender, ThumbnailAbstract):
        return
    _crop_image(instance.thumbnail.path,
                app_settings.UPLOADED_IMG_SIZE,
                'middle')

# We don't specify the user model (because it's an abstract model). So we check
# the name of it in the signal.
post_save.connect(crop_image, dispatch_uid="image_auto_resize")


class ContentAbstract(SlugAbstract):
    """
    Abstract model that implements content (usually rendered with rich text
    input).
    """
    content = models.TextField(_("Content"))

    search_fields = ("content",)

    class Meta:
        abstract = True


class DescriptionAbstract(ContentAbstract):
    """
    Abstract model that implements description, both manually inserted or
    automaticaly created from content.
    """
    description = models.TextField(_("Description"), blank=True)
    gen_description = models.BooleanField(_("Generate description"),
                                          help_text=_(
                                          "If checked, the description will be"
                                          " automatically generated from "
                                          "content. Uncheck if you want to "
                                          "manually set a custom "
                                          "description."), default=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.description and self.gen_description:
            self.description = self.__description_from_content()
        super(DescriptionAbstract, self).save(*args, **kwargs)

    def __description_from_content(self):
        if self.content:
            stripped = strip_tags(self.content)
            return truncatewords_html(stripped, 100)
        # Falls back to the title.
        return str(self.title)
