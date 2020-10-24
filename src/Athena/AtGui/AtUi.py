# coding: utf8

from Athena import AtCore, AtUtils, AtConstants

from functools import partial

import os
import re
import random
import string
import sys
import traceback
import webbrowser

from Qt import QtCore, QtGui, QtWidgets, __binding__

#TODO: Remove dev imports.
from pprint import pprint
import time

_DEV = False
_USE_ATHENA_STYLESHEET = True  #TODO: Remove if not used.


#WATCHME: CSS : QCssParser::parseColorValue: Specified color without alpha value but alpha given: 'rgb 255, 255, 255, 25'


class AtSettingsManager(object):
    """Manager for UI settings that can get the value automatically to save the settings."""

    __SETTINGS = QtCore.QSettings('config.ini', QtCore.QSettings.IniFormat)

    __GETTER_METHODS = {}

    @classmethod
    def getSettings(cls):
        """Get the QSettings object used by this manager
        
        Return:
        --------
        QtCore.QSettings
            The QSetting instance used by the Manager
        """

        return cls.__SETTINGS

    @classmethod
    def loadSetting(cls, setting, default=None, type=None, getter=None):
        """Allow to load the specified setting from it's name, else the defaultValue

        Parameters:
        -----------
        setting: str
            The name of the setting to load.
        default: object (default: None)
            The default value to return if the setting is not saved.
        type: object (default: None)
            The type to catch the value in before returning it.
        getter: types.FunctionType (default: None)
            Any callable that would allow to return the value to use to save the setting when saveSettings will be called.
        """

        if getter is not None and callable(getter):
            cls.__GETTER_METHODS[setting] = getter

        setting = cls.__SETTINGS.value(setting, defaultValue=default)
        return setting if type is None else type(setting)

    @classmethod
    def saveSettings(cls):
        """Save the value automatically for setting with a callable getter method."""

        for setting, getter in cls.__GETTER_METHODS.items():
            cls.__SETTINGS.setValue(setting, getter())


