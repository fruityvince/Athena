from Athena import AtCore, AtUtils, AtConstants

from functools import partial

import os
import sys
import random
import string
import traceback
import webbrowser

# Use PySide2 or PyQt5.
try: from PySide2 import QtCore, QtGui, QtWidgets
except: from PyQt5 import QtCore, QtGui, QtWidgets
finally: __QTBINDING__ = QtCore.__name__.partition('.')[0]


class Athena(QtWidgets.QMainWindow):
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

    def __init__(self, context=None, env=None, displayMode=AtConstants.AVAILABLE_DISPLAY_MODE[0], dev=False, verbose=False):
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

        self.parentApplication = getParentApplication()
        super(Athena, self).__init__(self.parentApplication)

        self.register = AtCore.Register(verbose=verbose)
        self.resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)
        self.software = self.register.software
        self.defaultDisplayMode = displayMode if displayMode in AtConstants.AVAILABLE_DISPLAY_MODE else AtConstants.AVAILABLE_DISPLAY_MODE[0]
        self.dev = dev
        self.blueprints = {}

        self.verbose = verbose
        self.configuration = {'context': context, 'env': env}

        self.canClose = True
        
        self.statusBar = self.statusBar()

        # Build, Setup and connect the ui
        self.buildUi()
        self.setupUi()
        self.connectUi()

        self.setup_context()

        self.resize(400, 800)
        self.setWindowTitle('{0} - {1}'.format(AtConstants.PROGRAM_NAME, self.software.capitalize()))
        self.setWindowIcon(self.resourcesManager.get('logo.png', AtConstants.PROGRAM_NAME, QtGui.QIcon))  #TODO: Find a logo and add it here.

        self.setProperty("saveWindowPref", True)  # This will prevent the window to leave foreground on OSX

    def buildUi(self):
        """ Create all widgets and layout for the ui """

        # -- Central Widget
        self.centralWidget = QtWidgets.QWidget()
        self.mainLayout = QtWidgets.QVBoxLayout(self.centralWidget)
        self.setCentralWidget(self.centralWidget)

        # -- MenuBar
        self.menu = self.menuBar()
        self.option_QMenu = self.menu.addMenu('Options')
        self.register_QMenu = self.menu.addMenu('Register')
        self.help_QMenu = self.menu.addMenu('Help')
        if self.dev:
            self.dev_QMenu = self.menu.addMenu('Dev')

        # -- Options Menu
        self.option_QMenu.addSection('Enable Processes')

        self.checkAll_QAction = QtWidgets.QAction(self.resourcesManager.get('setEnabled.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Enable All Processes', self.option_QMenu)
        self.option_QMenu.addAction(self.checkAll_QAction)
        self.uncheckAll_QAction = QtWidgets.QAction(self.resourcesManager.get('setDisabled.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Disable All Processes', self.option_QMenu)
        self.option_QMenu.addAction(self.uncheckAll_QAction)
        self.defaultAll_QAction = QtWidgets.QAction(self.resourcesManager.get('setDefault.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Reset All Processes', self.option_QMenu)
        self.option_QMenu.addAction(self.defaultAll_QAction)

        self.option_QMenu.addSection('Process Ordering')
        self.orderBy_QMenu = self.option_QMenu.addMenu(self.resourcesManager.get('order.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Order By')

        self.orderByBlueprint_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[0], self.orderBy_QMenu)
        self.orderBy_QMenu.addAction(self.orderByBlueprint_QAction)
        self.orderByCategory_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[1], self.orderBy_QMenu)
        self.orderBy_QMenu.addAction(self.orderByCategory_QAction)
        self.orderAlphabetically_QAction = QtWidgets.QAction(AtConstants.AVAILABLE_DISPLAY_MODE[2], self.orderBy_QMenu)
        self.orderBy_QMenu.addAction(self.orderAlphabetically_QAction)

        orderBy = QtWidgets.QActionGroup(self.orderBy_QMenu)
        orderBy.addAction(self.orderByBlueprint_QAction)
        orderBy.addAction(self.orderByCategory_QAction)
        orderBy.addAction(self.orderAlphabetically_QAction)
        self.orderBy = orderBy

        # -- Register Menu
        # self.currentModule_QAction = QtWidgets.QAction('', self.register_QMenu)
        # self.currentModule_QAction.setEnabled(False)


        # Help Menu
        self.openWiki_QAction = QtWidgets.QAction(self.resourcesManager.get('wiki.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "Open Wiki", self.help_QMenu)
        self.help_QMenu.addAction(self.openWiki_QAction)

        self.reportBug_QAction = QtWidgets.QAction(self.resourcesManager.get('bug.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "Report Bug", self.help_QMenu)
        self.help_QMenu.addAction(self.reportBug_QAction)

        # self.support_QAction = QtWidgets.QAction(self.resourcesManager.get('support.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), "Support Project", self.help_QMenu)
        # self.help_QMenu.addAction(self.support_QAction)

        # -- Context & Environment Toolbar
        self.environment_toolbar = QtWidgets.QToolBar('Environment', self)

        self.contexts_QComboBox = QtWidgets.QComboBox(self)
        self.environment_toolbar.addWidget(self.contexts_QComboBox)

        self.envs_QComboBox = QtWidgets.QComboBox(self)
        self.environment_toolbar.addWidget(self.envs_QComboBox)

        self.addToolBar(self.environment_toolbar)

        # -- Quick Action Toolbar
        self.action_Qtoolbar = QtWidgets.QToolBar('Actions')  #TODO: Maybe show a button to show ui when this is detached. The close event will only hide ui.

        self.runAllCheck_QAction = QtWidgets.QAction(self.resourcesManager.get('check.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Check all', self)
        self.action_Qtoolbar.addAction(self.runAllCheck_QAction)

        self.runAllFix_QAction = QtWidgets.QAction(self.resourcesManager.get('fix.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Fix all', self)
        self.action_Qtoolbar.addAction(self.runAllFix_QAction)

        self.toggleWindow_QAction = QtWidgets.QAction(self.resourcesManager.get('switch.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)
        self.action_Qtoolbar.addAction(self.toggleWindow_QAction)

        self.addToolBar(self.action_Qtoolbar)

        # -- Search and progress Stacked Layout
        searchAndProgress_QStackedLayout = QtWidgets.QStackedLayout()

        self.filterProcesses_QLineEdit = QtWidgets.QLineEdit(self)
        searchAndProgress_QStackedLayout.addWidget(self.filterProcesses_QLineEdit)

        self.generalProgress_QProgressbar = QtWidgets.QProgressBar(self)
        searchAndProgress_QStackedLayout.addWidget(self.generalProgress_QProgressbar)

        self.searchAndProgress_QWidget = QtWidgets.QWidget(self)
        self.searchAndProgress_QWidget.setLayout(searchAndProgress_QStackedLayout)   

        self.searchAndProgress_QStackedLayout = searchAndProgress_QStackedLayout
        self.mainLayout.addWidget(self.searchAndProgress_QWidget)     

        # -- Process Scroll Area
        self.processes_ProcessesScrollArea = ProcessesScrollArea(self.register, self.dev, self)
        self.processes_ProcessesScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.processes_ProcessesScrollArea)

        # -- Statusbar
        self.version_QPushButton = QtWidgets.QPushButton(AtConstants.VERSION)
        self.statusBar.addPermanentWidget(self.version_QPushButton)

    def setupUi(self):
        """ Setup all widgets, Layout in the ui and the main window """

        # -- Options Menu
        self.option_QMenu.setSeparatorsCollapsible(False)

        self.orderByBlueprint_QAction.setCheckable(True)
        self.orderByBlueprint_QAction.setChecked(self.defaultDisplayMode == self.orderByBlueprint_QAction.text())

        self.orderByCategory_QAction.setCheckable(True)
        self.orderByCategory_QAction.setChecked(self.defaultDisplayMode == self.orderByCategory_QAction.text())

        self.orderAlphabetically_QAction.setCheckable(True)
        self.orderAlphabetically_QAction.setChecked(self.defaultDisplayMode == self.orderAlphabetically_QAction.text())

        self.setDisplayMode()
        
        self.orderBy.setExclusive(True)

        # -- Setup contexts, the env will be dinamically set according to the data stored in env. (see connectUi)
        self.setup_context()

        # -- filterProcesses LineEdit
        self.filterProcesses_QLineEdit.setPlaceholderText('Filter Processes...')

        self.searchAndProgress_QWidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.searchAndProgress_QWidget.setFixedHeight(25)

        # -- Action Toolbar
        self.action_Qtoolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.action_Qtoolbar.setIconSize(QtCore.QSize(15, 15))

        # -- Shortcuts
        self.runAllCheck_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_C), self)
        self.runAllFix_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_F), self)
        self.reloadBlueprintsModules_QShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_R), self)

        self.toggleWindow_QAction.setVisible(False)

        # -- Statusbar
        self.version_QPushButton.setFixedHeight(15)
        self.version_QPushButton.setEnabled(True if self.dev else False)

    def connectUi(self):
        """ Connect all widgets to their methods """

        # -- Options Menu
        self.checkAll_QAction.triggered.connect(self.processes_ProcessesScrollArea.checkAll)
        self.uncheckAll_QAction.triggered.connect(self.processes_ProcessesScrollArea.uncheckAll)
        self.defaultAll_QAction.triggered.connect(self.processes_ProcessesScrollArea.defaultAll)

        self.orderBy.triggered.connect(self.setDisplayMode, QtCore.Qt.UniqueConnection)

        self.contexts_QComboBox.currentIndexChanged.connect(self.setup_envs, QtCore.Qt.UniqueConnection)
        self.contexts_QComboBox.currentIndexChanged.emit(self.contexts_QComboBox.currentIndex())
        
        self.envs_QComboBox.currentIndexChanged.connect(self.reload, QtCore.Qt.UniqueConnection)

        self.runAllCheck_QAction.triggered.connect(self.processes_ProcessesScrollArea.runAllCheck, QtCore.Qt.UniqueConnection)
        self.runAllFix_QAction.triggered.connect(self.processes_ProcessesScrollArea.runAllFix, QtCore.Qt.UniqueConnection)

        self.action_Qtoolbar.topLevelChanged.connect(self.setMinimal, QtCore.Qt.UniqueConnection)

        self.filterProcesses_QLineEdit.textChanged.connect(self.processes_ProcessesScrollArea.filterProcesses, QtCore.Qt.UniqueConnection)

        self.toggleWindow_QAction.triggered.connect(self.toggleVisibility, QtCore.Qt.UniqueConnection)

        # -- Shortcuts
        self.runAllCheck_QShortcut.activated.connect(self.processes_ProcessesScrollArea.runAllCheck)
        self.runAllFix_QShortcut.activated.connect(self.processes_ProcessesScrollArea.runAllFix)
        self.reloadBlueprintsModules_QShortcut.activated.connect(self.reloadBlueprintsModules)

        # -- Statusbar
        self.version_QPushButton.clicked.connect(self.reloadBlueprintsModules)

    def refreshUi(self):
        """ """

        # self.register.setup_data()  #TODO: This should be called when necessary only.
        pass

    def closeEvent(self, event):
        """Call when the ui is about to close, allow to close the ui.

        If the ui can be close (`action_Qtoolbar` not detached) the window will be deleted.

        parameters:
        -----------
        event: QCloseEvent
            Close event given by Qt to this method.
        """

        if self.canClose:
            self.deleteLater()
            return super(Athena, self).closeEvent(event)

        self.toggleVisibility()

    def setMinimal(self, topLevel):
        """Allow to switch canClose attribute to prevent window from closing without `action_Qtoolbar`.

        parameters:
        -----------
        topLevel: bool
            Current topLevel state of the `action_Qtoolbar` widget.
        """

        if topLevel:
            self.canClose = False
            self.toggleWindow_QAction.setVisible(True)
        else:
            self.canClose = True
            self.toggleWindow_QAction.setVisible(False)

    def toggleVisibility(self):
        """ Switch window visibility """

        self.setVisible(not self.isVisible())

    def reload(self):
        """ Reload the current blueprints and set the data of the scroll area. """

        with BusyCursor():
            self.blueprints = self.getBlueprints()  #TODO: Make this a property !
            self.processes_ProcessesScrollArea.data = self.blueprints

            self.filterProcesses_QLineEdit.textChanged.emit(self.filterProcesses_QLineEdit.text())

    def reloadBlueprintsModules(self):
        """ Reload the current blueprints.

        notes:
        ------
            Usefull for devellopement purposes, allow to reload the processes classes without breaking the pointers.
        """

        modules = self.register.reloadBlueprintsModules()
        self.reload()

        self.statusBar.showMessage('Reload modules: {}'.format(' - '.join([module.__name__.rpartition('.')[-1] for module in modules])), 5000)

    def setup_context(self):
        """ Switch the current context used by the tool. """

        register = self.register

        with BusyCursor(), BlockSignals([self.contexts_QComboBox], block=True):
            contexts_QComboBox = self.contexts_QComboBox

            # Get the current text before clearing the QComboBox and populate it with the right data.
            currentContext = contexts_QComboBox.currentText()
            contexts_QComboBox.clear()

            for context in register.contexts:
                contexts_QComboBox.addItem(QtGui.QIcon(register.getContextIcon(context)), context)

            # Fallback 1: If there is a value in the QComboBox before, switch on the same value for the new context if exists
            currentIndex = contexts_QComboBox.findText(currentContext)
            if currentIndex > -1:
                contexts_QComboBox.setCurrentIndex(currentIndex)

            # Fallback 2: If a default value have been given at init, switch to this value.
            else:
                defaultText = self.configuration['context']
                if defaultText is not None:
                    defaultIndex = contexts_QComboBox.findText(defaultText)
                    if defaultIndex > -1:
                        contexts_QComboBox.setCurrentIndex(defaultIndex)
                    else: 
                        contexts_QComboBox.setCurrentIndex(0)

        self.contexts_QComboBox.currentIndexChanged.emit(self.contexts_QComboBox.currentIndex())

    def setup_envs(self, index):
        """ Setup the current env for the tool to display processes.

        parameters:
        -----------
        index: int
            The current index of the `envs_QComboBox` widget.
        
        notes:
        ------
            If the method is called after context changed and current env also exist in the new context, it will stay on the same env.
        """

        register = self.register

        with BusyCursor(), BlockSignals([self.envs_QComboBox], block=True):
            # Catch a possible error, if signal give -1 there is an error
            if index == -1: 
                return

            envs_QComboBox = self.envs_QComboBox

            # Get the context from in contexts QComboBox from index given by signal
            context = self.contexts_QComboBox.itemText(index)
            if not context: 
                return

            # Get the current text before clearing the QComboBox and populate it with the right data.
            currentEnv = envs_QComboBox.currentText()
            envs_QComboBox.clear()

            for env in register.getEnvs(context):
                envs_QComboBox.addItem(QtGui.QIcon(register.getEnvIcon(context, env)), env)

            # Fallback 1: If there is a value in the QComboBox before, switch on the same value for the new context if exists
            currentIndex = envs_QComboBox.findText(currentEnv)
            if currentIndex > -1 and currentIndex <= envs_QComboBox.count():
                envs_QComboBox.setCurrentIndex(currentIndex)

            # Fallback 2: If a default value have been given at init, switch to this value.
            else:
                defaultText = self.configuration['env']
                if defaultText is not None:
                    defaultIndex = envs_QComboBox.findText(defaultText)
                    if defaultIndex > -1:
                        envs_QComboBox.setCurrentIndex(defaultIndex)
                    else: 
                        envs_QComboBox.setCurrentIndex(0)

        self.envs_QComboBox.currentIndexChanged.emit(self.envs_QComboBox.currentIndex())

    def setDisplayMode(self):
        """ Change the current display mode of the scroll area widget. """

        self.processes_ProcessesScrollArea.displayMode = self.orderBy.checkedAction().text()
        self.processes_ProcessesScrollArea.refreshDisplay()

    def getBlueprints(self):
        """ Get the blueprint from the register from current context and env. """

        return  self.register.getBlueprints(self.contexts_QComboBox.currentText(), self.envs_QComboBox.currentText(), forceReload=self.dev)


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

        painter.drawText(option.rect.adjusted(0, option.rect.height(), option.rect.width(), option.rect.height()), 
                         itemData[0])

        painter.restore()


class Status(object):
    """ Available status for ProcessWidget display 

    It handle color and isFail attribute that define if the process should be error.
    """

    class DEFAULT():
        color = QtGui.QColor(50, 50, 50)
        isFail = False        

    class SUCCESS():
        color = QtGui.QColor(0, 128, 0)  # Office Green
        isFail = False

    class EXCEPTION():
        color = QtGui.QColor(85, 85, 85) # Davy's Grey
        isFail = True

    class WARNING():
        color = QtGui.QColor(196, 98, 16) # Alloy Orange
        isFail = True

    class ERROR():
        color = QtGui.QColor(102, 0, 0) # Blood Red
        isFail = True


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
    QPushButton#check, QPushButton#fix, QPushButton#tool
    {
        padding-left: 4px;
    }
    QPushButton#check:hover, QPushButton#fix:hover, QPushButton#tool:hover
    {
        background-color: rgba(0, 0, 0, 70);
    }
    QPushButton#check:pressed, QPushButton#fix:pressed, QPushButton#tool:pressed
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

    def __init__(self, blueprint, parent, window=None):
        """ Initialise the Process widget from a blueprint.

        parameters:
        -----------
        blueprint: QaulityCheck.AtCore.Blueprint
            A Athena Blueprint that will be drived through ui.
        parent: QWidget
            The QWidget parent of this widget.
        """ 

        super(ProcessWidget, self).__init__(parent)

        self.parent = parent
        self.window = window or parent

        self.resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)
        
        self.blueprint = blueprint
        self.options = blueprint._options
        self.name = blueprint._name
        self.docstring = blueprint._docstring
        self.isEnabled = blueprint._isEnabled
        self.isCheckable = blueprint._isCheckable
        self.isFixable = blueprint._isFixable
        self.hasTool = blueprint._hasTool
        self.isNonBlocking = blueprint._isNonBlocking

        self.status = Status.DEFAULT
        self.isOpened = False

        self._feedback = None

        self.buildUi()
        self.setupUi()
        self.connectUi()

    def buildUi(self):
        """ Create each widget that constitue the ProcessWidget """

        # -- Enable CheckBox
        self.enable_QCheckBox = QtWidgets.QRadioButton(self)

        # -- Process Name Display PushButton
        self.name_QLabel = QtWidgets.QPushButton(self.resourcesManager.get('right-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), self.name, self)

        # -- Tool PushButton
        self.tool_QPushButton =  QtWidgets.QPushButton(self.resourcesManager.get('tool.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Fix PushButton
        self.fix_QPushButton = QtWidgets.QPushButton(self.resourcesManager.get('fix.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Check PushButton
        self.check_QPushButton = QtWidgets.QPushButton(self.resourcesManager.get('check.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Help PushButton
        self.help_QPushButton =  QtWidgets.QPushButton(self.resourcesManager.get('help.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), '', self)

        # -- Stack Layout -> Stack Widget
        self.header_QStackedLayout = QtWidgets.QStackedLayout(self)

        self.header_QWidget = QtWidgets.QWidget(self)
        self.header_QWidget.setLayout(self.header_QStackedLayout)

        # -- Container Layout
        container_QWidget = QtWidgets.QWidget(self)
        container_QHBoxLayout = QtWidgets.QHBoxLayout(container_QWidget)

        container_QHBoxLayout.addWidget(self.enable_QCheckBox)
        container_QHBoxLayout.addWidget(self.name_QLabel)

        container_QHBoxLayout.addStretch()

        container_QHBoxLayout.addWidget(self.tool_QPushButton)
        container_QHBoxLayout.addWidget(self.fix_QPushButton)
        container_QHBoxLayout.addWidget(self.check_QPushButton)
        container_QHBoxLayout.addWidget(self.help_QPushButton)

        self.header_QStackedLayout.addWidget(container_QWidget)

        self.container_QHBoxLayout = container_QHBoxLayout
        
        # -- Progressbar
        self.progressbar_QProgressBar = QtWidgets.QProgressBar()
        self.header_QStackedLayout.addWidget(self.progressbar_QProgressBar)

        # -- Result Widget
        self.result_QListWidget = TracebackList(self)

        # -- Main Layout
        main_QVBoxLayout = QtWidgets.QVBoxLayout(self)

        main_QVBoxLayout.addWidget(self.header_QWidget)
        main_QVBoxLayout.addWidget(self.result_QListWidget)

        self.main_QVBoxLayout = main_QVBoxLayout

    def setupUi(self):
        """ Setup each widget that constitue the ProcessWidget. """

        # -- Enable CheckBox
        self.enable_QCheckBox.setChecked(self.isEnabled)

        # -- Process Name Display PushButton
        # self.name_QLabel.setButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.name_QLabel.setIconSize(QtCore.QSize(15, 15))

        # -- Tool PushButton
        self.tool_QPushButton.setObjectName(AtConstants.TOOL)
        self.tool_QPushButton.setToolTip('Launch "{0}" tool'.format(self.name))
        self.tool_QPushButton.setVisible(self.hasTool)

        # -- Fix PushButton
        self.fix_QPushButton.setObjectName(AtConstants.FIX)
        self.fix_QPushButton.setToolTip('Run "{0}" fix'.format(self.name))
        self.fix_QPushButton.setVisible(False)

        # -- Check PushButton
        self.check_QPushButton.setObjectName(AtConstants.CHECK)
        self.check_QPushButton.setToolTip('Run "{0}" check'.format(self.name))
        self.check_QPushButton.setVisible(self.isCheckable)

        # -- Help PushButton
        self.help_QPushButton.setObjectName('help')
        self.help_QPushButton.setToolTip(self.docstring)
        self.help_QPushButton.enterEvent = self.showTooltip

        # -- Container Layout
        self.container_QHBoxLayout.setContentsMargins(5, 0, 0, 0)
        self.container_QHBoxLayout.setSpacing(5)

        # -- Progressbar
        self.progressbar_QProgressBar.setAlignment(QtCore.Qt.AlignLeft)
        self.progressbar_QProgressBar.setFormat(AtConstants.PROGRESSBAR_FORMAT.format(self.name))

        # -- Stack Layout -> Stack Widget
        self.header_QWidget.setFixedHeight(25)

        # -- Result Widget
        self.result_QListWidget.setVisible(False)

        # -- Main Layout
        self.main_QVBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.main_QVBoxLayout.setSpacing(0)

        palette = self.palette()
        palette.setColor(palette.Background, self.status.color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.setStyleSheet(self.STYLESHEET)
        self.setFixedHeight(25)

    def connectUi(self):
        """ Connect all widget to their respective methods. """

        # -- Process Name Display PushButton
        self.name_QLabel.clicked.connect(self.toggleTraceback)

        # -- Tool PushButton
        self.tool_QPushButton.clicked.connect(self.execTool)

        # -- Fix PushButton
        self.fix_QPushButton.clicked.connect(self.execFix)

        # -- Check PushButton
        self.check_QPushButton.clicked.connect(self.execCheck)

        # -- Connect the progressbar to the process _progressbar attribute.
        self.blueprint.setProgressbar(self.progressbar_QProgressBar)

    def enterEvent(self, event):
        """ Event handled by Qt to manage mouse enter event and lighter the widget color.

        parameters:
        -----------
        event: QEvent
            Event emitted by Qt when mouse enter the widget.
        """

        palette = self.palette()

        palette.setColor(palette.Background, self.status.color.lighter(125))
        self.setPalette(palette)

    def leaveEvent(self, event):
        """ Event handled by Qt to manage mouse exit event and reset widget color.

        parameters:
        -----------
        event: QEvent
            Event emitted by Qt when mouse exit the widget.
        """

        palette = self.palette()

        palette.setColor(palette.Background, self.status.color)
        self.setPalette(palette)

    def mousePressEvent(self, event):
        """ Event handled by Qt to manage click press on the widget and darker it's color.

        parameters:
        -----------
        event: QEvent
            Event emitted by Qt when click is pressed on the widget.
        """

        palette = self.palette()

        palette.setColor(palette.Background, self.status.color.darker(125))
        self.setPalette(palette)

        if event.button() is QtCore.Qt.MouseButton.LeftButton:
            self.toggleTraceback()
        elif event.button() is QtCore.Qt.MouseButton.RightButton:
            self.setChecked(not self.isChecked())

    def mouseReleaseEvent(self, event):
        """ Event handled by Qt to manage click release on the widget and reset it's color.

        parameters:
        -----------
        event: QEvent
            Event emitted by Qt when click is released on the widget.
        """

        palette = self.palette()

        # It seems that mouseReleaseEvent is triggered after leaveEvent
        palette.setColor(palette.Background, self.status.color.lighter(125))
        self.setPalette(palette)

    @property
    def feedback(self):
        """ Getter that return the value stored in `_feedback` """

        return self._feedback

    @feedback.setter
    def feedback(self, value):
        """ `_feedback` setter that allow to show feedback in the tree widget.

        parameters:
        -----------
        value: list(dict(), ...)
            List of data to create in the list widget. This value should be the feedback of a process stored in a blueprint.
        """

        self._feedback = value
        self.result_QListWidget.clear()

        if value is None:
            self.result_QListWidget.setVisible(self.isOpened)
            self.closeTraceback()
            return

        elif isinstance(value, str):  # If the value is a `str` it should be display flat in the widget.
            self.result_QListWidget.logException(value.split('\n'))  # Exception occured, print it in the widget

        else:
            self.result_QListWidget.logFeedback(value)  # Error found, log them in the widget
        self.openTraceback()

    def toggleTraceback(self):
        """Switch visibility of the traceback widget. """

        if not self.isOpened:
            self.openTraceback()
        else:
            self.closeTraceback()
            
    def openTraceback(self):
        """ Show the traceback widget and change the displayed arrow shape. """

        if not self.feedback:
            return
        self.name_QLabel.setIcon(self.resourcesManager.get('bottom-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon))
        self.isOpened = True
        self.setFixedHeight(45 + self.result_QListWidget.getContentSize().height())

        self.result_QListWidget.setVisible(self.isOpened)

    def closeTraceback(self):
        """ Hide the traceback widget and change the displayed arrow shape. """

        self.name_QLabel.setIcon(self.resourcesManager.get('right-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon))
        self.isOpened = False
        self.setFixedHeight(25)

        self.result_QListWidget.setVisible(self.isOpened)

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
        return self.enable_QCheckBox.isChecked()

    def setChecked(self, state):
        """ Check the ProcessWidget """

        self.enable_QCheckBox.setChecked(state)

    def execCheck(self):
        """ Run the `check` method of the Blueprint's Process.

        Exec the Process `check` method and retrieve the result to change the process state and log feedback if necessary.
        Handle any Exception to switch the ProcessWidget state to 'Exception' and log the Exception's feedback in it.
        """

        with self.ExecContext(self), BusyCursor():
            try:
                result, state = self.blueprint.check()
                    #TODO: Why this ?

                if state:
                    if self.isNonBlocking:
                        self.status = Status.WARNING  # There is warning(s).
                    else:
                        self.status = Status.ERROR  # There is error(s).
                    self.feedback = result
                    self.fix_QPushButton.setVisible(self.isFixable)
                else:
                    self.status = Status.SUCCESS # The process succeed.
                    self.feedback = None
                    self.fix_QPushButton.setVisible(False)

            except Exception as error:
                self.status = Status.EXCEPTION  # The process encounter an exception during it's execution.
                self.feedback = traceback.format_exc(error).rstrip() #TODO: Test another way
                traceback.print_exc(error)

    def execFix(self):
        """ Run the `fix` method of the Blueprint's Process.

        Exec the Process `fix` method and handle any Exception to switch the ProcessWidget state to 'Exception' and log the 
        Exception's feedback in it.
        Then, launch the `execCheck` method to catch any other error to update the ProcessWidget.
        """

        with self.ExecContext(self), BusyCursor():
            try:
                result = self.blueprint.fix()

            except Exception as error:
                self.status = Status.EXCEPTION  # The process encounter an exception during it's execution.
                self.feedback = traceback.format_exc(error).rstrip() #TODO: Test another way
                traceback.print_exc(error)
                return

        # After a fix, re-launch a check to ensure everything is clean.
        self.execCheck()


    def execTool(self):
        """ Run the `tool` method of the Blueprint's Process.

        Exec the Process `tool` method and handle any Exception to switch the ProcessWidget state to 'Exception' and log the 
        Exception's feedback in it.
        """

        with self.ExecContext(self), BusyCursor():
            try:
                result = self.blueprint.tool()

                if result is not None and hasattr(result, 'show'):
                    result.setParent(self.window, QtCore.Qt.Window)
                    result.show()

            except Exception as error:
                self.status = Status.EXCEPTION  # The process encounter an exception during it's execution.
                self.feedback = traceback.format_exc(error).rstrip() #TODO: Test another way
                traceback.print_exc(error)

    class ExecContext(object):

        def __init__(self, instance):
            self.instance = instance

        def __enter__(self):
            self.instance.leaveEvent(None)

            self.instance.header_QStackedLayout.setCurrentIndex(1)
            self.instance.progressbar_QProgressBar.setValue(0)

        def __exit__(self, exception_type, exception_value, traceback):
            
            self.instance.header_QStackedLayout.setCurrentIndex(0)

            if self.instance.underMouse():
                self.instance.enterEvent(None)
            else:
                self.instance.leaveEvent(None)


class TracebackList(QtWidgets.QTreeWidget):

    def __init__(self, parent):
        super(TracebackList, self).__init__(parent)

        self.parent = parent

        self.resourcesManager = AtUtils.RessourcesManager(__file__, backPath='..{0}ressources'.format(os.sep), key=AtConstants.PROGRAM_NAME)

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.itemExpanded.connect(self.expand)
        self.itemCollapsed.connect(self.collapse)

        self.header().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

    def mouseReleaseEvent(self, event):

        if event.button() is QtCore.Qt.MouseButton.RightButton:
            return event.ignore()

        toSelect = []
        for item in self.selectedItems():
            data = item.data(0, QtCore.Qt.UserRole)
            if not data: 
                continue

            if item.parent() is None:
                toSelect.extend(data['toSelect'])
            else: 
                toSelect.append(data)
        
        AtUtils.softwareSelection(list(set(toSelect)))

        return super(TracebackList, self).mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        
        contextMenu = QtWidgets.QMenu(self)
        contextMenu.setSeparatorsCollapsible(False)

        selectAll_QAction = QtWidgets.QAction(self.resourcesManager.get('select.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Select All', contextMenu)
        selectAll_QAction.triggered.connect(self.selectAll)
        contextMenu.addAction(selectAll_QAction)

        contextMenu.addSeparator()

        expandAll_QAction = QtWidgets.QAction(self.resourcesManager.get('bottom-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Expand All', contextMenu)
        expandAll_QAction.triggered.connect(self.expandAll)
        contextMenu.addAction(expandAll_QAction)

        collapseAll_QAction = QtWidgets.QAction(self.resourcesManager.get('right-arrow.png', AtConstants.PROGRAM_NAME, QtGui.QIcon), 'Collapse All', contextMenu)
        collapseAll_QAction.triggered.connect(self.collapseAll)
        contextMenu.addAction(collapseAll_QAction)

        contextMenu.popup(QtGui.QCursor.pos())

        return super(TracebackList, self).contextMenuEvent(event)

    def logFeedback(self, text):

        self.setHeaderHidden(False)
        self.setHeaderLabels(['Found {0} error{1}'.format(len(text), 's' if len(text) > 1 else ''), ''])

        for feedback in text:
            toDisplay = feedback['toDisplay']

            if toDisplay:
                parent = QtWidgets.QTreeWidgetItem([str(feedback['title']), '        found {0}'.format(str(len(toDisplay)))])
                parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
            else:
                parent = QtWidgets.QTreeWidgetItem([str(feedback['title'])])
                parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.DontShowIndicator)

            # If there is a documentation for this error display it in a tooltip.
            if feedback['documentation']:
                parent.setToolTip(0, feedback['documentation'])

            parent.setData(0, QtCore.Qt.UserRole, feedback)

            self.addTopLevelItem(parent)

    def expand(self, item):

        with BusyCursor():
            self.clearChildren(item)

            data = item.data(0, QtCore.Qt.UserRole)
            for toDisplay, toSelect in zip(data['toDisplay'], data['toSelect']):
                if not toDisplay:
                    continue
                child = QtWidgets.QTreeWidgetItem([str(toDisplay)])
                child.setData(0, QtCore.Qt.UserRole, toSelect)
                item.addChild(child)

            self.parent.setFixedHeight(45 + self.getContentSize().height())

    def collapse(self, item):

        with BusyCursor():
            self.clearChildren(item)

            self.parent.setFixedHeight(45 + self.getContentSize().height())

    def clearChildren(self, item):

        for i in reversed(range(item.childCount())):
            child = item.takeChild(i)
            del child

    def logException(self, exception):

        self.setHeaderHidden(True)

        for line in exception:
            parent = QtWidgets.QTreeWidgetItem([line])
            self.addTopLevelItem(parent)

    def selectAll(self):

        items = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]

        toSelect = []
        for item in items:
            item.setSelected(True)
            data = item.data(0, QtCore.Qt.UserRole)
            toSelect.extend(data['toSelect'])

        AtUtils.softwareSelection(list(set(toSelect)))

    def expandAll(self):

        items = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        for item in items:
            item.setExpanded(True)

    def collapseAll(self):

        items = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        for item in items:
            item.setExpanded(False)

    def getContentSize(self):
        """  """

        height = 2 * self.frameWidth() # border around tree

        header = self.header()
        if not self.isHeaderHidden():
            headerSizeHint = header.sizeHint()
            height += headerSizeHint.height()

        rows = 0
        it = QtWidgets.QTreeWidgetItemIterator(self)
        while it.value() is not None:
            rows += 1
            index = self.indexFromItem(it.value())
            height += self.rowHeight(index)
            it += 1

        self.resizeColumnToContents(0)
        return QtCore.QSize(header.length() + 2 * self.frameWidth(), height)


class ProcessesScrollArea(QtWidgets.QScrollArea):
    """ Scroll Area widget display and manage Process Widgets

    Manage the display and give a global control over all ProcessWidgets.
    This widget only need to have its data changed to display the new ProcessWidgets that it will create and delete when needed.
    It also give controll over all Process Widgets like check/unchek, run check/fix and filter.
    """

    def __init__(self, register, dev=False, parent=None):
        super(ProcessesScrollArea, self).__init__()

        self.register = register
        self.dev = dev
        self.parent = parent
        self.displayMode = AtConstants.AVAILABLE_DISPLAY_MODE[0]

        self._data = []
        self.processes = {}

        self.stopRequested = False

        self.mainLayout = QtWidgets.QVBoxLayout(self)

        self.buildUi()
        self.setupUi()
        self.setWidgetResizable(True)

        self.showNoProcess()

    def buildUi(self):
        """ Build the Scroll Area Widget """

        scrollAreaWidgetContents = QtWidgets.QWidget(self)
        self.setWidget(scrollAreaWidgetContents)
        self.layout = QtWidgets.QVBoxLayout(scrollAreaWidgetContents)

        self.scrollAreaWidgetContents = scrollAreaWidgetContents

        #FIXME This seems not to work with PyQt5
        # -- Fonts
        # self.noProcesses_QFont = QtGui.QFont('Candara', 20)
        # self.category_QFont = QtGui.QFont('Candara', 15)

    def setupUi(self):
        """ Setup the ScrollArea widget """

        # palette = self.palette()
        # palette.setColor(QtGui.QPalette.Background, QtGui.QColor(52, 52, 52))
        # self.setPalette(palette)

        self.layout.setSpacing(1)
        try: self.layout.setMargin(0)  # Deprecated in PyQt5 But not on PySide2
        except: pass
        self.scrollAreaWidgetContents.setContentsMargins(2, 2, 2, 2)

    def keyPressEvent(self, event):

        if event.key() == QtCore.Qt.Key_Escape:
            self.stopRequested = True
            return event.accept()

        return super(ProcessesScrollArea, self).keyPressEvent(event)

    def refreshDisplay(self): #TODO: Maybe remove this wrapper. By renaming the addWidget.
        """ Refresh the display of the widget by removing all Widgets and rebuild the new one. """

        self.clear(self.layout, safe=True)
        self.addWidgets()
        self.showNoProcess()

    @property
    def data(self):
        """ Getter that return value of `self._data`. """
        return self._data

    @data.setter
    def data(self, value):
        """ Setter for `self._data`.

        parameters:
        -----------
        value: dict(int: Blueprint)
            Dict containing Blueprint object to use as source for ProcessWidgets.
        """
        
        self._data = value

        self.buildWidgets()
        self.clear(self.layout, safe=not self.dev)  # In dev mode, we always delete the widget to simplify the test.

        if value:
            self.addWidgets()
        else:
            self.showNoProcess()

    def showNoProcess(self):
        """ Switch the widget display to show only a text. """

        if self.processes:
            return

        self.clear(self.layout, safe=False)

        noProcesses_QLabel = QtWidgets.QLabel('No Process Available')
        noProcesses_QLabel.setAlignment(QtCore.Qt.AlignCenter)
        noProcesses_QLabel.setStyleSheet('font: 15pt;')
        # noProcesses_QLabel.setFont(self.noProcesses_QFont)
        self.layout.addWidget(noProcesses_QLabel)

    def runAllCheck(self):
        """ Execute check method on all visible processes that could be run.

        Launch each check by blueprint order if they can be launched (relative to their tags and visibility state.)
        Also update the general progress bar to display execution progress.
        """

        if not self.processes:
            return

        self.stopRequested = False
        self.parent.statusBar.showMessage('Check in progress... Press [ESCAPE] to interrupt', 1)
        self.parent.searchAndProgress_QStackedLayout.setCurrentIndex(1)

        progressbarLen = 100.0/len(self.processes)
        for i, process in self.processes.items():
            if self.stopRequested:
                raise

            self.parent.generalProgress_QProgressbar.setValue(progressbarLen*i)

            if process.blueprint._isCheckable and process.isChecked() and (process.isVisible() or not self.parent.canClose):
                self.ensureWidgetVisible(process)
                process.execCheck()
        
        self.parent.searchAndProgress_QStackedLayout.setCurrentIndex(0)
        self.parent.generalProgress_QProgressbar.reset()

    def runAllFix(self):
        """ Execute fix method on all visible processes that could be run.

        Launch each fix by blueprint order if they can be launched (relative to their tags and visibility state.)
        Also update the general progress bar to display execution progress.
        """

        if not self.processes:
            return

        self.stopRequested = False
        self.parent.statusBar.showMessage('Fix in progress... Press [ESCAPE] to interrupt', 1)
        self.parent.searchAndProgress_QStackedLayout.setCurrentIndex(1)

        progressbarLen = 100.0/len(self.processes)
        for i, process in self.processes.items():
            if self.stopRequested:
                raise

            self.parent.generalProgress_QProgressbar.setValue(progressbarLen*i)

            if not process.status.isFail and process.status is not Status.EXCEPTION:
                continue

            if process.isFixable and process.isChecked() and (process.isVisible() or not self.parent.canClose):
                self.ensureWidgetVisible(process)
                process.execFix()

        self.parent.searchAndProgress_QStackedLayout.setCurrentIndex(0)
        self.parent.generalProgress_QProgressbar.reset()

        if self.register.getData('parameters').get('recheck', False):
            self.runAllCheck()

    def buildWidgets(self):
        """" Create the new widget and setup them.

        Build the process widgets from blueprint list and setup them (resolve links with process methods.)
        """
        
        self.processes = processes = self.register.getData('widget') or {}
        if processes and not self.dev:
            return  # There is already widgets in the register

        uiLinkResolveBlueprints = []
        for index, blueprint in enumerate(self._data):
            if not blueprint._inUi:
                uiLinkResolveBlueprints.append(None)
                continue  # Skip this check if it does not be run in ui
            processes[index] = processWidget = ProcessWidget(blueprint, parent=self, window=self.parent)
            uiLinkResolveBlueprints.append(processWidget)
        self.register.setData('widget', processes)

        for blueprint in self._data:
            blueprint.resolveLinks(uiLinkResolveBlueprints, check='execCheck', fix='execFix', tool='execTool')

    # Could be property (get/set) named displayMode
    def addWidgets(self):
        """ Fallback on all display mode to launch the corresponding `addWidget` method. """

        mode = self.displayMode

        if mode == AtConstants.AVAILABLE_DISPLAY_MODE[0]:
            self.addWidgetsByHeader()
        elif mode == AtConstants.AVAILABLE_DISPLAY_MODE[1]:
            self.addWidgetsByCategory()
        elif mode == AtConstants.AVAILABLE_DISPLAY_MODE[2]:
            self.addWidgetsAlphabetically()

        for widget in self.processes.values():
            widget.leaveEvent(None)

    def addWidgetsByHeader(self):
        """ Add widget in the scroll area by Blueprint order (default) """

        for index in self.processes.keys():
            self.layout.addWidget(self.processes[index])

        self.layout.addStretch()

    def addWidgetsByCategory(self):
        """ Add widgets in the scroll area by Category Order (Also add Label for category) """

        categories = []
        orderedByCategory = {}
        for index, process in self.processes.items():
            category = process.blueprint.category

            if category not in categories:
                categories.append(category)
                orderedByCategory[category] = []
            orderedByCategory[category].append(process)

        # categories.sort()

        for category in categories:
            processes = orderedByCategory[category]

            category_QLabel = QtWidgets.QLabel('{0}'.format(category))
            category_QLabel.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom)
            category_QLabel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
            category_QLabel.setStyleSheet('font: 11pt; font-weight: bold')
            self.layout.addWidget(category_QLabel)

            for process in processes:
                self.layout.addWidget(process)

        self.layout.addStretch()

    def addWidgetsAlphabetically(self):
        """ Add widget in the scroll area by Blueprint order (default) """

        for process in sorted(self.processes.values(), key=lambda proc: proc.blueprint.name):
            self.layout.addWidget(process)

        self.layout.addStretch()

    def checkAll(self):
        """ Check all Process Widget in the scroll area """

        for process in self.processes.values():
            process.setChecked(True)

    def uncheckAll(self):
        """ Uncheck all Process Widget in the scroll area """

        for process in self.processes.values():
            process.setChecked(False)

    def defaultAll(self):
        """ Reset all Process Widget check state in the scroll area """

        for process in self.processes.values():
            process.setChecked(process.blueprint.isEnabled)

    def filterProcesses(self, text):
        """ Allow to filter the list of processes by hiding those who didn't match with the given string string.

        parameters:
        -----------
        text: str
            Text used to filter processes in the area.
        """

        for process in self.processes.values():
            process.setVisible(text.lower() in process.blueprint.name.lower())

        if not text:
            self.parent.statusBar.showMessage('{} processes available'.format(len(self.processes)), 3000)
            return

        visibleProcesses = [process for process in self.processes.values() if process.isVisible()]
        if not visibleProcesses:
            self.parent.statusBar.showMessage('No process match name "{}"'.format(text), 3000)
        else:
            self.parent.statusBar.showMessage('Found {} processes that match name "{}"'.format(len(visibleProcesses), text), 3000)

    def clear(self, layout, safe=False):
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
                self.clear(layoutItem, safe=safe)
                layoutItem.deleteLater()
                del layoutItem


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

        self.widgets = widgets
        self.block = block

    def __enter__(self):
        self.defaultStates = {}
        for widget in self.widgets:
            self.defaultStates[widget] = widget.blockSignals(self.block)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for widget, state in self.defaultStates.items():
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
        standaloneApplication = QtWidgets.QApplication(sys.argv)
        win = Athena()
        win.show()

        sys.exit(standaloneApplication.exec_())
        return standaloneApplication  #TODO: Find what is needed here to launch the tool in standalone mode

    topWidgets = QtCore.QCoreApplication.instance().topLevelWidgets()
    topWidgets = [widget for widget in topWidgets
                   if widget.isVisible() 
                   and widget.parent() is None 
                   and isinstance(widget, QtWidgets.QWidget)]

    # If there is no top widget, the tool is standalone
    if not topWidgets:
        return None

    # if len(topWidgets) == 1:
    #     return topWidgets[0]

    for widget in topWidgets:
        if widget.objectName().lower() == 'mainwindow' or widget.windowIconText():
            return widget
        elif widget.metaObject().className().lower() == 'foundry::ui::dockmainwindow':
            return widget

    raise RuntimeError('Could not find the parent window')


def getSizeFromScreen():
    """ Get the Width and Height of the Window relative to a 16:9 Scale """

    rec = QtWidgets.QApplication.desktop().screenGeometry()
    
    width = rec.width()
    height = rec.height()
    
    return ((width*450)/2560, (height*900)/1440)













def main():

    app = QtWidgets.QApplication(sys.argv)
    win = Athena()
    win.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()



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