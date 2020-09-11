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

#WATCHME: Dev Import
from pprint import pprint

_DEV = False
_USE_ATHENA_STYLESHEET = True


#WATCHME: CSS : QCssParser::parseColorValue: Specified color without alpha value but alpha given: 'rgb 255, 255, 255, 25'

class SettingsManager(object):

    __SETTINGS = QtCore.QSettings(AtConstants.PROGRAM_NAME, QtCore.QSettings.IniFormat)

    __GETTER_METHODS = {}

    @classmethod
    def getSettings(cls):
        return cls.__SETTINGS

    @classmethod
    def loadSetting(cls, setting, default=None, type=str, getter=None):
        if getter is not None and callable(getter):
            cls.__GETTER_METHODS[setting] = getter
        return type(cls.__SETTINGS.value(setting, defaultValue=default))

    @classmethod
    def saveSettings(cls):
        for setting, getter in cls.__GETTER_METHODS.items():
            cls.__SETTINGS.setValue(setting, getter())

class AthenaWidget(QtWidgets.QWidget):
    """Main ui for Athena, it offer all possible features available from The API and is Available on multiple softwares.

    The Athena is a tool made to execute conformity processes to check/fix errors based on the current software or OS, 
    it read the loaded python packages to find all thoses who follow the implemented convention. 
    In theses packages it will find all contexts and by parsing the module it will load all envs from the right software. 
    Theses modules will be loaded and the blueprint retrieved from the `blueprints` variable in it.

    All checks have to inherit from the Process class from Athena.AtCore, they can be overrided on blueprint level using
    arguments, tags and/or links.

    Notes
    -----
    Except for develloping, you should better run the tool using the `launch()` function from the main module. `Athena.launch()`

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

    def __init__(self, context=None, env=None, displayMode=AtConstants.AVAILABLE_DISPLAY_MODE[0], dev=False, verbose=False, parent=None):
        """ Initialise the Athena tool by loading ressources, getting register and all other data for ui.

        Parameters
        ----------
        context: str, optional
            Context name to setup at launch. If it does not exist, fallback to first context of the list. (default: None)
        env: str, optional
            Env to setup at default. If it does not exist, fallback to first env of the current context. (default: None)
        displayMode: str, optional
            Setup the blueprint's display mode at launch (default: 'blueprint')
        mode: str, optional
            Define the mode used to launch the tool ang give different access to some options. (default: 'user')
        verbose: bool
            Should the tool print informations about its execution. (default: False)
        """

        super(AthenaWidget, self).__init__(parent)

        self.setWindowFlags(QtCore.Qt.Window)

        self._register = AtCore.Register(verbose=verbose)
        self._resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)
        self._defaultDisplayMode = displayMode if displayMode in AtConstants.AVAILABLE_DISPLAY_MODE else AtConstants.AVAILABLE_DISPLAY_MODE[0]
        
        global _DEV
        _DEV = dev

        self._verbose = verbose
        self._configuration = {'context': context, 'env': env}
        
        # Build, Setup and connect the ui
        self._buildUi()
        self._setupUi()
        self._connectUi()

        # self._setupContext()
        self.reload()

        self.resize(
            SettingsManager.loadSetting('width', default=400, type=int, getter=self.width), 
            SettingsManager.loadSetting('height', default=800, type=int, getter=self.height)
        )
        self.setWindowTitle('{0} - {1}'.format(AtConstants.PROGRAM_NAME, self._register.software.capitalize()))
        self.setWindowIcon(self._resourcesManager.get('logo.png', AtConstants.PROGRAM_NAME, QtGui.QIcon))  #TODO: Find a logo and add it here.

        # This will prevent the window to leave foreground on OSX
        self.setProperty("saveWindowPref", True)

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
        if _DEV:
            self._dev_QMenu = self._menuBar.addMenu('Dev')
        self._help_QMenu = self._menuBar.addMenu('Help')

        self._mainLayout.addWidget(self._menuBar)

        # -- Options Menu
        # self._option_QMenu.addSection('Enable Processes')

        self._checkAll_QAction = QtWidgets.QAction(self._resourcesManager.get('setEnabled.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Enable All Processes', self._option_QMenu)
        self._option_QMenu.addAction(self._checkAll_QAction)
        self._uncheckAll_QAction = QtWidgets.QAction(self._resourcesManager.get('setDisabled.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Disable All Processes', self._option_QMenu)
        self._option_QMenu.addAction(self._uncheckAll_QAction)
        self._defaultAll_QAction = QtWidgets.QAction(self._resourcesManager.get('setDefault.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Reset All Processes', self._option_QMenu)
        self._option_QMenu.addAction(self._defaultAll_QAction)

        # self._option_QMenu.addSection('Process Ordering')
        self._orderBy_QMenu = self._option_QMenu.addMenu(self._resourcesManager.get('order.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Order By')

        self._orderByBlueprint_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[0], self._orderBy_QMenu)
        self._orderBy_QMenu.addAction(self._orderByBlueprint_QAction)
        self._orderByCategory_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[1], self._orderBy_QMenu)
        self._orderBy_QMenu.addAction(self._orderByCategory_QAction)
        self._orderAlphabetically_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[2], self._orderBy_QMenu)
        self._orderBy_QMenu.addAction(self._orderAlphabetically_QAction)

        self._orderBy = orderBy = QtWidgets.QActionGroup(self._orderBy_QMenu)
        orderBy.addAction(self._orderByBlueprint_QAction)
        orderBy.addAction(self._orderByCategory_QAction)
        orderBy.addAction(self._orderAlphabetically_QAction)

        # -- Register Menu
        # self.currentModule_QAction = QtWidgets.QAction('', self._register_QMenu)
        # self.currentModule_QAction.setEnabled(False)

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

        # Dev Menu
        if _DEV:
            self.reloadBlueprints_QAction = QtWidgets.QAction(self._resourcesManager.get('reload.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "Reload Blueprints", self._dev_QMenu)
            self._dev_QMenu.addAction(self.reloadBlueprints_QAction)

            self._documentation_QAction = QtWidgets.QAction(self._resourcesManager.get('documentation.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "[Placeholder] Techical Documentation", self._help_QMenu)
            self._dev_QMenu.addAction(self._documentation_QAction)

        # -- Context & Environment Toolbar
        self._toolbar = QtWidgets.QToolBar()

        self._contexts_QComboBox = QtWidgets.QComboBox(self); self._contexts_QComboBox.setObjectName('contexts_QComboBox')
        self._toolbar.addWidget(self._contexts_QComboBox)

        self._envs_QComboBox = QtWidgets.QComboBox(self); self._envs_QComboBox.setObjectName('envs_QComboBox')
        self._toolbar.addWidget(self._envs_QComboBox)

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

        # -- Statusbar
        # self._version_Qlabel = QtWidgets.QLabel(AtConstants.VERSION)
        # self.statusBar().addPermanentWidget(self._version_Qlabel)

        self._mainLayout.addLayout(self._subLayout)

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

        self.setDisplayMode()
        
        self._orderBy.setExclusive(True)

        # -- Action Toolbar
        self._toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._toolbar.setIconSize(QtCore.QSize(15, 15))

        # -- Setup contexts, the env will be dinamically set according to the data stored in env. (see connectUi)
        self._setupContext()

        # -- Shortcuts
        self.runAllCheck_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_C), self)
        self.runAllFix_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_F), self)
        self.reloadBlueprintsModules_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_R), self)

        # -- Search and progress bar
        self._searchAndProgressBar.searchBar.setPlaceholderText('Filter Processes...')

    def _connectUi(self):
        """ Connect all widgets to their methods """

        # -- Options Menu
        self._checkAll_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.checkAll)
        self._uncheckAll_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.uncheckAll)
        self._defaultAll_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.defaultAll)

        self._orderBy.triggered.connect(self.setDisplayMode, QtCore.Qt.UniqueConnection)

        self._contexts_QComboBox.currentIndexChanged.connect(self._setupEnvs, QtCore.Qt.UniqueConnection)
        self._contexts_QComboBox.currentIndexChanged.emit(self._contexts_QComboBox.currentIndex())
        
        self._envs_QComboBox.currentIndexChanged.connect(self.reload, QtCore.Qt.UniqueConnection)

        self._runAllCheck_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.runAllCheck, QtCore.Qt.UniqueConnection)
        self._runAllFix_QAction.triggered.connect(self._processWidgets_ProcessesScrollArea.runAllFix, QtCore.Qt.UniqueConnection)

        # -- Help Menu
        self._openWiki_QAction.triggered.connect(partial(QtGui.QDesktopServices.openUrl, AtConstants.WIKI_LINK), QtCore.Qt.UniqueConnection)
        self._reportBug_QAction.triggered.connect(partial(QtGui.QDesktopServices.openUrl, AtConstants.REPORT_BUG_LINK), QtCore.Qt.UniqueConnection)

        # -- Dev Menu
        if _DEV:
            self.reloadBlueprints_QAction.triggered.connect(self.reloadBlueprintsModules, QtCore.Qt.UniqueConnection)
            self._documentation_QAction.triggered.connect(partial(QtGui.QDesktopServices.openUrl, AtConstants.WIKI_LINK), QtCore.Qt.UniqueConnection)

        # -- Search and progress bar
        self._searchAndProgressBar.searchBar.textChanged.connect(self._processWidgets_ProcessesScrollArea.filterProcesses, QtCore.Qt.UniqueConnection)

        # -- Shortcuts
        self.runAllCheck_QShortcut.activated.connect(self._processWidgets_ProcessesScrollArea.runAllCheck)
        self.runAllFix_QShortcut.activated.connect(self._processWidgets_ProcessesScrollArea.runAllFix)
        self.reloadBlueprintsModules_QShortcut.activated.connect(self.reloadBlueprintsModules)

        # -- Processes Scroll Area
        # self._processWidgets_ProcessesScrollArea.feedbackMessageRequested.connect(self.statusBar().showMessage)
        self._processWidgets_ProcessesScrollArea.progressValueChanged.connect(self._searchAndProgressBar.setValue)
        self._processWidgets_ProcessesScrollArea.progressValueReseted.connect(self._searchAndProgressBar.reset)

    def closeEvent(self, event):
        """Call when the ui is about to close, allow to close the ui.

        If the ui can be close (`action_Qtoolbar` not detached) the window will be deleted.
        Else, the ui will only be hidden.

        parameters:
        -----------
        event: QCloseEvent
            Close event given by Qt to this method.
        """

        SettingsManager.saveSettings()
        self.deleteLater()
        return super(AthenaWidget, self).closeEvent(event)

    def reload(self):
        """ Reload the current blueprints and set the data of the scroll area. """

        with BusyCursor():
            self._processWidgets_ProcessesScrollArea.setBlueprints(self.getBlueprints())

            # Restore the current filter to hidde checks that does not match the search.
            self._searchAndProgressBar.searchBar.textChanged.emit(self._searchAndProgressBar.searchBar.text())

    def reloadBlueprintsModules(self):
        """ Reload the current blueprints.

        notes:
        ------
            Usefull for devellopement purposes, allow to reload the processes classes without breaking the pointers.
        """
        self._register.reload()
        self._setupContext()

        self.reload()
        self.statusBar().showMessage('Successfully reload blueprint\'s modules for env `{0}`.'.format(self._envs_QComboBox.currentText()), 5000)

    def _setupContext(self):
        """ Switch the current context used by the tool. """
        register = self._register

        with BusyCursor(), BlockSignals([self._contexts_QComboBox], block=True):
            contexts_QComboBox = self._contexts_QComboBox

            # Get the current text before clearing the QComboBox and populate it with the right data.
            currentContext = contexts_QComboBox.currentText()
            contexts_QComboBox.clear()

            for context in register._contexts:
                contexts_QComboBox.addItem(QtGui.QIcon(context.iconPath), context._name, context)

            # Fallback 1: If there is a value in the QComboBox before, switch on the same value for the new context if exists
            currentIndex = contexts_QComboBox.findText(currentContext)
            if currentIndex > -1:
                contexts_QComboBox.setCurrentIndex(currentIndex)

            # Fallback 2: If a default value have been given at init, switch to this value.
            else:
                defaultText = self._configuration['context']
                if defaultText is not None:
                    defaultIndex = contexts_QComboBox.findText(defaultText)
                    if defaultIndex > -1:
                        contexts_QComboBox.setCurrentIndex(defaultIndex)
                    else: 
                        contexts_QComboBox.setCurrentIndex(0)

        self._contexts_QComboBox.currentIndexChanged.emit(self._contexts_QComboBox.currentIndex())

    def _setupEnvs(self, index):
        """ Setup the current env for the tool to display processes.

        parameters:
        -----------
        index: int
            The current index of the `envs_QComboBox` widget.
        
        notes:
        ------
            If the method is called after context changed and current env also exist in the new context, it will stay on the same env.
        """
        register = self._register

        with BusyCursor(), BlockSignals([self._envs_QComboBox], block=True):
            # Catch a possible error, if signal give -1 there is an error
            if index == -1: 
                return

            envs_QComboBox = self._envs_QComboBox

            # Get the context from contexts_QComboBox index given by signal
            context = self._contexts_QComboBox.itemData(index, QtCore.Qt.UserRole)
            if not context: 
                return

            # Get the current text before clearing the QComboBox and populate it with the right data.
            currentEnv = envs_QComboBox.currentText()
            envs_QComboBox.clear()

            for env in context.envs:
                envs_QComboBox.addItem(QtGui.QIcon(env.iconPath), env._name, env)

            # Fallback 1: If there is a value in the QComboBox before, switch on the same value for the new context if exists
            currentIndex = envs_QComboBox.findText(currentEnv)
            if currentIndex > -1 and currentIndex <= envs_QComboBox.count():
                envs_QComboBox.setCurrentIndex(currentIndex)

            # Fallback 2: If a default value have been given at init, switch to this value.
            else:
                defaultText = self._configuration['env']
                if defaultText is not None:
                    defaultIndex = envs_QComboBox.findText(defaultText)
                    if defaultIndex > -1:
                        envs_QComboBox.setCurrentIndex(defaultIndex)
                    else: 
                        envs_QComboBox.setCurrentIndex(0)

        self._envs_QComboBox.currentIndexChanged.emit(self._envs_QComboBox.currentIndex())

    def setDisplayMode(self):
        """ Change the current display mode of the scroll area widget. """

        self._processWidgets_ProcessesScrollArea.displayMode = self._orderBy.checkedAction().text()
        self._processWidgets_ProcessesScrollArea.refreshDisplay()

    def getBlueprints(self):
        """ Get the blueprint from the register from current context and env. """
        envData = self._envs_QComboBox.itemData(self._envs_QComboBox.currentIndex(), QtCore.Qt.UserRole)
        return None if not envData else envData.blueprints


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

    def __init__(self, blueprint, parent=None):
        """ Initialise the Process widget from a blueprint.

        parameters:
        -----------
        blueprint: QaulityCheck.AtCore.Blueprint
            A Athena Blueprint that will be drived through ui.
        parent: QWidget
            The QWidget parent of this widget.
        """ 

        super(ProcessWidget, self).__init__(parent)

        self._resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)
        
        self._blueprint = blueprint
        self._settings = blueprint._settings
        self._name = blueprint._name
        self._docstring = blueprint._docstring
        self._isEnabled = blueprint._isEnabled
        self._isCheckable = blueprint._isCheckable
        self._isFixable = blueprint._isFixable
        self._hasTool = blueprint._hasTool
        self._isNonBlocking = blueprint._isNonBlocking

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
        self._name_QLabel.clicked.connect(self.toggleTraceback)

        # -- Tool PushButton
        self._tool_QPushButton.clicked.connect(self.execTool)

        # -- Fix PushButton
        self._fix_QPushButton.clicked.connect(self.execFix)

        # -- Check PushButton
        self._check_QPushButton.clicked.connect(self.execCheck)

        # -- Profiler PushButton
        if _DEV:
            self._profiler_QPushButton.clicked.connect(self._openTraceback)
            self._profiler_QPushButton.clicked.connect(partial(self._processDisplay.logProfiler, ''))

        # -- Connect the progressbar to the process _progressbar attribute.
        self._blueprint.setProgressbar(self._progressbar_QProgressBar)

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
            self.toggleTraceback()
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
            self.closeTraceback()
            return

        if isinstance(feedback, list) and isinstance(feedback[0], AtCore.Feedback):
            self._processDisplay.logFeedback(feedback)
        elif isinstance(feedback, Exception):
            self._processDisplay.logTraceback(feedback)
        else:
            raise NotImplementedErrror('Data to log are not implemented yet.')

        self.openTraceback()

    def toggleTraceback(self):
        """Switch visibility of the traceback widget. """

        if not self._isOpened:
            self.openTraceback()
        else:
            self.closeTraceback()
            
    def _openTraceback(self):
        """ Show the traceback widget and change the displayed arrow shape. """

        self._name_QLabel.setIcon(self._resourcesManager.get('bottom-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon))
        self._isOpened = True
        self._updateHeight(self._processDisplay.sizeHint())

        self._processDisplay.setVisible(self._isOpened)

    def openTraceback(self):
        """ Show the traceback widget and change the displayed arrow shape. """

        if not self.feedback:
            return
        self._openTraceback()

    def closeTraceback(self):
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

        with self.__ExecContext(self), BusyCursor():
            try:
                result, status = self._blueprint.check()

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

    def execFix(self):
        """ Run the `fix` method of the Blueprint's Process.

        Exec the Process `fix` method and handle any Exception to switch the ProcessWidget state to 'Exception' and log the 
        Exception's feedback in it.
        Then, launch the `execCheck` method to catch any other error to update the ProcessWidget.
        """

        with self.__ExecContext(self), BusyCursor():
            try:
                result, status = self._blueprint.fix()

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

        with self.__ExecContext(self), BusyCursor():
            try:
                result = self._blueprint.tool()
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

        def __exit__(self, exception_type, exception_value, traceback):
            
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
            header = self.header()
            headerSizeHint = header.sizeHint()
            height += headerSizeHint.height()
        rows = 0
        it = QtWidgets.QTreeWidgetItemIterator(self)
        while it.value() is not None:
            rows += 1
            index = self.indexFromItem(it.value())
            height += self.rowHeight(index)
            it += 1

        # We always include the height of the horizontalScrollBar to be sure it will not hide a feedback.
        height += self.horizontalScrollBar().height()

        newSizeHint = QtCore.QSize(sizeHint.width(), height + 5)  # +5 is a fixed offset to add some free space under the latest feedback.
        return newSizeHint

    def minimumSizeHint(self):
        return self.sizeHint()

class FeedbackWidget(_AbstractLogTreeWidget):

    sizeChanged = QtCore.Signal(QtCore.QSize)

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

            if feedback.hasFeedback():
                parent = QtWidgets.QTreeWidgetItem([str(feedback._thread._title), '        found {0}'.format(str(len(feedback._toDisplay)))])
                # parent.setForeground(1, QtGui.QColor(*thread._status._color))  # Color the number of issue with the status color.
                parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
            else:
                parent = QtWidgets.QTreeWidgetItem([str(feedback._thread._title)])
                parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.DontShowIndicator)

            # If there is a documentation for this error display it in a tooltip.
            if thread._documentation is not None:
                parent.setToolTip(0, thread._documentation)

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

            for toDisplay, toSelect in feedback.iterItems():
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

    def logProfiler(self, profiler):
        pass

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
        self._feedbackWidget.sizeChanged.connect(self._updateHeight)

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

        # -- Setup Profiler Widget
        self._profilerWidget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

    def displayFeedback(self):
        self._mainLayout.setCurrentWidget(self._feedbackWidget)

        self.updateGeometry()

    def displayTracebak(self):        
        # This will lazilly load the tracebackWidget, it will create it if it has been requested.
        if self._tracebackWidget is None:
            self._addTracebackWidget()
        self._mainLayout.setCurrentWidget(self._tracebackWidget)

        self.updateGeometry()

    def displayProfiler(self):
        # This will lazilly load the profilerWidget, it will create it if it has been requested.
        if self._profilerWidget is None:
            self._addProfilerWidget()
        self._mainLayout.setCurrentWidget(self._profilerWidget)

        self.updateGeometry()

    def logFeedback(self, feedbacks):
        self.displayFeedback()
        self._feedbackWidget.logFeedback(feedbacks)

    def logTraceback(self, traceback):
        self.displayTracebak()
        self._tracebackWidget.logTraceback(traceback)

    def logProfiler(self, profiler):
        self.displayProfiler()
        self._profilerWidget.logProfiler(profiler)


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
        super(ProcessesScrollArea, self).__init__()

        self._register = register
        self._parent = parent
        self.displayMode = AtConstants.AVAILABLE_DISPLAY_MODE[0]

        self._blueprints = []
        self._processWidgets = []

        self._stopRequested = False

        self._mainLayout = QtWidgets.QVBoxLayout(self)

        self._buildUi()
        self._setupUi()
        self.setWidgetResizable(True)

        # self._showNoProcess()
        # self.viewport().update()

    def _buildUi(self):
        """ Build the Scroll Area Widget """

        self._scrollAreaWidgetContents = ProcessesScrollAreaViewport(); self._scrollAreaWidgetContents.setObjectName('scrollAreaWidgetContents')
        self.setWidget(self._scrollAreaWidgetContents)
        self._layout = QtWidgets.QVBoxLayout(self._scrollAreaWidgetContents)

        #FIXME This seems not to work with PyQt5
        # -- Fonts
        # self.noProcesses_QFont = QtGui.QFont('Candara', 20)
        # self.category_QFont = QtGui.QFont('Candara', 15)

    def _setupUi(self):
        """ Setup the ScrollArea widget """

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
    def getBlueprints(self):
        """ Getter that return value of `self._data`. """
        return self._blueprints

    # Should not work like that !!!
    def setBlueprints(self, blueprints):
        """ Setter for `self._data`.

        parameters:
        -----------
        value: dict(int: Blueprint)
            Dict containing Blueprint object to use as source for ProcessWidgets.
        """
        
        self._blueprints = blueprints

        #WATCHME: Is this really working ? 
        if not blueprints:
            return

        self._buildProcessWidgets()
        self._clear(self._layout, safe=not _DEV)  # In dev mode, we always delete the widget to simplify the test.

        if blueprints:
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
        for i, process in enumerate(self._processWidgets):
            if self._stopRequested:
                break

            self.progressValueChanged.emit(progressbarLen*i)

            if process._blueprint._isCheckable and process.isChecked() and (process.isVisible() or not self._parent._canClose):
                self.ensureWidgetVisible(process)
                process.execCheck()

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
        for i, process in enumerate(self._processWidgets):
            if self._stopRequested:
                break

            self.progressValueChanged.emit(progressbarLen*i)

            # Skip processes with no error or that are in exception.
            if not isinstance(process.status, AtCore.Status.FailStatus):
                continue

            if process._isFixable and process.isChecked() and (process.isVisible() or not self._parent.canClose):
                self.ensureWidgetVisible(process)
                process.execFix()

        self.progressValueReseted.emit()

    def _buildProcessWidgets(self):
        """" Create the new widget and setup them.

        Build the process widgets from blueprint list and setup them (resolve links with process methods.)
        """
        self._processWidgets = processWidgets = []
        if not _DEV:
            # I use `list.extend` because if I don't and assign it to the result of `filter`, processWidgets
            # will point to another list than the instance attribute and the result will become unpredictable.
            processWidgets.extend(filter(None, (blueprint.getData('widget') for blueprint in self._blueprints)))
            if processWidgets:
                return  # There is already widgets in the register

        uiLinkResolveBlueprints = []
        for blueprint in self._blueprints:
            if not blueprint._inUi:
                uiLinkResolveBlueprints.append(None)
                continue  # Skip this check if it does not be run in ui
            processWidget = ProcessWidget(blueprint, parent=self)

            processWidgets.append(processWidget)
            uiLinkResolveBlueprints.append(processWidget)
            blueprint.setData('widget', processWidget)

        for blueprint in self._blueprints:
            blueprint.resolveLinks(uiLinkResolveBlueprints, check='execCheck', fix='execFix', tool='execTool')

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
            category = process._blueprint.category

            if category not in categories:
                categories.append(category)
                orderedByCategory[category] = []
            orderedByCategory[category].append(process)

        #TODO: Implement or remove this
        # categories.sort()

        for category in categories:
            processes = orderedByCategory[category]

            category_QLabel = QtWidgets.QLabel('{0}'.format(category))
            category_QLabel.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom)
            category_QLabel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
            category_QLabel.setStyleSheet('font: 11pt; font-weight: bold')
            self._layout.addWidget(category_QLabel)

            for process in processes:
                self._layout.addWidget(process)

        self._layout.addStretch()

    def _addWidgetsAlphabetically(self):
        """ Add widget in the scroll area by Blueprint order (default) """

        for process in sorted(self._processWidgets, key=lambda proc: proc._blueprint._name):
            self._layout.addWidget(process)

        self._layout.addStretch()

    def checkAll(self):
        """ Check all Process Widget in the scroll area """

        for process in self._processWidgets:
            process.setChecked(True)

    def uncheckAll(self):
        """ Uncheck all Process Widget in the scroll area """

        for process in self._processWidgets:
            process.setChecked(False)

    def defaultAll(self):
        """ Reset all Process Widget check state in the scroll area """

        for process in self._processWidgets:
            process.setChecked(process._blueprint.isEnabled)

    def filterProcesses(self, text):
        """ Allow to filter the list of processes by hiding those who didn't match with the given string string.

        parameters:
        -----------
        text: str
            Text used to filter processes in the area.
        """

        #WIP: This function should not receive text but SearchPattern
        if not text:
            self.feedbackMessageRequested.emit('{} processes available'.format(len(self._processWidgets)), 3000)
            for process in self._processWidgets:
                process.setVisible(True)
            return

        searchPattern = AtUtils.SearchPattern(text)
        hashTags = set(searchPattern.iterHashTags(text))

        allowedStatus = set(filter(None, (AtCore.Status.getStatusByName(statusName) for statusName in hashTags)))
        for process in self._processWidgets:
            process.setVisible(all((
                bool(searchPattern.search(process._blueprint._name)),  # Check if the str match the user regular expression.
                process._status in allowedStatus if hashTags else True  # Check if the process are of a filtered Status.
            )))

        visibleProcesses = [process for process in self._processWidgets if process.isVisible()]
        if not visibleProcesses:
            self.feedbackMessageRequested.emit('No process match pattern "{}"'.format(searchPattern.pattern), 3000)
        else:
            self.feedbackMessageRequested.emit('Found {} processes that match name "{}"'.format(len(visibleProcesses), searchPattern.pattern), 3000)

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
            logoPixmap = logoPixmap.scaled(QtCore.QSize(125, 125), QtCore.Qt.KeepAspectRatio)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Multiply)

            centerPoint = (event.rect().bottomRight() - logoPixmap.rect().bottomRight()) / 2
            painter.drawPixmap(centerPoint, logoPixmap)

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

    rec = QtWidgets.QApplication.desktop().screenGeometry()
    
    width = rec.width()
    height = rec.height()
    
    return ((width*450)/2560, (height*900)/1440)













if __name__ == '__main__':
    
    app = QtWidgets.QApplication(sys.argv)
    win = AthenaWidget(dev=True)
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