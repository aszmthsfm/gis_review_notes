# -*- coding: utf-8 -*-
"""
 GisReviewNotes
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsMessageLog, Qgis,QgsApplication


import os.path
from pathlib import Path

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
from .services.render_service import RenderService
from .services.selection_service import SelectionService
from .services.export_service import ExportService
from .controllers.review_controller import ReviewController
from .controllers.map_controller import MapController


class GisReviewNotes:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # 初始化配置服务（用于获取GPKG路径）
        self.config_service = ConfigService()

        # 初始化连接管理器
        self.conn_manager = ConnectionManager.instance()

        # 获取GPKG路径（优先使用配置，否则使用默认路径）
        gpkg_path = self.config_service.get_gpkg_path()
        if not gpkg_path:
            # 使用用户数据目录作为默认路径
            user_data_dir = Path(QgsApplication.qgisSettingsDirPath())
            gpkg_path = str(user_data_dir / "gis_review_notes.gpkg")
            self.config_service.set_gpkg_path(gpkg_path)

        # 初始化GPKG管理器并确保数据库存在
        self.gpkg_manager = GpkgManager(gpkg_path)
        self.gpkg_manager.init_or_migrate()

        # 初始化数据仓库
        self.note_repo = NoteRepository(self.conn_manager)
        self.project_meta_repo = ProjectMetaRepository(self.conn_manager)

        # 初始化业务服务
        self.note_service = NoteService(self.note_repo, self.project_meta_repo)
        self.selection_service = SelectionService(self.iface)
        self.render_service = RenderService(self.iface)
        self.export_service = ExportService()

        # 初始化控制器
        self.review_controller = ReviewController(
            None,  # DockWidget将在run()中设置
            self.note_service,
            self.selection_service,
            self.render_service,
            self.export_service
        )
        self.map_controller = MapController(self.iface, self.review_controller)

        self.actions = []
        self.menu = self.tr(u'&GIS Review Notes')
        self.toolbar = self.iface.addToolBar(u'GisReviewNotes')
        self.toolbar.setObjectName(u'GisReviewNotes')

        self.pluginIsActive = False
        self.dockwidget = None

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate('GisReviewNotes', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar."""
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
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/gis_review_notes/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'GIS Review Notes'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )
        #独立快捷按钮（对选中要素添加批注）
        self.add_action(
            icon_path,  # 若有其他单独设计的图标，可替换此处路径
            text=self.tr(u'为选中要素添加批注'),
            callback=self._add_note_to_selection,
            parent=self.iface.mainWindow()
        )

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        if self.dockwidget:
            self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&GIS Review Notes'), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Run method that loads and starts the plugin"""
        if not self.pluginIsActive:
            self.pluginIsActive = True

            # 创建DockWidget
            self.dockwidget = GisReviewNotesDockWidget()

            # 设置控制器（在run()中设置，确保DockWidget已创建）
            self.review_controller.set_dock_widget(self.dockwidget)

            # 连接关闭信号
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # 添加到界面
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

            # 初始化控制器（确保项目哈希已更新）
            self.review_controller.initialize()

            # 启用地图工具
            self.map_controller.enable_identify_tool()

    def _add_note_to_selection(self):
        """主工具栏独立按钮的回调函数"""
        if not self.pluginIsActive:
            self.run()  # 如果侧边栏未打开，先初始化并打开面板

        # 直接调用控制器中改造后的添加逻辑
        self.review_controller._on_add_note()
