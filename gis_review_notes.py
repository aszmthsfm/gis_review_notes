# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GisReviewNotes
                             -------------------
        begin                : 2026-06-22
        copyright            : (C) 2026 by zhangshun
        email                : 2023302051097@whu.edu.cn
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsMessageLog, Qgis

import os.path

# Import the code for the DockWidget
from .gis_review_notes_dockwidget import GisReviewNotesDockWidget

# Import architecture modules
from .core.models import ReviewNote
from .data.connection_manager import ConnectionManager
from .data.gpkg_manager import GpkgManager
from .data.note_repository import NoteRepository
from .data.project_meta_repository import ProjectMetaRepository
from .services.config_service import ConfigService
from .services.note_service import NoteService
from .services.selection_service import SelectionService
from .services.render_service import RenderService
from .services.export_service import ExportService
from .controllers.review_controller import ReviewController
from .controllers.map_controller import MapController


class GisReviewNotes:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'GisReviewNotes_{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&GIS Review Notes')
        self.toolbar = self.iface.addToolBar(u'GisReviewNotes')
        self.toolbar.setObjectName(u'GisReviewNotes')

        self.pluginIsActive = False
        self.dockwidget = None

        # 依赖对象占位
        self.conn_manager = None
        self.gpkg_manager = None
        self.note_repo = None
        self.project_meta_repo = None
        self.config_service = None
        self.note_service = None
        self.selection_service = None
        self.render_service = None
        self.export_service = None
        self.review_controller = None
        self.map_controller = None

    def tr(self, message):
        return QCoreApplication.translate('GisReviewNotes', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip is not None: action.setStatusTip(status_tip)
        if whats_this is not None: action.setWhatsThis(whats_this)
        if add_to_toolbar: self.toolbar.addAction(action)
        if add_to_menu: self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = ':/plugins/gis_review_notes/icon.png'
        self.add_action(icon_path, text=self.tr(u'GIS Review Notes'), callback=self.run, parent=self.iface.mainWindow())

    def onClosePlugin(self):
        if self.dockwidget:
            self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        self.pluginIsActive = False

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&GIS Review Notes'), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar
        self._cleanup_resources()

    def _cleanup_resources(self):
        """有序清理资源"""
        if self.review_controller:
            self.review_controller.cleanup()
        if self.render_service:
            self.render_service.clear_overlay()
        if self.map_controller:
            self.map_controller.disable_identify_tool()
        if self.conn_manager:
            self.conn_manager.close()

    def _build_dependency_chain(self):
        """构建依赖注入链"""
        # 1. Data 层
        self.conn_manager = ConnectionManager.instance()

        # 解析 GPKG 路径 (这里先用临时路径，后续由 ConfigService 提供)
        gpkg_path = os.path.join(self.plugin_dir, "review_notes.gpkg")
        self.gpkg_manager = GpkgManager(gpkg_path)
        self.gpkg_manager.init_or_migrate()
        self.conn_manager.switch_gpkg(gpkg_path)

        self.note_repo = NoteRepository(self.conn_manager)
        self.project_meta_repo = ProjectMetaRepository(self.conn_manager)

        # 2. Service 层
        self.config_service = ConfigService()
        self.note_service = NoteService(self.note_repo, self.project_meta_repo)
        self.selection_service = SelectionService(self.iface)
        self.render_service = RenderService(self.iface)
        self.export_service = ExportService()

        # 3. Controller 层
        self.review_controller = ReviewController(
            self.dockwidget, self.note_service, self.selection_service,
            self.render_service, self.export_service
        )
        self.map_controller = MapController(self.iface, self.review_controller)

        # 4. 绑定生命周期信号
        project = QgsProject.instance()
        project.readProject.connect(self._on_project_loaded)
        project.projectSaved.connect(self._on_project_saved)

    def _on_project_loaded(self):
        if self.review_controller:
            self.review_controller.initialize()

    def _on_project_saved(self):
        if self.review_controller:
            self.review_controller.on_project_saved()

    def run(self):
        if not self.pluginIsActive:
            self.pluginIsActive = True
            if self.dockwidget == None:
                self.dockwidget = GisReviewNotesDockWidget()

                # 构建依赖链，将 DockWidget 传给控制器
                self._build_dependency_chain()

                self.dockwidget.closingPlugin.connect(self.onClosePlugin)
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)

            # 首次启动加载当前项目数据
            self._on_project_loaded()
            self.dockwidget.show()
