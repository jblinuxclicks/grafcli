"""Local resources.

TODO: simplify and refactor private methods.

"""
import os

from grafcli.exceptions import InvalidPath, InvalidDocument, DocumentNotFound
from grafcli.config import config
from grafcli.documents import Dashboard, Row, Panel
from grafcli.storage import system

BACKUPS = 'backups'
TEMPLATES = 'templates'
DASHBOARDS = 'dashboards'
ROWS = 'rows'
PANELS = 'panels'

LOCAL_RESOURCES = (BACKUPS, TEMPLATES)

DATA_DIR = os.path.expanduser(config['resources'].get('data-dir', ''))
BACKUPS_DIR = os.path.join(DATA_DIR, BACKUPS)
TEMPLATES_DIR = os.path.join(DATA_DIR, TEMPLATES)
DASHBOARDS_DIR = os.path.join(TEMPLATES_DIR, DASHBOARDS)
ROWS_DIR = os.path.join(TEMPLATES_DIR, ROWS)
PANELS_DIR = os.path.join(TEMPLATES_DIR, PANELS)

DIR_DOCUMENTS = {
    DASHBOARDS: Dashboard,
    ROWS: Row,
    PANELS: Panel,
}


class LocalResources(object):

    def __init__(self):
        for path in (DATA_DIR, BACKUPS_DIR, TEMPLATES_DIR, DASHBOARDS_DIR, ROWS_DIR, PANELS_DIR):
            system.makepath(path)

    def list(self, category, *parts):
        if category not in LOCAL_RESOURCES:
            raise InvalidPath("Invalid local directory: {}".format(category))

        if not parts:
            return system.list_files(DATA_DIR, category)

        if category == BACKUPS:
            return self._list_dashboards(BACKUPS_DIR, *parts)
        elif category == TEMPLATES:
            return self._list_templates(*parts)

    def _list_templates(self, directory, *parts):
        if not parts:
            return system.list_files(TEMPLATES_DIR, directory)

        if directory == DASHBOARDS:
            return self._list_dashboards(DASHBOARDS_DIR, *parts)
        elif directory == ROWS:
            return self._list_rows(*parts)
        elif directory == PANELS:
            return self._list_panels(*parts)

    def _list_dashboards(self, directory, dashboard_name=None, row_name=None, panel_name=None):
        source = system.read_file(directory, dashboard_name)
        dashboard = Dashboard(source, dashboard_name)

        if not row_name:
            return [row.name for row in dashboard.rows]

        panels = [panel.name for panel in dashboard.row(row_name).panels]

        if panel_name:
            if panel_name in panels:
                raise InvalidPath("Panel contains no sub-nodes")
            else:
                raise InvalidPath("There is no such panel: {}".format(panel_name))
        else:
            return panels

    def _list_rows(self, row_name=None):
        source = system.read_file(ROWS_DIR, row_name)
        row = Row(source)

        return [panel.name for panel in row.panels]

    def _list_panels(self, *parts):
        raise InvalidPath("Panels contain no sub-nodes")

    def get(self, category, *parts):
        if category not in LOCAL_RESOURCES:
            raise InvalidPath("Invalid local directory: {}".format(category))

        if not parts:
            raise InvalidPath("Can not get directory")

        if category == BACKUPS:
            return self._get_dashboards(BACKUPS_DIR, parts)
        else:
            return self._get_templates(*parts)

    def _get_templates(self, directory, *parts):
        if directory == DASHBOARDS:
            return self._get_dashboards(DASHBOARDS_DIR, *parts)
        elif directory == ROWS:
            return self._get_rows(*parts)
        elif directory == PANELS:
            return self._get_panels(*parts)

    def _get_dashboards(self, directory, dashboard_name=None, row_name=None, panel_name=None):
        source = system.read_file(directory, dashboard_name)
        dashboard = Dashboard(source, dashboard_name)

        if row_name:
            row = dashboard.row(row_name)

            if panel_name:
                return row.panel(panel_name)
            else:
                return row

        return dashboard

    def _get_rows(self, row_name=None, panel_name=None):
        source = system.read_file(ROWS_DIR, row_name)
        row = Row(source)

        if panel_name:
            return row.panel(panel_name)
        else:
            return row

    def _get_panels(self, panel_name=None):
        source = system.read_file(PANELS_DIR, panel_name)
        return Panel(source)

    def save(self, document, category, *parts):
        if category not in LOCAL_RESOURCES:
            raise InvalidPath("Invalid local directory: {}".format(category))

        if category == BACKUPS:
            self._save_backup(document, *parts)
        elif category == TEMPLATES:
            self._save_template(document, *parts)

    def _save_backup(self, document, *parts):
        try:
            dashboard = self.get(list(parts))
            dashboard.update(document)
        except DocumentNotFound:
            if not isinstance(document, Dashboard):
                raise InvalidDocument("Can not add {} as backup"
                                      .format(type(document).__name__))

        system.write_file(BACKUPS_DIR, document.name, document.source)

    def _save_template(self, document, directory, *parts):
        try:
            origin_document = self.get(TEMPLATES, directory, *parts)
            origin_document.update(document)

            top_parent = origin_document
            while top_parent.parent:
                top_parent = top_parent.parent

            document = top_parent
        except DocumentNotFound:
            document_class = DIR_DOCUMENTS[directory]
            if not isinstance(document, document_class):
                raise InvalidDocument("Can not add {} to {}"
                                      .format(type(document).__name__, directory))

        system.write_file(os.path.join(TEMPLATES_DIR, directory), document.name, document.source)

    def remove(self, category, *parts):
        if category not in LOCAL_RESOURCES:
            raise InvalidPath("Invalid local directory: {}".format(category))

        if category == BACKUPS:
            self._remove_backup(*parts)
        elif category == TEMPLATES:
            self._remove_template(*parts)

    def _remove_backup(self, backup):
        system.remove_file(BACKUPS_DIR, backup)

    def _remove_template(self, directory, *parts):
        document = self.get(TEMPLATES, directory, *parts)

        parent = document.parent
        if parent:
            parent.remove_child(document.name)
            system.write_file(os.path.join(TEMPLATES_DIR, directory), parent.name, parent.source)
        else:
            system.remove_file(directory, document.name)