class AthenaWidget(QtWidgets.QWidget):
    """Main ui for Athena, it offer all possible features available from The API and is available on multiple softwares.

    Athena is a tool made to execute Sanity processes to check/fix errors based on the current software or OS, 
    it read the loaded python packages to find all thoses who follow the implemented convention. 
    In theses packages it will find all Blueprints by parsing the module and will load them all for the right software. 
    Theses modules will be loaded and the Processor retrieved from the `descriptions` variable in them.

    All Processes have to inherit from the `Athena.AtCore.Process` class, they can be overrided on blueprint level using
    arguments, tags, links and more.
    """

    STYLESHEET = \
    """
    AthenaWidget
    {
        background-color: rgb(70, 70, 70);
    }

    QMenuBar
    {
        color: rgb(200, 200, 200);
        background-color: rgb(70, 70, 70);
    }

    QComboBox
    {
        color: rgb(200, 200, 200);
        background-color: rgb(90, 90, 90);
    }
    QComboBox QAbstractItemView 
    {
        background-color: rgb(50, 50, 50);
    }

    QToolButton
    {
        color: rgb(200, 200, 200);
        background-color: rgba(0, 0, 0, 0);
        height: 20px;
        border: none;
        border-radius: 4px;
    }
    QToolButton:hover
    {
        background-color: rgba(0, 0, 0, 70);
    }
    QToolButton:pressed
    {
        background-color: rgba(0, 0, 0, 40);
    }
    """

    def __init__(self, register, blueprint=None, displayMode=AtConstants.AVAILABLE_DISPLAY_MODE[0], parent=None):
        """ Initialise the Athena tool by loading ressources, getting register and all other data for ui.

        Parameters
        ----------
        blueprint: str, optional
            Blueprint to load by default. If it does not exist, fallback to first Blueprint available (default: None)
        displayMode: str, optional
            Setup the blueprint's display mode at launch (default: 'blueprint')
        mode: str, optional
            Define the mode used to launch the tool ang give different access to some options. (default: 'user')
        verbose: bool
            Should the tool print informations about its execution. (default: False)
        """

        super(AthenaWidget, self).__init__(parent)

        self._register = register
        self._resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)
        self._defaultDisplayMode = displayMode if displayMode in AtConstants.AVAILABLE_DISPLAY_MODE else AtConstants.AVAILABLE_DISPLAY_MODE[0]

        self._defaultBlueprint = blueprint
        
        # Build, Setup and connect the ui
        self._buildUi()
        self._setupUi()
        self._connectUi()

        self.reload()  # Will setup Blueprints and load Processors.

        defaultWidth, defaultHeight = getSizeFromScreen()
        self.resize(
            AtSettingsManager.loadSetting('width', default=defaultWidth, type=int, getter=self.width), 
            AtSettingsManager.loadSetting('height', default=defaultHeight, type=int, getter=self.height)
        )

        self.setWindowTitle('{constants.PROGRAM_NAME} - {software} - {constants.VERSION}'.format(
            constants=AtConstants, 
            software=self._register.software.capitalize())
        )
        self.setWindowIcon(self._resourcesManager.get('logo.png', AtConstants.PROGRAM_NAME, QtGui.QIcon))  #TODO: Find a logo and add it here.

        # This will prevent the window to leave foreground on OSX
        self.setProperty("saveWindowPref", True)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)


    def _buildUi(self):
        """ Create all widgets and layout for the ui """

        self.setObjectName(self.__class__.__name__)

        # -- Main Layout
        self._mainLayout = QtWidgets.QVBoxLayout(self); self._mainLayout.setObjectName('mainLayout')
        self._subLayout = QtWidgets.QVBoxLayout(); self._subLayout.setObjectName('subLayout')

        # -- MenuBar
        self._menuBar = QtWidgets.QMenuBar(); self._menuBar.setObjectName('menuBar')
        self._option_QMenu = self._menuBar.addMenu('Options')
        self._register_QMenu = self._menuBar.addMenu('Register')
        self._help_QMenu = self._menuBar.addMenu('Help')

        self._mainLayout.addWidget(self._menuBar)

        # -- Options Menu
        if __binding__ in ('PySide2', 'PyQt5'):
            self._option_QMenu.addSection('Enable Processes')

        self._checkAll_QAction = QtWidgets.QAction(self._resourcesManager.get('setEnabled.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Enable All Processes', self._option_QMenu)
        self._option_QMenu.addAction(self._checkAll_QAction)
        self._uncheckAll_QAction = QtWidgets.QAction(self._resourcesManager.get('setDisabled.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Disable All Processes', self._option_QMenu)
        self._option_QMenu.addAction(self._uncheckAll_QAction)
        self._defaultAll_QAction = QtWidgets.QAction(self._resourcesManager.get('setDefault.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Reset All Processes', self._option_QMenu)
        self._option_QMenu.addAction(self._defaultAll_QAction)

        if __binding__ in ('PySide2', 'PyQt5'):
            self._option_QMenu.addSection('Toggle Processes')

        self._openAll_QAction = QtWidgets.QAction(self._resourcesManager.get('bottom-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Open All Processes', self._option_QMenu)
        self._option_QMenu.addAction(self._openAll_QAction)
        self._closeAll_QAction = QtWidgets.QAction(self._resourcesManager.get('right-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Close All Processes', self._option_QMenu)
        self._option_QMenu.addAction(self._closeAll_QAction)


        if __binding__ in ('PySide2', 'PyQt5'):
            self._option_QMenu.addSection('Process Ordering')
        self._orderBy_QMenu = self._option_QMenu.addMenu(self._resourcesManager.get('order.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Order By')

        self._orderByBlueprint_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[0], self._orderBy_QMenu)
        self._orderBy_QMenu.addAction(self._orderByBlueprint_QAction)
        self._orderByCategory_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[1], self._orderBy_QMenu)
        self._orderBy_QMenu.addAction(self._orderByCategory_QAction)
        self._orderAlphabetically_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[2], self._orderBy_QMenu)
        self._orderBy_QMenu.addAction(self._orderAlphabetically_QAction)

        self._orderBy = QtWidgets.QActionGroup(self._orderBy_QMenu)
        self._orderBy.addAction(self._orderByBlueprint_QAction)
        self._orderBy.addAction(self._orderByCategory_QAction)
        self._orderBy.addAction(self._orderAlphabetically_QAction)

        # -- Register Menu
        self._createNewPath_QAction = QtWidgets.QAction(self._resourcesManager.get('create.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Create New Path', self._register_QMenu)
        self._register_QMenu.addAction(self._createNewPath_QAction)

        # Help Menu
        self._openWiki_QAction = QtWidgets.QAction(self._resourcesManager.get('wiki.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '[Placeholder] Open Wiki', self._help_QMenu)
        self._help_QMenu.addAction(self._openWiki_QAction)

        self._reportBug_QAction = QtWidgets.QAction(self._resourcesManager.get('bug.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '[Placeholder] Report Bug', self._help_QMenu)
        self._help_QMenu.addAction(self._reportBug_QAction)

        self._support_QAction = QtWidgets.QAction(self._resourcesManager.get('support.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "[Placeholder] Support Project", self._help_QMenu)
        self._help_QMenu.addAction(self._support_QAction)

        self.lab_QAction = QtWidgets.QAction(self._resourcesManager.get('lab.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "[Placeholder] Access Lab", self._help_QMenu)
        self._help_QMenu.addAction(self.lab_QAction)

        self.share_QAction = QtWidgets.QAction(self._resourcesManager.get('share.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "[Placeholder] Share", self._help_QMenu)
        self._help_QMenu.addAction(self.share_QAction)

        # -- Toolbar
        self._toolbar = QtWidgets.QToolBar()

        self._blueprints_QComboBox = QtWidgets.QComboBox(self); self._blueprints_QComboBox.setObjectName('envs_QComboBox')
        self._toolbar.addWidget(self._blueprints_QComboBox)

        self._runAllCheck_QAction = QtWidgets.QAction(self._resourcesManager.get('check.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Check all', self); self._runAllCheck_QAction.setObjectName('runAllCheck_QAction')
        self._toolbar.addAction(self._runAllCheck_QAction)

        self._runAllFix_QAction = QtWidgets.QAction(self._resourcesManager.get('fix.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Fix all', self); self._runAllFix_QAction.setObjectName('runAllFix_QAction')
        self._toolbar.addAction(self._runAllFix_QAction)

        self._subLayout.addWidget(self._toolbar)

        # -- Search and progress bar
        self._searchAndProgressBar = SearchAndProgressBar(self)
        self._subLayout.addWidget(self._searchAndProgressBar)  

        # -- Processes Scroll Area
        self._processWidgets_ProcessesScrollArea = ProcessesScrollArea(self._register, self)
        self._processWidgets_ProcessesScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._subLayout.addWidget(self._processWidgets_ProcessesScrollArea)

        self._mainLayout.addLayout(self._subLayout)

        # -- Dev Menu
        if _DEV:
            self._dev_QMenu = self._menuBar.addMenu('Dev')
            
            self._reloadBlueprints_QAction = QtWidgets.QAction(self._resourcesManager.get('reload.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "Reload Blueprints", self._dev_QMenu)
            self._dev_QMenu.addAction(self._reloadBlueprints_QAction)

            self._documentation_QAction = QtWidgets.QAction(self._resourcesManager.get('documentation.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "[Placeholder] Techical Documentation", self._help_QMenu)
            self._dev_QMenu.addAction(self._documentation_QAction)

    def _setupUi(self):
        """ Setup all widgets, Layout in the ui and the main window """

        self.setStyleSheet(self.STYLESHEET)

        self.setContentsMargins(0, 0, 0, 0)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)
        self._subLayout.setContentsMargins(5, 5, 5, 5)

        # -- Options Menu
        self._option_QMenu.setSeparatorsCollapsible(False)

        self._orderByBlueprint_QAction.setCheckable(True)
        self._orderByBlueprint_QAction.setChecked(self._defaultDisplayMode == self._orderByBlueprint_QAction.text())

        self._orderByCategory_QAction.setCheckable(True)
        self._orderByCategory_QAction.setChecked(self._defaultDisplayMode == self._orderByCategory_QAction.text())

        self._orderAlphabetically_QAction.setCheckable(True)
        self._orderAlphabetically_QAction.setChecked(self._defaultDisplayMode == self._orderAlphabetically_QAction.text())

        self._setupBlueprints()

        self.setDisplayMode()
        
        self._orderBy.setExclusive(True)

        # -- Action Toolbar
        self._toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._toolbar.setIconSize(QtCore.QSize(15, 15))

        self._blueprints_QComboBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # -- Shortcuts
        self.runAllCheck_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_C), self)
        self.runAllFix_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_F), self)

        # -- Search and progress bar
        self._searchAndProgressBar.searchBar.setPlaceholderText('Filter Processes...')

        # -- Dev Menu
        if _DEV:
            self._reloadBlueprintsModules_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_R), self)

    def _connectUi(self):
        """ Connect all widgets to their methods """

        # -- Options Menu
        self._checkAll_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.checkAll)
        self._uncheckAll_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.uncheckAll)
        self._defaultAll_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.defaultAll)

        self._openAll_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.openAll)
        self._closeAll_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.closeAll)

        self._orderBy.triggered.connect(self.setDisplayMode, QtCore.Qt.UniqueConnection)
        
        #TODO: See if this is still relevant ?
        self._blueprints_QComboBox.currentIndexChanged.connect(self._updateScrollAreaBlueprint, QtCore.Qt.UniqueConnection)

        # -- Register
        self._createNewPath_QAction.triggered.connect(self._createNewPath, QtCore.Qt.UniqueConnection)

        self._runAllCheck_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.runAllCheck, QtCore.Qt.UniqueConnection)
        self._runAllFix_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.runAllFix, QtCore.Qt.UniqueConnection)

        # -- Help Menu
        self._openWiki_QAction.triggered.connect(partial(QtGui.QDesktopServices.openUrl, AtConstants.WIKI_LINK), QtCore.Qt.UniqueConnection)
        self._reportBug_QAction.triggered.connect(partial(QtGui.QDesktopServices.openUrl, AtConstants.REPORT_BUG_LINK), QtCore.Qt.UniqueConnection)

        # -- Search and progress bar
        self._searchAndProgressBar.searchBar.textChanged.connect(self._processWidgets_ProcessesScrollArea.filterProcesses, QtCore.Qt.UniqueConnection)

        # -- Shortcuts
        self.runAllCheck_QShortcut.activated.connect(self._processWidgets_ProcessesScrollArea.runAllCheck)
        self.runAllFix_QShortcut.activated.connect(self._processWidgets_ProcessesScrollArea.runAllFix)

        # -- Processes Scroll Area
        # self._processWidgets_ProcessesScrollArea.feedbackMessageRequested.connect(self.statusBar().showMessage)
        self._processWidgets_ProcessesScrollArea.progressValueChanged.connect(self._searchAndProgressBar.setValue)
        self._processWidgets_ProcessesScrollArea.progressValueReseted.connect(self._searchAndProgressBar.reset)

        # -- Dev Menu
        if _DEV:
            self._reloadBlueprints_QAction.triggered.connect(self._reloadBlueprints, QtCore.Qt.UniqueConnection)
            self._documentation_QAction.triggered.connect(partial(QtGui.QDesktopServices.openUrl, AtConstants.WIKI_LINK), QtCore.Qt.UniqueConnection)

            self._reloadBlueprintsModules_QShortcut.activated.connect(self._reloadBlueprints, QtCore.Qt.UniqueConnection)

    def closeEvent(self, event):
        """Call when the ui is about to close, allow to close the ui.

        If the ui can be close (`action_Qtoolbar` not detached) the window will be deleted.
        Else, the ui will only be hidden.

        parameters:
        -----------
        event: QCloseEvent
            Close event given by Qt to this method.
        """

        AtSettingsManager.saveSettings()
        self.deleteLater()
        return super(AthenaWidget, self).closeEvent(event)

    def _reloadBlueprints(self):
        """ Reload the current blueprints.

        notes:
        ------
            Usefull for devellopement purposes, allow to reload the processes classes without breaking the pointers.
        """
        self._register.reload()
        self.reload()

    def reload(self):
        """ Reload Blueprints and update scrollArea."""

        self._setupBlueprints()
        self._updateScrollAreaBlueprint()

    def _updateScrollAreaBlueprint(self):

        with BusyCursor():
            self._processWidgets_ProcessesScrollArea.setBlueprint(self.getBlueprint())

            # Restore the current filter to hidde checks that does not match the search.
            self._searchAndProgressBar.searchBar.textChanged.emit(self._searchAndProgressBar.searchBar.text())

    def _setupBlueprints(self):
        """ Setup the current Blueprint for the tool to display processes."""

        with BusyCursor(), BlockSignals((self._blueprints_QComboBox,), block=True):
            # Get the current text before clearing the QComboBox and populate it with the right data.
            currentBlueprints = self._blueprints_QComboBox.currentText()
            self._blueprints_QComboBox.clear()
            
            for blueprint in self._register.blueprints:
                self._blueprints_QComboBox.addItem(QtGui.QIcon(blueprint.icon), blueprint.name, blueprint)

            # Fallback 1: If there is a value in the QComboBox before, switch on the same value.
            currentIndex = self._blueprints_QComboBox.findText(currentBlueprints)
            if currentIndex > -1 and currentIndex <= self._blueprints_QComboBox.count():
                self._blueprints_QComboBox.setCurrentIndex(currentIndex)

            # Fallback 2: If a default value have been given at init, switch to this value.
            else:
                defaultText = self._defaultBlueprint
                if defaultText is not None:
                    defaultIndex = self._blueprints_QComboBox.findText(defaultText)
                    if defaultIndex > -1:
                        self._blueprints_QComboBox.setCurrentIndex(defaultIndex)
                    else: 
                        self._blueprints_QComboBox.setCurrentIndex(0)

    def setDisplayMode(self):
        """ Change the current display mode of the scroll area widget. """

        self._processWidgets_ProcessesScrollArea.displayMode = self._orderBy.checkedAction().text()
        self._processWidgets_ProcessesScrollArea.refreshDisplay()

    def getBlueprint(self):
        """ Get the blueprint from the register from current context and env. """
        
        return self._blueprints_QComboBox.itemData(self._blueprints_QComboBox.currentIndex(), QtCore.Qt.UserRole)

    def _createNewPath(self):

        directoryToCreate, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 
            'Select New {0} package path'.format(AtConstants.PROGRAM_NAME),
            QtCore.QDir.currentPath(),
            'Folders',
            '',
            QtWidgets.QFileDialog.FileMode.Directory | QtWidgets.QFileDialog.Option.ShowDirsOnly
        )

        if not directoryToCreate:
            return

        AtUtils.createNewAthenaPackageHierarchy(directoryToCreate)


#TODO: There is still improvment to do on this widget to allow complex filters
class SearchAndProgressBar(QtWidgets.QWidget):

    STYLESHEET = \
    """
    QLineEdit#searchBar
    {
        background-color: rgba(0, 0, 0, 60);
        border-width: 1px;
        border-style: solid;
        border-radius: 3px;
        border-color: rgb(255, 255, 255, 25);
        color: rgba(255, 255, 255, 200);
    }
    QLineEdit#searchBar:hover
    {
        background-color: rgba(0, 0, 0, 70);
    }
    QLineEdit#searchBar:Focus
    {
        border-color: rgba(93, 138, 168, 200);
    }
    """

    def __init__(self, parent=None):
        super(SearchAndProgressBar, self).__init__(parent=parent)

        self._resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)

        self._buildUi()
        self._setupUi()

    def _buildUi(self):

        # -- Search and progress Stacked Layout
        self._mainLayout = QtWidgets.QStackedLayout(); self._mainLayout.setObjectName('mainLayout')
        self.setLayout(self._mainLayout)

        self._searchBar = QtWidgets.QLineEdit(self); self._searchBar.setObjectName('searchBar')
        self._mainLayout.addWidget(self._searchBar)

        self._progressBar = QtWidgets.QProgressBar(self); self._progressBar.setObjectName('progressBar')
        self._mainLayout.addWidget(self._progressBar)

    def _setupUi(self):
        self.setStyleSheet(self.STYLESHEET)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedHeight(25)

        # -- Search Bar
        self._searchBar.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._searchBar.setFixedHeight(25)

        if __binding__ in ('PySide2', 'PyQt5'):
            self._searchBar.addAction(self._resourcesManager.get('search.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), QtWidgets.QLineEdit.LeadingPosition)

    @property
    def searchBar(self):
        return self._searchBar

    def setValue(self, value):
        self._mainLayout.setCurrentIndex(1)
        self._progressBar.setValue(value)

    def reset(self):
        self._mainLayout.setCurrentIndex(0)
        self._progressBar.reset()


"""
# View
class ProcessView(QtWidgets.QListView):

    def __init__(self, parent=None):
        super(ProcessView, self).__init__(parent)

    def paintEvent(self, event):
        if self.model().rowCount(0):
            return super(ProcessView, self).paintEvent(event)
        
        viewport = self.viewport()
        painter = QtGui.QPainter(viewport)
        painter.drawText(viewport.rect(), QtCore.Qt.AlignCenter, 'No Process Available')


# Model
class ProcessModel(QtCore.QAbstractListModel):

    #TODO: https://github.com/trufont/defconQt/blob/master/Lib/defconQt/controls/listView.py (1)

    BlueprintRole = QtCore.Qt.UserRole + 1 #TODO: Think about an eventual refacto.

    def __init__(self, data=None, parent=None):
        super(ProcessModel, self).__init__(parent)

        self._data = data or {}

    def data(self, index, role=QtCore.Qt.DisplayRole):
        
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return 'index.internalPointer.blueprint()'

            if role == self.BlueprintRole:
                return self._data

    def setData(self, index, value, role):

        if role == self.BlueprintRole:
            self._data = value
            self.dataChanged.emit(index, index, [self.BlueprintRole])

    def flags(self, index):
        default_flags = super(ProcessModel, self).flags(index)

        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | default_flags

        return default_flags

    def index(self, row, column, parent=QtCore.QModelIndex()):
        
        if parent.isValid():
            return self.createIndex(row, column, parent.internalPointer().children[row])
        
        return self.createIndex(row, column, self._data.get(row, 0))

    def columnCount(self, index):
        return 1

    def rowCount(self, index):
        return len(self._data)


# Delegate
class ProcessDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, parent=None, *args):
        super(ProcessDelegate, self).__init__(parent, *args)

    def paint(self, painter, option, index):

        painter.save()

        itemData = index.data(QtCore.Qt.UserRole + 1)[index.row()]
        
        painter.setFont(QtGui.QFont('Cantarell', 10, QtGui.QFont.Bold))

        painter.drawText(option.rect.adjusted(0, option.rect.height(), option.rect.width(), option.rect.height()), itemData[0])

        painter.restore()
"""


class ProcessWidget(QtWidgets.QWidget):
    """ Individual widget that handle a specific Process

    The widget display the Process name, check, fix and tool button if available and not overrided by a Tag.
    It also display the documentation and log errors in a tree.

    notes:
    ------
        Theses widgets can be used for another tools, they just need a blueprint object.
        The widget use the RessourceManager to prevent generating multiple instances of a same Qicon.
    """

    STYLESHEET = \
    """
    QPushButton
    {
        color: rgb(200, 200, 200);
        border: none;
        margin: 0px;
        text-align: left;
        height: 25px;
        background-color: rgba(0, 0, 0, 0);
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
        border-radius: 7px;
    }
    QPushButton#check, QPushButton#fix, QPushButton#tool, QPushButton#profiler
    {
        padding-left: 4px;
    }
    QPushButton#check:hover, QPushButton#fix:hover, QPushButton#tool:hover, QPushButton#profiler:hover
    {
        background-color: rgba(0, 0, 0, 70);
    }
    QPushButton#check:pressed, QPushButton#fix:pressed, QPushButton#tool:pressed, QPushButton#profiler:pressed
    {
        background-color: rgba(0, 0, 0, 130);
    }
    QPushButton#help:hover
    {
        background-color: rgba(0, 0, 0, 0);
    }
    QPushButton#help:pressed
    {
        background-color: rgba(0, 0, 0, 0);
    }
    """

    _CLOSED_HEIGHT = 25

    def __init__(self, processor, doProfiling=False, parent=None):
        """ Initialise the Process widget from a processor.

        parameters:
        -----------
        processor: QaulityCheck.AtCore.Processor
            An Athena Processor object that will allow to be controlled by this widget.
        parent: QWidget
            The QWidget parent of this widget.
        """ 

        super(ProcessWidget, self).__init__(parent)

        self._resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)
        
        self._processor = processor
        self._doProfiling = doProfiling

        self._settings = processor._settings
        self._name = processor.niceName
        self._category = processor.category
        self._docstring = processor.docstring
        self._isEnabled = processor.isEnabled

        self._isCheckable = processor.isCheckable
        self._isFixable = processor.isFixable
        self._hasTool = processor.hasTool

        self._isNonBlocking = processor.isNonBlocking

        self._status = AtCore.Status._DEFAULT
        self._isOpened = False
        self.__frameQColor = QtGui.QColor(*self._status._color)  # This QColor object will be updated (no new instance everytime color will change)

        self._feedback = None

        self._buildUi()
        self._setupUi()
        self._connectUi()

    def _buildUi(self):
        """ Create each widget that are part of the ProcessWidget """

        # -- Enable CheckBox
        self._enable_QCheckBox = QtWidgets.QRadioButton(self)

        # -- Process Name Display PushButton
        self._name_QLabel = QtWidgets.QPushButton(self._resourcesManager.get('right-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), self._name, self)

        # -- Tool PushButton
        self._tool_QPushButton = QtWidgets.QPushButton(self._resourcesManager.get('tool.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Fix PushButton
        self._fix_QPushButton = QtWidgets.QPushButton(self._resourcesManager.get('fix.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Check PushButton
        self._check_QPushButton = QtWidgets.QPushButton(self._resourcesManager.get('check.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Help PushButton
        self._help_QPushButton = QtWidgets.QPushButton(self._resourcesManager.get('help.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Profiler PushButton
        if _DEV:
            self._profiler_QPushButton =  QtWidgets.QPushButton(self._resourcesManager.get('profiler.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Stack Layout -> Stack Widget
        self._header_QStackedLayout = QtWidgets.QStackedLayout(self)

        self._header_QWidget = QtWidgets.QWidget(self)
        self._header_QWidget.setLayout(self._header_QStackedLayout)

        # -- Container Layout
        container_QWidget = QtWidgets.QWidget(self)
        container_QHBoxLayout = QtWidgets.QHBoxLayout(container_QWidget)

        container_QHBoxLayout.addWidget(self._enable_QCheckBox)
        container_QHBoxLayout.addWidget(self._name_QLabel)

        container_QHBoxLayout.addStretch()

        container_QHBoxLayout.addWidget(self._tool_QPushButton)
        container_QHBoxLayout.addWidget(self._fix_QPushButton)
        container_QHBoxLayout.addWidget(self._check_QPushButton)
        container_QHBoxLayout.addWidget(self._help_QPushButton)
        if _DEV: 
            container_QHBoxLayout.addWidget(self._profiler_QPushButton)

        self._header_QStackedLayout.addWidget(container_QWidget)

        self._container_QHBoxLayout = container_QHBoxLayout
        
        # -- Progressbar
        self._progressbar_QProgressBar = QtWidgets.QProgressBar()
        self._header_QStackedLayout.addWidget(self._progressbar_QProgressBar)

        # -- Process Display Widget
        self._processDisplay = ProcessDisplayWidget(self)

        # -- Main Layout
        main_QVBoxLayout = QtWidgets.QVBoxLayout(self)

        main_QVBoxLayout.addWidget(self._header_QWidget)
        main_QVBoxLayout.addWidget(self._processDisplay)

        self._main_QVBoxLayout = main_QVBoxLayout

    def _setupUi(self):
        """ Setup each widget that constitue the ProcessWidget. """

        # -- Enable CheckBox
        self._enable_QCheckBox.setChecked(self._isEnabled)

        # -- Process Name Display PushButton
        # self._name_QLabel.setButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._name_QLabel.setIconSize(QtCore.QSize(15, 15))

        # -- Tool PushButton
        self._tool_QPushButton.setObjectName(AtConstants.TOOL)
        self._tool_QPushButton.setToolTip('Launch "{0}" tool'.format(self._name))
        self._tool_QPushButton.setVisible(self._hasTool)

        # -- Fix PushButton
        self._fix_QPushButton.setObjectName(AtConstants.FIX)
        self._fix_QPushButton.setToolTip('Run "{0}" fix'.format(self._name))
        self._fix_QPushButton.setVisible(False)

        # -- Check PushButton
        self._check_QPushButton.setObjectName(AtConstants.CHECK)
        self._check_QPushButton.setToolTip('Run "{0}" check'.format(self._name))
        self._check_QPushButton.setVisible(self._isCheckable)

        # -- Help PushButton
        self._help_QPushButton.setObjectName('help')
        self._help_QPushButton.setToolTip(self._docstring)
        self._help_QPushButton.enterEvent = self.showTooltip

        # -- Profiler PushButton
        if _DEV:
            self._profiler_QPushButton.setObjectName('profiler')
            self._profiler_QPushButton.setToolTip('Profile process'.format(self._name))
            self._profiler_QPushButton.setVisible(True)

        # -- Container Layout
        self._container_QHBoxLayout.setContentsMargins(5, 0, 0, 0)
        self._container_QHBoxLayout.setSpacing(5)

        # -- Progressbar
        self._progressbar_QProgressBar.setAlignment(QtCore.Qt.AlignLeft)
        self._progressbar_QProgressBar.setFormat(AtConstants.PROGRESSBAR_FORMAT.format(self._name))

        # -- Stack Layout -> Stack Widget
        self._header_QWidget.setFixedHeight(25)
        self._header_QWidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        # -- Process Display Widget
        self._processDisplay.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._processDisplay.setVisible(False)

        # -- Main Layout
        self._main_QVBoxLayout.setContentsMargins(0, 0, 0, 0)
        self._main_QVBoxLayout.setSpacing(0)

        #WATCHME: It seems that without this the background will stay white untill palette is refreshed.
        palette = self.palette()
        palette.setColor(palette.Background, self.__frameQColor)
        self.setPalette(palette)

        self.setAutoFillBackground(True)

        self.setStyleSheet(self.STYLESHEET)
        self.setFixedHeight(self._CLOSED_HEIGHT)

    def _connectUi(self):
        """ Connect all widget to their respective methods. """

        # -- Process Name Display PushButton
        self._name_QLabel.clicked.connect(self.toggleDisplayWidget)

        # -- Tool PushButton
        self._tool_QPushButton.clicked.connect(self.execTool)

        # -- Fix PushButton
        self._fix_QPushButton.clicked.connect(self.execFix)

        # -- Check PushButton
        self._check_QPushButton.clicked.connect(self.execCheck)

        # -- Profiler PushButton
        if _DEV:
            self._profiler_QPushButton.clicked.connect(self._openDisplayWidget)
            self._profiler_QPushButton.clicked.connect(partial(self._processDisplay.logProfiler, self._processor._processProfile))

        # -- Connect the progressbar to the process _progressbar attribute.
        self._processor.setProgressbar(self._progressbar_QProgressBar)

        # -- Log Widget
        self._processDisplay.sizeChanged.connect(self._updateHeight)

    def enterEvent(self, event):
        """ Event handled by Qt to manage mouse enter event and lighter the widget color.

        parameters:
        -----------
        event: QEvent
            Event emitted by Qt when mouse enter the widget.
        """

        palette = self.palette()

        palette.setColor(palette.Background, self.__frameQColor.lighter(125))
        self.setPalette(palette)

    def leaveEvent(self, event):
        """ Event handled by Qt to manage mouse exit event and reset widget color.

        parameters:
        -----------
        event: QEvent
            Event emitted by Qt when mouse exit the widget.
        """

        palette = self.palette()

        palette.setColor(palette.Background, self.__frameQColor)
        self.setPalette(palette)

    def mousePressEvent(self, event):
        """ Event handled by Qt to manage click press on the widget and darker it's color.

        parameters:
        -----------
        event: QEvent
            Event emitted by Qt when click is pressed on the widget.
        """

        palette = self.palette()

        palette.setColor(palette.Background, self.__frameQColor.darker(125))
        self.setPalette(palette)

        if event.button() is QtCore.Qt.MouseButton.LeftButton:
            self.toggleDisplayWidget()
        elif event.button() is QtCore.Qt.MouseButton.RightButton:
            self.setChecked(not self.isChecked())
        else:
            return event.ignore()

        return event.accept()

    def mouseReleaseEvent(self, event):
        """ Event handled by Qt to manage click release on the widget and reset it's color.

        parameters:
        -----------
        event: QEvent
            Event emitted by Qt when click is released on the widget.
        """

        palette = self.palette()

        # It seems that mouseReleaseEvent is triggered after leaveEvent
        palette.setColor(palette.Background, self.__frameQColor.lighter(125))
        self.setPalette(palette)

    def _updateHeight(self, size):
        # We always include the _CLOSED_HEIGHT constant to keep the space for the header of the check and simulate an openning.
        self.setFixedHeight(self._CLOSED_HEIGHT + size.height())

    @property
    def feedback(self):
        """ Getter that return the value stored in `_feedback` """

        return self._feedback

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, newStatus):
        self._status = newStatus
        self.__frameQColor.setRgb(*newStatus._color)

    def logResult(self, feedback):
        self._feedback = feedback

        if not feedback:
            self._processDisplay.setVisible(self._isOpened)
            self.closeDisplayWidget()
            return

        if isinstance(feedback, list) and isinstance(feedback[0], AtCore.Feedback):
            self._processDisplay.logFeedback(feedback)
        elif isinstance(feedback, Exception):
            self._processDisplay.logTraceback(feedback)
        else:
            raise NotImplementedErrror('Data to log are not implemented yet.')

        self.openDisplayWidget()

    def toggleDisplayWidget(self):
        """Switch visibility of the traceback widget. """

        if not self._isOpened:
            self.openDisplayWidget()
        else:
            self.closeDisplayWidget()
            
    def _openDisplayWidget(self):
        """ Show the traceback widget and change the displayed arrow shape. """

        self._name_QLabel.setIcon(self._resourcesManager.get('bottom-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon))
        self._isOpened = True
        self._updateHeight(self._processDisplay.sizeHint())

        self._processDisplay.setVisible(self._isOpened)

    def openDisplayWidget(self):
        """ Show the traceback widget and change the displayed arrow shape. """

        if not self.feedback:
            return
        self._openDisplayWidget()

    def closeDisplayWidget(self):
        """ Hide the traceback widget and change the displayed arrow shape. """

        self._name_QLabel.setIcon(self._resourcesManager.get('right-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon))
        self._isOpened = False
        self.setFixedHeight(self._CLOSED_HEIGHT)

        self._processDisplay.setVisible(self._isOpened)

    def showTooltip(self, event):
        """ Show the tooltip on the cursor's position.

        parameters:
        -----------
        event: QEvent
            Event given by Qt to manage the tooltip.
        """

        position = QtGui.QCursor.pos()
        widget = self.childAt(self.mapFromGlobal(position))

        if widget:
            QtWidgets.QToolTip.showText(position, widget.toolTip(), self)

    def isChecked(self):
        """ Return Wheter the ProcessWidget is checked or not. """
        return self._enable_QCheckBox.isChecked()

    def setChecked(self, state):
        """ Check the ProcessWidget """

        self._enable_QCheckBox.setChecked(state)

    def execCheck(self):
        """ Run the `check` method of the Blueprint's Process.

        Exec the Process `check` method and retrieve the result to change the process state and log feedback if necessary.
        Handle any Exception to switch the ProcessWidget state to 'Exception' and log the Exception's feedback in it.
        """

        self.closeDisplayWidget()

        with self.__ExecContext(self), BusyCursor():
            try:
                result, status = self._processor._check(links=True, doProfiling=self._doProfiling)

                self.status = status
                if isinstance(status, AtCore.Status.FailStatus):
                    self.logResult(result)
                    self._fix_QPushButton.setVisible(self._isFixable)
                elif isinstance(status, AtCore.Status.SuccessStatus):
                    self.logResult(result)
                    self._fix_QPushButton.setVisible(False)

            except Exception as exception:
                self.status = AtCore.Status._EXCEPTION  # The process encounter an exception during it's execution.
                self.logResult(exception)
                print(AtUtils.formatTraceback(traceback.format_exc(exception)))

    def execFix(self):
        """ Run the `fix` method of the Blueprint's Process.

        Exec the Process `fix` method and handle any Exception to switch the ProcessWidget state to 'Exception' and log the 
        Exception's feedback in it.
        Then, launch the `execCheck` method to catch any other error to update the ProcessWidget.
        """

        self.closeDisplayWidget()

        with self.__ExecContext(self), BusyCursor():
            try:
                result, status = self._processor.fix(doProfiling=self._doProfiling)

                self.status = status
                if isinstance(status, AtCore.Status.FailStatus):
                    self.logResult(result)
                    self._fix_QPushButton.setVisible(self._isFixable)
                elif isinstance(status, AtCore.Status.SuccessStatus):
                    self.logResult(None)
                    self._fix_QPushButton.setVisible(False)

            except Exception as exception:
                self.status = AtCore.Status._EXCEPTION  # The process encounter an exception during it's execution.
                self.logResult(exception)
                print(AtUtils.formatTraceback(traceback.format_exc(exception)))
                return

        # After a fix, re-launch a check to ensure everything is clean.
        # self._register.getData('parameters').get('recheck', False)
        self.execCheck()

    def execTool(self):
        """ Run the `tool` method of the Blueprint's Process.

        Exec the Process `tool` method and handle any Exception to switch the ProcessWidget state to 'Exception' and log the 
        Exception's feedback in it.
        """

        self.closeDisplayWidget()

        with self.__ExecContext(self), BusyCursor():
            try:
                result = self._processor.tool(doProfiling=self._doProfiling)
                if result is not None and isinstance(result, QtWidgets.QWidget):
                    result.setParent(self, QtCore.Qt.Window)
                    result.show()

            except Exception as exception:
                self.status = AtCore.Status._EXCEPTION  # The process encounter an exception during it's execution.
                self.logResult(exception)
                print(AtUtils.formatTraceback(traceback.format_exc(exception)))

    class __ExecContext(object):

        def __init__(self, instance):
            self.instance = instance

        def __enter__(self):
            self.instance.leaveEvent(None)

            self.instance._header_QStackedLayout.setCurrentIndex(1)
            self.instance._progressbar_QProgressBar.setValue(0)

        def __exit__(self, *args):
            
            self.instance._header_QStackedLayout.setCurrentIndex(0)

            if self.instance.underMouse():
                self.instance.enterEvent(None)
            else:
                self.instance.leaveEvent(None)


class _AbstractLogTreeWidget(QtWidgets.QTreeWidget):
    """Abstract parent class for tree widgets in ProcessDisplayWidget.

    This class is meant to be subclassed by custom tree widget to display things in ProcessDisplayWidget.
    It will override the sizeHint method to allow TreeWidget to rescale automatically based on it's content.

    """
    # see `outline` for Focus -> does not seeems to work.
    # For maya it's still better without style..
    STYLESHEET = \
    """

    QAbstractScrollArea
    {
        margin-left: 1px;
        margin-right: 1px;
        margin-bottom: 1px;
    }

    QTreeWidget
    {   
        background-color: rgba(45, 45, 45, 255);
        alternate-background-color: rgba(55, 55, 55, 255);
        color: rgb(200, 200, 200);
    }
    QTreeWidget:Focus
    {
        border-width: 1px;
        border-style: solid;
        border-color: rgba(93, 138, 168, 200);
    }
    QTreeWidget::item:hover, QTreeWidget::item:hover:selected 
    {
        background-color: rgba(55, 55, 55, 120);
    }

    QTreeWidget::item:selected 
    {
        border:none;
        background-color: rgba(255,255,255,0);
    }

    QHeaderView
    {
        margin: 0px;
    }
    QHeaderView::section
    {   
        color: rgb(200, 200, 200);
        background-color: rgb(90, 90, 90);
    }

    QScrollBar
    {
        margin: 1px;
    }
    """

    sizeChanged = QtCore.Signal(QtCore.QSize)

    def __init__(self, parent=True):
        super(_AbstractLogTreeWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        # self.setAutoFillBackground(True)
        # self.setStyleSheet(self.STYLESHEET)
        self.setAlternatingRowColors(True)

    def sizeHint(self):
        sizeHint = super(_AbstractLogTreeWidget, self).sizeHint()

        height = 2 * self.frameWidth() # border around tree
        if not self.isHeaderHidden():
            height += self.header().sizeHint().height()

        it = QtWidgets.QTreeWidgetItemIterator(self)
        while it.value() is not None:
            height += self.rowHeight(self.indexFromItem(it.value()))
            it += 1

        # We always include the height of the horizontalScrollBar to be sure it will not hide a feedback.
        height += self.horizontalScrollBar().height()

        return QtCore.QSize(sizeHint.width(), height + 5)  # +5 is a fixed offset to add some free space under the latest feedback.

    def minimumSizeHint(self):
        return self.sizeHint()

class FeedbackWidget(_AbstractLogTreeWidget):

    def __init__(self, parent=True):
        super(FeedbackWidget, self).__init__(parent)

        self._resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)

        # -- Connect the feedback widget to allow call of expand and collapse.
        self.itemExpanded.connect(self.expandFeedback)
        self.itemCollapsed.connect(self.collapseFeedback)

    def mouseReleaseEvent(self, event):

        if event.button() is QtCore.Qt.MouseButton.RightButton:
            return event.ignore()

        selectionDict = self.getSelectionDict()
        if not selectionDict:
            return
        elif len(selectionDict) > 1:
            print('Unable to select items from different thread due to different selection methods.')  #FIXME: Replace with better log, error or find a way to use multiple selectMethodes.
            return
        else:
            parentModelIndex = next(iter(selectionDict))
            itemsIndexes = [item.row() for item in selectionDict[parentModelIndex]]

            feedback = self.itemFromIndex(parentModelIndex).data(0, QtCore.Qt.UserRole)
            if itemsIndexes:
                feedback.select(itemsIndexes)
            else:
                feedback.selectAll()

        return super(FeedbackWidget, self).mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        
        contextMenu = QtWidgets.QMenu(self)
        contextMenu.setSeparatorsCollapsible(False)

        selectAll_QAction = QtWidgets.QAction(self._resourcesManager.get('select.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Select All', contextMenu)
        selectAll_QAction.triggered.connect(self.selectAll)
        contextMenu.addAction(selectAll_QAction)

        contextMenu.addSeparator()

        expandAll_QAction = QtWidgets.QAction(self._resourcesManager.get('bottom-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Expand All', contextMenu)
        expandAll_QAction.triggered.connect(self.expandAllFeedback)
        contextMenu.addAction(expandAll_QAction)

        collapseAll_QAction = QtWidgets.QAction(self._resourcesManager.get('right-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Collapse All', contextMenu)
        collapseAll_QAction.triggered.connect(self.collapseAllFeedback)
        contextMenu.addAction(collapseAll_QAction)

        contextMenu.popup(QtGui.QCursor.pos())

        return event.accept()

    def logFeedback(self, feedbacks):

        self.setHeaderHidden(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setHeaderLabels(['Found {0} error{1}'.format(len(feedbacks), 's' if len(feedbacks) > 1 else ''), ''])

        self.clear()
        for feedback in feedbacks:

            thread = feedback._thread

            if feedback:
                parent = QtWidgets.QTreeWidgetItem([str(thread.title), '        found {0}'.format(str(len(feedback._toDisplay)))])
                parent.setForeground(1, QtGui.QColor(*thread._status._color))  # Color the number of issue with the status color.
                parent.setToolTip(1, thread._status._name)  # Display the status name as tooltip.
                parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
            else:
                parent = QtWidgets.QTreeWidgetItem([str(thread.title)])
                parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.DontShowIndicator)

            # If there is a documentation for this error display it in a tooltip.
            if thread.documentation is not None:
                parent.setToolTip(0, thread.documentation)

            parent.setData(0, QtCore.Qt.UserRole, feedback)

            self.addTopLevelItem(parent)

        self.resizeColumnToContents(0)

    def _clearItemChildren(self, item):
        for i in reversed(range(item.childCount())):
            child = item.takeChild(i)
            del child

    def expandFeedback(self, item):
        with BusyCursor():
            feedback = item.data(0, QtCore.Qt.UserRole)

            for toDisplay, toSelect in zip(feedback.toDisplay, feedback.toSelect):
                if not toDisplay:
                    continue
                child = QtWidgets.QTreeWidgetItem([str(toDisplay)])
                item.addChild(child)
                #FIXME: Internal C++ object (PySide2.QtWidgets.QTreeWidgetItem) already deleted. (Raised when Pandora is init before first Athena Launch)
            self.sizeChanged.emit(self.sizeHint())

    def collapseFeedback(self, item):
        with BusyCursor():
            self._clearItemChildren(item)
            self.sizeChanged.emit(self.sizeHint())

    def expandAllFeedback(self):
        items = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        for item in items:
            item.setExpanded(True)

    def collapseAllFeedback(self):
        items = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        for item in items:
            item.setExpanded(False)

    def selectAll(self):

        selectedItem = next(iter(self.selectedItems()), None) # Only one because the right click changed
        if selectedItem is None:
            return
        parent = selectedItem.parent() or selectedItem

        feedback = parent.data(0, QtCore.Qt.UserRole)
        feedback.selectAll()
        
        selectedItem.setSelected(False)
        parent.setSelected(True)

    def iterFeedbackItems(self):
        for i in range(self.topLevelItemCount()):
            yield self.topLevelItem(i)

    def getSelectionDict(self):

        selectionDict = {}
        selectedIndexesIt = iter(self.selectionModel().selectedIndexes())
        for each, _ in list(zip(selectedIndexesIt, selectedIndexesIt)):
            parent = each.parent()
            if parent.row() == -1:
                selectionDict[each] = []
            else:
                if parent not in selectionDict:
                    selectionDict[parent] = []
                selectionDict[parent].append(each)

        return selectionDict


class TracebackWidget(QtWidgets.QPlainTextEdit):

    def __init__(self, parent=None):
        super(TracebackWidget, self).__init__(parent)

        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.setReadOnly(True)

        #WATCHME: It looks like for the first call off `self.horizontalScrollBar().height()` in sizeHint the value is wrong...
        self.horizontalScrollBar().setFixedHeight(12)

    def mousePressEvent(self, event):
        """Override the `mousePressEvent` to be abble to accept the event on right click. (`contextMenuEvent`)

        """
        if event.button() is QtCore.Qt.MouseButton.RightButton:
            return event.accept()  # Accept the event to prevent bubble up.

        return super(TracebackWidget, self).mousePressEvent(event)

    def contextMenuEvent(self, event):
        
        contextMenu = QtWidgets.QMenu(self)
        contextMenu.setSeparatorsCollapsible(False)

        printTraceback_QAction = QtWidgets.QAction('Print Traceback', contextMenu)
        printTraceback_QAction.triggered.connect(self.printTraceback)
        contextMenu.addAction(printTraceback_QAction)

        copyTraceback_QAction = QtWidgets.QAction('Copty to clipboard', contextMenu)
        copyTraceback_QAction.triggered.connect(self.copyTracebackToClipboard)
        contextMenu.addAction(copyTraceback_QAction)

        contextMenu.popup(QtGui.QCursor.pos())
        return event.accept()

    def sizeHint(self):
        sizeHint = super(TracebackWidget, self).sizeHint()
        
        height = self.fontMetrics().height() * (self.getLineCount() + 1)
        height += self.horizontalScrollBar().height()

        newSizeHint = QtCore.QSize(sizeHint.width(), height)

        return newSizeHint

    def minimumSizeHint(self):
        return self.sizeHint()

    def logTraceback(self, exception):
        #TODO: Think about a way to stor the exception in the widget.
        
        self.document().setPlainText(AtUtils.formatTraceback(traceback.format_exc(exception)))

        # When the text is too long and because the cursor is at the end, the scrollBar can already be on the right.
        self.moveCursor(QtGui.QTextCursor.Start)

        # This is called to ensure that the view is centered where we need by default.
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().minimum())

    def getLineCount(self):
        return len(self.toPlainText().split('\n'))

    def printTraceback(self):
        print(self.toPlainText())

    def copyTracebackToClipboard(self, clipboard=QtWidgets.QApplication.clipboard()):
        clipboard.setText(self.toPlainText())


class ProfilerWidget(_AbstractLogTreeWidget):

    def __init__(self, parent=None):
        super(ProfilerWidget, self).__init__(parent)

        self.itemExpanded.connect(self.emitSizeChange)
        self.itemCollapsed.connect(self.emitSizeChange)

    def contextMenuEvent(self, event):
        
        contextMenu = QtWidgets.QMenu(self)
        contextMenu.setSeparatorsCollapsible(False)

        saveStatsAs_QAction = QtWidgets.QAction('Save Stats As...', contextMenu)
        saveStatsAs_QAction.triggered.connect(self._saveStatsAs)
        contextMenu.addAction(saveStatsAs_QAction)

        contextMenu.popup(QtGui.QCursor.pos())
        return event.accept()

    def emitSizeChange(self, *args, **kwargs):
        self.sizeChanged.emit(self.sizeHint())

    def logProfiler(self, profiler):
        headers = ['Functions']
        headers.extend(profiler.CATEGORIES)
        self.setHeaderLabels(headers)

        # -- Set check Datas
        checkProfile = profiler.get(AtConstants.CHECK)
        if checkProfile is not None:
            currentCheckWidget = next(iter(self.findItems(AtConstants.CHECK, 0) or ()), None)
            if not currentCheckWidget or (checkProfile['time'] > currentCheckWidget.data(0, QtCore.Qt.UserRole)['time']):
                checkParent = QtWidgets.QTreeWidgetItem([AtConstants.CHECK, checkProfile['ncalls'], checkProfile['tottime']])
                checkParent.setData(0, QtCore.Qt.UserRole, checkProfile)
                for call in checkProfile['calls']:
                    callData = ['']
                    callData.extend(call)
                    checkChild = QtWidgets.QTreeWidgetItem(callData)
                    checkParent.addChild(checkChild)

                if currentCheckWidget:
                    index = self.indexOfTopLevelItem(currentCheckWidget)
                    self.takeTopLevelItem(index)
                    del currentCheckWidget
                    self.insertTopLevelItem(index, checkParent)
                else:
                    self.addTopLevelItem(checkParent)


        # -- Set fix Data
        fixProfile = profiler.get(AtConstants.FIX)
        if fixProfile is not None:
            currentFixWidget = next(iter(self.findItems(AtConstants.FIX, 0) or ()), None)
            if not currentFixWidget or (fixProfile['time'] > currentFixWidget.data(0, QtCore.Qt.UserRole)['time']):
                fixParent = QtWidgets.QTreeWidgetItem([AtConstants.FIX, fixProfile['ncalls'], fixProfile['tottime']])
                fixParent.setData(0, QtCore.Qt.UserRole, fixProfile)
                for call in fixProfile['calls']:
                    callData = ['']
                    callData.extend(call)
                    fixChild = QtWidgets.QTreeWidgetItem(callData)
                    fixParent.addChild(fixChild)

                if currentFixWidget:
                    index = self.indexOfTopLevelItem(currentFixWidget)
                    self.takeTopLevelItem(index)
                    del currentFixWidget
                    self.insertTopLevelItem(index, fixParent)
                else:
                    self.addTopLevelItem(fixParent)

        # -- Set Tool Data
        toolProfile = profiler.get(AtConstants.TOOL)
        if toolProfile is not None:
            currentToolWidget = next(iter(self.findItems(AtConstants.TOOL, 0) or ()), None)
            if not currentToolWidget or (toolProfile['time'] > currentToolWidget.data(0, QtCore.Qt.UserRole)['time']):
                toolParent = QtWidgets.QTreeWidgetItem([AtConstants.TOOL, toolProfile['ncalls'], toolProfile['tottime']])
                toolParent.setData(0, QtCore.Qt.UserRole, toolProfile)
                for call in toolProfile['calls']:
                    callData = ['']
                    callData.extend(call)
                    toolChild = QtWidgets.QTreeWidgetItem(callData)
                    toolParent.addChild(toolChild)

                if currentToolWidget:
                    index = self.indexOfTopLevelItem(currentToolWidget)
                    self.takeTopLevelItem(index)
                    del currentToolWidget
                    self.insertTopLevelItem(index, toolParent)
                else:
                    self.addTopLevelItem(toolParent)

    def _saveStatsAs(self):
        raise NotImplementedError

class ProcessDisplayStackedLayout(QtWidgets.QStackedLayout):
    def __init__(self, parent=None):
        super(ProcessDisplayStackedLayout, self).__init__(parent)

    def setCurrentWidget(self, widget):
        for i in range(self.count()):
            self.widget(i).setVisible(False)
            self.widget(i).setEnabled(False)

        widget.setVisible(True)
        widget.setEnabled(True)

        return super(ProcessDisplayStackedLayout, self).setCurrentWidget(widget)

class ProcessDisplayWidget(QtWidgets.QWidget):

    sizeChanged = QtCore.Signal(QtCore.QSize)

    def __init__(self, parent):
        super(ProcessDisplayWidget, self).__init__(parent)

        self._resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)

        self._buildUi()
        self._setupUi()
        self._connectUi()

    def _buildUi(self):
        self._mainLayout = ProcessDisplayStackedLayout(self)

        self._feedbackWidget = FeedbackWidget(self)
        self._mainLayout.addWidget(self._feedbackWidget)
        
        # Other widgets will be loaded lazily. Thet will be created if they need to be displayed.
        self._tracebackWidget = None
        self._profilerWidget = None

    def _setupUi(self):
        # Seems to not work on PySide 1
        # self.header().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

        self._feedbackWidget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

    def _connectUi(self):
        self._feedbackWidget.sizeChanged.connect(self._updateHeight, QtCore.Qt.UniqueConnection)

    def sizeHint(self):
        sizeHint = self._mainLayout.currentWidget().sizeHint()
        self._updateHeight(sizeHint)
        return sizeHint

    def _updateHeight(self, size):
        # We always include the _CLOSED_HEIGHT constant to keep the space for the header of the check and simulate an openning.
        self.setFixedHeight(size.height())
        self.sizeChanged.emit(size)

    def _addTracebackWidget(self):
        # -- Build Traceback Widget
        self._tracebackWidget = TracebackWidget(self)
        self._mainLayout.addWidget(self._tracebackWidget)
        
        # -- Setup Traceback Widget
        self._tracebackWidget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

    def _addProfilerWidget(self):
        # -- Build Profiler Widget
        self._profilerWidget = ProfilerWidget(self)
        self._mainLayout.addWidget(self._profilerWidget)
        self._profilerWidget.sizeChanged.connect(self._updateHeight, QtCore.Qt.UniqueConnection)

        # -- Setup Profiler Widget
        self._profilerWidget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

    def displayFeedback(self):
        self._mainLayout.setCurrentWidget(self._feedbackWidget)

        self._feedbackWidget.updateGeometry()
        # self.updateGeometry()

    def displayTracebak(self):
        # This will lazilly load the tracebackWidget, it will create it if it has been requested.
        if self._tracebackWidget is None:
            self._addTracebackWidget()
        self._mainLayout.setCurrentWidget(self._tracebackWidget)

        self._tracebackWidget.updateGeometry()
        # self.updateGeometry()

    def displayProfiler(self):
        # This will lazilly load the profilerWidget, it will create it if it has been requested.
        if self._profilerWidget is None:
            self._addProfilerWidget()
        self._mainLayout.setCurrentWidget(self._profilerWidget)

        self._profilerWidget.updateGeometry()
        # self.updateGeometry()

    def logFeedback(self, feedbacks):
        self.displayFeedback()
        self._feedbackWidget.logFeedback(feedbacks)

    def logTraceback(self, traceback):
        self.displayTracebak()
        self._tracebackWidget.logTraceback(traceback)

    def logProfiler(self, profiler):
        self.displayProfiler()
        self._profilerWidget.logProfiler(profiler)


class ScrollBar(QtWidgets.QScrollBar):

    # For Horizontal scroll bar
    # https://stackoverflow.com/questions/24725558/qt-applying-stylesheet-on-qscrollarea-making-horizontal-scrollbar-disappear-but

    STYLESHEET = \
    """
    QScrollBar:vertical 
    {
        background: rgb(45, 45, 45);
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical
    {
        background: rgb(110, 110, 110);
        min-height: 20px;
    }
    QScrollBar::add-line:vertical
    {
        background: rgba(0, 0, 0, 0);
        height: 0px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
    }
    QScrollBar::sub-line:vertical
    {
        background: rgba(0, 0, 0, 0);
        height: 0px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical
    {
        background: none;
    }
    """

    STYLESHEET_HOVER = \
    """
    QScrollBar:vertical 
    {{   
        background: {linesBackground};
        margin: {buttonsHeight} 0 {buttonsHeight} 0;
    }}
    QScrollBar::handle:vertical 
    {{   
        background: {handleBackground};
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover
    {{
        background: {handleHoverBackground};
    }}
    QScrollBar::handle:vertical:pressed
    {{
        background: {handlePressedBackground};
    }}
    QScrollBar::add-line:vertical 
    {{
        background: {linesBackground};
        height: {buttonsHeight};
        subcontrol-position: bottom;
        subcontrol-origin: margin;
    }}
    QScrollBar::add-line:vertical:hover
    {{
        background: {buttonHoverBackground};
    }}
    QScrollBar::add-line:vertical:pressed
    {{
        background: {buttonPressedBackground};
    }}
    QScrollBar::sub-line:vertical 
    {{
        background: {linesBackground};
        height: {buttonsHeight};
        subcontrol-position: top;
        subcontrol-origin: margin;
    }}
    QScrollBar::sub-line:vertical:hover
    {{
        background: {buttonHoverBackground};
    }}
    QScrollBar::sub-line:vertical:pressed
    {{
        background: {buttonPressedBackground};
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical
    {{
        background: none;
    }}
    """

    ARGS_HOVER = \
    {
        'linesBackground': 'rgb(70, 70, 70)',
        'handleBackground': 'rgb(110, 110, 110)',
        'handleHoverBackground': 'rgb(130, 130, 130)',
        'handlePressedBackground': 'rgb(150, 150, 150)',
        'buttonHoverBackground': 'rgb(80, 80, 80)',
        'buttonPressedBackground': 'rgb(100, 100, 100)',
        'buttonsHeight': '10px',
    }

    def __init__(self, parent=None, minimumWidth=4, maximumWidth=12, increaseDuration=50, decreaseDuration=100,
                 increaseTimer=150, decreaseTimer=1200):
        super(ScrollBar, self).__init__(parent=parent)

        self._minimumWidth = minimumWidth
        self._maximumWidth = maximumWidth
        self._increaseDuration = increaseDuration
        self._decreaseDuration = decreaseDuration
        self._increaseTimer = increaseTimer
        self._decreaseTimer = decreaseTimer

        self._ressourceManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)
        self.downPixmap = self._ressourceManager.get('scrollbar_down_arrow.png', AtConstants.PROGRAM_NAME, QtGui.QPixmap).scaled(10, 10, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.upPixmap = self._ressourceManager.get('scrollbar_up_arrow.png', AtConstants.PROGRAM_NAME, QtGui.QPixmap).scaled(10, 10, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        self._timer = QtCore.QTimer(self)
        self._increaseAnimation = QtCore.QVariantAnimation(startValue=minimumWidth, endValue=maximumWidth, duration=increaseDuration)
        self._decreaseAnimation = QtCore.QVariantAnimation(startValue=maximumWidth, endValue=minimumWidth, duration=decreaseDuration)

        self.setStyleSheet(self.STYLESHEET)
        self._setWidth(minimumWidth)
        self._setLarge(False)

        self._connectUi()

    def _connectUi(self):
        self._increaseAnimation.valueChanged.connect(self._setWidth)
        self._increaseAnimation.finished.connect(partial(self._setLarge, True))

        self._decreaseAnimation.valueChanged.connect(self._setWidth)
        self._decreaseAnimation.finished.connect(partial(self._setLarge, False))

    def enterEvent(self, event):
        super(ScrollBar, self).enterEvent(event)

        # If the scrollBar is already large, we need to stop the timer used to reset it.
        self._timer.stop()

        if not self._isLarge:
            self._timer = QtCore.QTimer(self)
            self._timer.timeout.connect(self._increaseAnimation.start)
            self._timer.timeout.connect(partial(self.setStyleSheet, self.STYLESHEET_HOVER.format(**self.ARGS_HOVER)))
            self._timer.timeout.connect(self._timer.stop)
            self._timer.start(self._increaseTimer)

    def leaveEvent(self, event):
        super(ScrollBar, self).leaveEvent(event)

        # We need to ensure that the timer is stopped before definning a new one. (probably garbaged if timeout/stop only.)
        self._timer.stop()

        if self._isLarge:
            self._timer = QtCore.QTimer(self)
            self._timer.timeout.connect(self._decreaseAnimation.start)
            self._timer.timeout.connect(partial(self.setStyleSheet, self.STYLESHEET))
            self._timer.timeout.connect(self._timer.stop)
            self._timer.start(self._decreaseTimer)

    def paintEvent(self, event):
        super(ScrollBar, self).paintEvent(event)

        painter = QtGui.QPainter(self)
        rect = event.rect()

        if self._isLarge:
            if self.orientation() is QtCore.Qt.Vertical:
                centerPoint = (rect.bottomRight() - self.downPixmap.rect().bottomRight()) / 2
                painter.drawPixmap(centerPoint.x(), rect.bottom()-10, self.downPixmap)

                centerPoint = (rect.bottomRight() - self.upPixmap.rect().bottomRight()) / 2
                painter.drawPixmap(centerPoint.x(), rect.top(), self.upPixmap)

            self.update()  # Prevent artefacts when painter is refeshing. (like the paint appearing elsewhere or clignotting)

        return event.accept()

    def sizeHint(self):
        return QtCore.QSize(self._width, 1)

    def _setLarge(self, isLarge):
        self._isLarge = isLarge

    def _setWidth(self, width):
        self._width = width
        self.setFixedWidth(width)


class ProcessesScrollArea(QtWidgets.QScrollArea):
    """ Scroll Area widget display and manage Process Widgets

    Manage the display and give a global control over all ProcessWidgets.
    This widget only need to have its data changed to display the new ProcessWidgets that it will create and delete when needed.
    It also give controll over all Process Widgets like check/unchek, run check/fix and filter.
    """

    feedbackMessageRequested = QtCore.Signal(str, int)  # Made to display feedback message in a statusBar. (If timeout type was of type float the message would never fade)
    progressValueChanged = QtCore.Signal(float)
    progressValueReseted = QtCore.Signal()

    STYLESHEET = \
    """
    QScrollArea
    {
        background-color: rgba(45, 45, 45, 255);
        border-width: 1px;
        border-style: solid;
        border-radius: 3px;
        border-color: transparent;
    }
    QScrollArea:Focus
    {
        border-color: rgba(93, 138, 168, 200);
    }

    ProcessesScrollAreaViewport
    {
        background-color: rgba(45, 45, 45, 255);
        border-width: 1px;
        border-style: solid;
        border-radius: 3px;
        border-color: transparent;
    }
    ProcessesScrollAreaViewport:Focus
    {
        border-color: rgba(93, 138, 168, 200);
    }

    QLabel
    {
        color: rgb(200, 200, 200);
    }
    """

    def __init__(self, register, parent=None):
        super(ProcessesScrollArea, self).__init__()  #TODO: Set the parent

        self._register = register
        self._parent = parent  #TODO: Remove this.
        self.displayMode = AtConstants.AVAILABLE_DISPLAY_MODE[0]

        self._blueprint = []
        self._processWidgets = []

        self._stopRequested = False

        self._mainLayout = QtWidgets.QVBoxLayout(self)

        self._buildUi()
        self._setupUi()
        self.setWidgetResizable(True)

    def _buildUi(self):
        """ Build the Scroll Area Widget """

        self._scrollAreaWidgetContents = ProcessesScrollAreaViewport(); self._scrollAreaWidgetContents.setObjectName('scrollAreaWidgetContents')
        self.setWidget(self._scrollAreaWidgetContents)
        self._layout = QtWidgets.QVBoxLayout(self._scrollAreaWidgetContents)

        self.setVerticalScrollBar(ScrollBar(parent=self))
        self.setHorizontalScrollBar(ScrollBar(parent=self))

        #FIXME This seems not to work with PyQt5
        # -- Fonts
        # self.noProcesses_QFont = QtGui.QFont('Candara', 20)
        # self.category_QFont = QtGui.QFont('Candara', 15)

    def _setupUi(self):
        """ Setup the ScrollArea widget """

        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self.setStyleSheet(self.STYLESHEET)

        self._layout.setSpacing(1)
        try: 
            self._layout.setMargin(0)  # Deprecated in PyQt5 But not on PySide2
        except Exception: 
            pass
        self._scrollAreaWidgetContents.setContentsMargins(2, 2, 2, 2)

    def keyPressEvent(self, event):

        if event.key() == QtCore.Qt.Key_Escape:
            self._stopRequested = True
            return event.accept()

        return super(ProcessesScrollArea, self).keyPressEvent(event)

    def refreshDisplay(self): #TODO: Maybe remove this wrapper. By renaming the addWidget.
        """ Refresh the display of the widget by removing all Widgets and rebuild the new one. """

        self._clear(self._layout, safe=True)
        self._addWidgets()
        self._showNoProcess()

    @property
    def getBlueprint(self):
        """ Getter that return value of `self._data`. """
        return self._blueprint

    # Should not work like that !!!
    def setBlueprint(self, blueprint):
        """ Setter for `self._data`.

        parameters:
        -----------
        value: dict(int: Blueprint)
            Dict containing Blueprint object to use as source for ProcessWidgets.
        """
        self._blueprint = blueprint

        #WATCHME: Is this really working ? 
        if not blueprint:
            return

        self._buildProcessWidgets()
        self._clear(self._layout, safe=not _DEV)  # In dev mode, we always delete the widget to simplify the test.

        if blueprint:
            self._addWidgets()
        else:
            self._showNoProcess()

    def _showNoProcess(self):
        """ Switch the widget display to show only a text. """

        if self._processWidgets:
            return

        self._clear(self._layout, safe=False)

        noProcesses_QLabel = QtWidgets.QLabel('No Process Available')
        noProcesses_QLabel.setAlignment(QtCore.Qt.AlignCenter)
        noProcesses_QLabel.setStyleSheet('font: 15pt;')
        # noProcesses_QLabel.setFont(self.noProcesses_QFont)
        self._layout.addWidget(noProcesses_QLabel)

    def runAllCheck(self):
        """ Execute check method on all visible processes that could be run.

        Launch each check by blueprint order if they can be launched (relative to their tags and visibility state.)
        Also update the general progress bar to display execution progress.
        """

        if not self._processWidgets:
            return

        self._stopRequested = False
        self.feedbackMessageRequested.emit('Check in progress... Press [ESCAPE] to interrupt.', 1)

        progressbarLen = 100.0/len(self._processWidgets)
        for i, processWidget in enumerate(self._processWidgets):
            if self._stopRequested:
                break

            self.progressValueChanged.emit(progressbarLen*i)

            if processWidget._isCheckable and processWidget.isChecked() and processWidget.isVisible():
                self.ensureWidgetVisible(processWidget)
                processWidget.execCheck()

        self.progressValueReseted.emit()

    def runAllFix(self):
        """ Execute fix method on all visible processes that could be run.

        Launch each fix by blueprint order if they can be launched (relative to their tags and visibility state.)
        Also update the general progress bar to display execution progress.
        """

        if not self._processWidgets:
            return

        self._stopRequested = False
        self.feedbackMessageRequested.emit('Fix in progress... Press [ESCAPE] to interrupt.', 1)

        progressbarLen = 100.0/len(self._processWidgets)
        for i, processWidget in enumerate(self._processWidgets):
            if self._stopRequested:
                break

            self.progressValueChanged.emit(progressbarLen*i)

            # Skip processes with no error or that are in exception.
            if not isinstance(processWidget.status, AtCore.Status.FailStatus):
                continue

            if processWidget._isFixable and processWidget.isChecked() and processWidget.isVisible():
                self.ensureWidgetVisible(processWidget)
                processWidget.execFix()

        self.progressValueReseted.emit()

    def _buildProcessWidgets(self):
        """" Create the new widget and setup them.

        Build the process widgets from blueprint list and setup them (resolve links with process methods.)
        """
        self._processWidgets = processWidgets = []
        if not _DEV:
            # I use `list.extend` because if I don't and assign it to the result of `filter`, processWidgets
            # will point to another list than the instance attribute and the result will become unpredictable.
            processWidgets.extend(filter(None, (processor.getData('widget') for processor in self._blueprint.processors)))
            if processWidgets:
                return  # There is already widgets in the register

        uiLinkResolve = {}
        for id_, processor in zip(self._blueprint.header, self._blueprint.processors):
            if not processor.inUi:
                continue

            processWidget = ProcessWidget(processor, doProfiling=_DEV, parent=self)

            processWidgets.append(processWidget)
            uiLinkResolve[id_] = processWidget if processor.inUi else None
            processor.setData('widget', processWidget)

        for processor in self._blueprint.processors:
            processor.resolveLinks(uiLinkResolve, check='execCheck', fix='execFix', tool='execTool')

    # Could be property (get/set) named displayMode
    def _addWidgets(self):
        """ Fallback on all display mode to launch the corresponding `addWidget` method. """

        mode = self.displayMode

        if mode == AtConstants.AVAILABLE_DISPLAY_MODE[0]:
            self._addWidgetsByHeader()
        elif mode == AtConstants.AVAILABLE_DISPLAY_MODE[1]:
            self._addWidgetsByCategory()
        elif mode == AtConstants.AVAILABLE_DISPLAY_MODE[2]:
            self._addWidgetsAlphabetically()

        for widget in self._processWidgets:
            widget.leaveEvent(None)

    def _addWidgetsByHeader(self):
        """ Add widget in the scroll area by Blueprint order (default) """

        for process in self._processWidgets:
            self._layout.addWidget(process)

        self._layout.addStretch()

    def _addWidgetsByCategory(self):
        """ Add widgets in the scroll area by Category Order (Also add Label for category) """

        categories = []
        orderedByCategory = {}
        for process in self._processWidgets:
            category = process._category

            if category not in categories:
                categories.append(category)
                orderedByCategory[category] = []
            orderedByCategory[category].append(process)

        #TODO: Implement or remove this
        # categories.sort()

        for category in categories:
            processWidgets = orderedByCategory[category]

            category_QLabel = QtWidgets.QLabel('{0}'.format(category))
            category_QLabel.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom)
            category_QLabel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
            category_QLabel.setStyleSheet('font: 11pt; font-weight: bold')
            self._layout.addWidget(category_QLabel)

            for processWidget in processWidgets:
                self._layout.addWidget(processWidget)

        self._layout.addStretch()

    def _addWidgetsAlphabetically(self):
        """ Add widget in the scroll area by Blueprint order (default) """

        for processWidget in sorted(self._processWidgets, key=lambda proc: proc._name):
            self._layout.addWidget(processWidget)

        self._layout.addStretch()

    def checkAll(self):
        """ Check all Process Widget in the scroll area """

        for processWidget in self._processWidgets:
            processWidget.setChecked(True)

    def uncheckAll(self):
        """ Uncheck all Process Widget in the scroll area """

        for processWidget in self._processWidgets:
            processWidget.setChecked(False)

    def defaultAll(self):
        """ Reset all Process Widget check state in the scroll area """

        for processWidget in self._processWidgets:
            processWidget.setChecked(processWidget._blueprint.isEnabled)

    def openAll(self):
        for processWidget in self._processWidgets:
            processWidget.openDisplayWidget()

    def closeAll(self):
        for processWidget in self._processWidgets:
            processWidget.closeDisplayWidget()

    def filterProcesses(self, text):
        """ Allow to filter the list of processes by hiding those who didn't match with the given string string.

        parameters:
        -----------
        text: str
            Text used to filter processes in the area.
        """

        #WIP: This function should not receive text but SearchPattern
        if not text:
            # self.feedbackMessageRequested.emit('{} processes available'.format(len(self._processWidgets)), 3000)
            for processWidget in self._processWidgets:
                processWidget.setVisible(True)
            return

        searchPattern = AtUtils.SearchPattern(text)
        hashTags = set(searchPattern.iterHashTags())

        allowedStatus = set(filter(None, (AtCore.Status.getStatusByName(statusName) for statusName in hashTags)))
        for processWidget in self._processWidgets:
            processWidget.setVisible(all((
                bool(searchPattern.search(processWidget._name)),  # Check if the str match the user regular expression.
                processWidget._status in allowedStatus if hashTags else True  # Check if the processWidget is of a filtered Status.
            )))

        visibleProcesses = [processWidget for processWidget in self._processWidgets if processWidget.isVisible()]

    def _clear(self, layout, safe=False):
        """ Clear all items in the layout

        Delete all widgets in the area to allow replacing them by another ones.
        Will delete Widgets, Spacers and Layouts.

        parameters:
        -----------
        layout: QtWidgets.QLayout
            The layout to clear all childs.
        safe: bool
            Preserve Process Widgets from being removed.
        """

        for i in reversed(range(layout.count())):
            layoutItem = layout.itemAt(i)

            if layoutItem.widget() is not None:
                widgetToRemove = layoutItem.widget()
                if safe and isinstance(widgetToRemove, ProcessWidget):
                    widgetToRemove.setParent(None)
                    layout.removeWidget(widgetToRemove)  #FIXME: It seems that in normal mode widget lose their color (not reset)
                    continue
                widgetToRemove.deleteLater()
                del widgetToRemove

            elif layoutItem.spacerItem() is not None:
                spacerToRemove = layoutItem.spacerItem()
                layout.removeItem(spacerToRemove)
                del spacerToRemove

            else:
                self._clear(layoutItem, safe=safe)
                layoutItem.deleteLater()
                del layoutItem


class ProcessesScrollAreaViewport(QtWidgets.QWidget):

    def __init__(self):
        super(ProcessesScrollAreaViewport, self).__init__()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        logoPixmap = QtGui.QPixmap()
        if logoPixmap.load(r'C:/Workspace/Athena/src/Athena/ressources/icons/test.png'):
            logoPixmap = logoPixmap.scaled(QtCore.QSize(125, 125), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Multiply)

            centerPoint = (event.rect().bottomRight() - logoPixmap.rect().bottomRight()) / 2
            painter.drawPixmap(centerPoint, logoPixmap)

        self.update()

        return super(ProcessesScrollAreaViewport, self).paintEvent(event)


######################################################################################################################################


class BlockSignals():
    """ Block signals of the given widgets for all instructions under the with statement. """

    def __init__(self, widgets, block=True):
        """ Init the Context attribute.

        parameters:
        -----------
        widgets: list(QtWidgets.QWidget, ...)
            List of all widget on which block signals.
        block: bool
            If True, all signals will be blocked, else, all signal will be activated.
        """

        self._widgets = widgets
        self._block = block

        self._defaultStates = {}

    def __enter__(self):
        for widget in self._widgets:
            self._defaultStates[widget] = widget.blockSignals(self._block)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for widget, state in self._defaultStates.items():
            widget.blockSignals(state)


class BusyCursor():
    """ Change the cursor type during execution of the instruction under the context statement. """

    def __enter__(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

    def __exit__(self, exception_type, exception_value, traceback):
        QtWidgets.QApplication.restoreOverrideCursor()


# Next functions as static method of a new class
def getParentApplication():
    """ Allow to get the parent Application widget relative to where the code is executed. """

    parentWindow = QtCore.QCoreApplication.instance()

    if not parentWindow:
        return None

    topWidgets = QtCore.QCoreApplication.instance().topLevelWidgets()
    topWidgets = [widget for widget in topWidgets
                   if widget.isVisible() 
                   and widget.parent() is None 
                   and isinstance(widget, QtWidgets.QWidget)]

    # If there is no top widget, the tool is standalone
    if not topWidgets:
        return None

    for widget in topWidgets:
        if widget.objectName().lower() == 'mainwindow' or widget.windowIconText():
            return widget
        elif widget.metaObject().className().lower() == 'foundry::ui::dockmainwindow':
            return widget

    return None


def getSizeFromScreen():
    """ Get the Width and Height of the Window relative to a 16:9 Scale """

    screenRect = QtWidgets.QApplication.desktop().screenGeometry()
    return ((screenRect.width()*450)/2560, (screenRect.height()*900)/1440)













if __name__ == '__main__':
    
    app = QtWidgets.QApplication(sys.argv)
    _DEV = True

    register = AtCore.Register()
    register.loadBlueprintsFromPackageStr('Athena.ressources.examples.Athena_Standalone')

    win = AthenaWidget(register=register, displayMode='Category')
    win.show()

    sys.exit(app.exec_())



'''
from gpdev.tools.Athena import ui
reload(ui)

app = ui.Athena()
'''

"""
.addSHortcut('Ctrl+Q')
"""

# Delete all ui 
"""
from PySide2 import QtWidgets

app = QtWidgets.QApplication.instance()
print('\n'.join(repr(w) for w in app.allWidgets() if 'gpdev' in repr(w)))

for w in app.allWidgets():
    if 'gpdev' in repr(w):
        #print 'Delete ' + w.objectName()
        w.deleteLater()
"""