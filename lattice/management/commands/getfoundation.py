from django.core.management import call_command
from django.core.management.base import BaseCommand
from optparse import make_option

from django.utils.translation import ugettext as _

from lattice import settings as app_settings
from cStringIO import StringIO

from zipfile import ZipFile
import requests
import os


class Command(BaseCommand):
    help = _("Downloads and unzip the CSS version of Foundation 5.0.2, "
             "extract it into the app static directory and execute the "
             "collectstatic management command.")
    option_list = BaseCommand.option_list + (
        make_option('-d', '--download-url',
                    dest='download-url',
                    default=app_settings.FOUNDATION_URL,
                    help=_("Url to download the Foundation zipball.")),
        make_option('-l', '--link',
                    dest='link',
                    action='store_true',
                    default=False,
                    help=_("Create a symbolic link to each file instead of"
                           "copying."))
    )

    def handle(self, *args, **options):
        response = requests.get(options["download-url"])

        if not response.status_code == 200:
            raise ReferenceError("Given url did not returned status code 200.")

        if not response.headers.get('content-type') == "application/zip":
            raise ValueError("Returned response is not a valid zip file")

        zip_buffer = StringIO()
        zip_buffer.write(response.content)

        zip_archive = ZipFile(zip_buffer)
        zip_archive.extractall(os.path.join(app_settings.APP_ROOT, 'static'))

        call_command('collectstatic', link=options['link'], interactive=False)
