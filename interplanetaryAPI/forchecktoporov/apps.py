import sys

from django.apps import AppConfig

from .data_ingestion import ingest_data


class ForchecktoporovConfig(AppConfig):
    name = 'forchecktoporov'

    def ready(self):
        '''
        Added to ingest new data files at the instantiation of the app.
        '''
        # skip ingesting data if the database is being migrated
        if 'migrate' not in ''.join(sys.argv) and 'makemigrations' not in ''.join(sys.argv):
            ingest_data()
