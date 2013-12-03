from django.conf import settings
import os

UPLOADED_IMG_SIZE = getattr(settings, 'UPLOADED_IMG_SIZE', (800, 800))

FOUNDATION_URL = getattr(settings, 'FOUNDATION_URL',
                         "http://foundation.zurb.com/cdn/releases/"
                         "foundation-5.0.2.zip")

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
