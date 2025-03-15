import sys
import os
import uuid
import json
import shutil
import random
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QPixmap, QColor, QFont, QIcon
from PyQt5.QtCore import QPropertyAnimation
import graphviz

# Создаём папку data, если её ещё нет
os.makedirs("data", exist_ok=True)


# =============================================================================
# Функции минимизации и преобразования
# =============================================================================

def initial_partition(mealy_dict, alphabet):
    partition = {}
    for s in mealy_dict:
        signature = tuple(mealy_dict[s][letter][1] for letter in alphabet)
        partition.setdefault(signature, set()).add(s)
    return list(partition.values())


def state_to_block_map(blocks):
    mapping = {}
    for i, block in enumerate(blocks):
        for s in block:
            mapping[s] = i
    return mapping


def refine_blocks(blocks, mealy_dict, alphabet):
    new_blocks = []
    state_block = state_to_block_map(blocks)
    for block in blocks:
        if len(block) == 1:
            new_blocks.append(block)
        else:
            groups = {}
            for s in block:
                trans_sig = tuple(state_block[mealy_dict[s][letter][0]] for letter in alphabet)
                groups.setdefault(trans_sig, set()).add(s)
            new_blocks.extend(groups.values())
    return new_blocks


def minimize_mealy(mealy_dict, alphabet):
    blocks = initial_partition(mealy_dict, alphabet)
    iteration_info = []
    iteration_info.append([sorted(list(b), key=int) for b in blocks])
    while True:
        new_blocks = refine_blocks(blocks, mealy_dict, alphabet)
        iteration_info.append([sorted(list(b), key=int) for b in new_blocks])
        if sorted([sorted(b) for b in new_blocks]) == sorted([sorted(b) for b in blocks]):
            break
        blocks = new_blocks
    minimized_map = {}
    for block in blocks:
        rep = sorted(block, key=int)[0]
        for s in block:
            minimized_map[s] = rep
    minimized_states = sorted(set(minimized_map.values()), key=int)
    min_mealy = {}
    for rep in minimized_states:
        s_candidate = rep
        min_mealy[rep] = {}
        for letter in alphabet:
            dest, out = mealy_dict[s_candidate][letter]
            new_dest = minimized_map[dest]
            min_mealy[rep][letter] = (new_dest, out)
    return blocks, minimized_map, min_mealy, iteration_info


def build_moore(min_mealy, alphabet):
    # Собираем реакции для каждого состояния (выходы, с которыми это состояние может быть достигнуто)
    moore_reactions = {s: set() for s in min_mealy}
    for s in min_mealy:
        for letter in alphabet:
            dest, out = min_mealy[s][letter]
            moore_reactions[dest].add(out)
    # Если для какого-либо состояния не заданы входящие реакции, добавляем произвольный выход 'x'
    for s in min_mealy:
        if not moore_reactions[s]:
            moore_reactions[s].add('x')

    def get_moore_name(state, reaction):
        return f"{state},{reaction}"

    # Создаём уникальные копии состояний автомата Мура вида (state, reaction)
    moore_states = {}
    for s in min_mealy:
        for reaction in moore_reactions[s]:
            moore_states[(s, reaction)] = get_moore_name(s, reaction)

    # Формируем таблицу переходов автомата Мура:
    # для каждого перехода из состояния q по символу letter переходим в состояние (dest, out),
    # где out берётся непосредственно из перехода автомата Мили
    moore_transitions = {}
    for (q, r) in moore_states:
        current_name = moore_states[(q, r)]
        moore_transitions[current_name] = {}
        for letter in alphabet:
            dest, out = min_mealy[q][letter]
            target_name = moore_states[(dest, out)]
            moore_transitions[current_name][letter] = target_name

    # Определяем начальное состояние автомата Мура
    possible_reactions = sorted(list(moore_reactions['1']))
    if 'x' in possible_reactions:
        moore_initial = moore_states[('1', 'x')]
    else:
        moore_initial = moore_states[('1', possible_reactions[0])]

    return moore_states, moore_transitions, moore_initial


# =============================================================================
# Функции визуализации
# =============================================================================

def visualize_mealy(min_mealy, alphabet, filename='minimized_mealy'):
    unique_id = str(uuid.uuid4())
    full_filename = os.path.join("data", f"{filename}_{unique_id}")
    mealy_graph = graphviz.Digraph(name='Minimized_Mealy', format='png')
    mealy_graph.attr(dpi="1200")
    mealy_graph.attr(rankdir='LR', size='9,5', bgcolor="#f9f9f9")
    mealy_graph.attr('node', shape='circle', style='filled', fillcolor='lightblue',
                     fontname='Helvetica', fontsize='22', penwidth='2')
    mealy_graph.attr('edge', color='black', fontname='Helvetica', fontsize='20', penwidth='4')
    for s in sorted(min_mealy.keys(), key=int):
        mealy_graph.node(s)
    mealy_graph.node('', shape='none')
    if '1' in min_mealy:
        mealy_graph.edge('', '1', style='bold')
    for s in sorted(min_mealy.keys(), key=int):
        for letter in alphabet:
            dest, out = min_mealy[s][letter]
            mealy_graph.edge(s, dest, label=f"{letter} / {out}")
    mealy_graph.render(full_filename, view=False)
    print(f"Минимизированный автомат Мили сохранён в файл: {full_filename}.png")
    return full_filename


def visualize_moore(moore_states, moore_transitions, moore_initial, filename='moore'):
    unique_id = str(uuid.uuid4())
    full_filename = os.path.join("data", f"{filename}_{unique_id}")
    moore_graph = graphviz.Digraph(name='Moore', format='png')
    moore_graph.attr(dpi="1200")
    moore_graph.attr(rankdir='LR', size='9,5', bgcolor="#f9f9f9")
    moore_graph.attr('node', shape='box', style='rounded,filled', fillcolor='lightgreen',
                     fontname='Helvetica', fontsize='22', penwidth='2')
    moore_graph.attr('edge', color='darkgray', fontname='Helvetica', fontsize='20', penwidth='4')
    for (s, r), name in moore_states.items():
        label = f"{s}\n{r}"
        moore_graph.node(name, label=label)
    moore_graph.node('', shape='none')
    moore_graph.edge('', moore_initial, style='bold')
    for s in moore_transitions:
        for letter in sorted(moore_transitions[s].keys()):
            dest = moore_transitions[s][letter]
            moore_graph.edge(s, dest, label=letter)
    moore_graph.render(full_filename, view=False)
    print(f"Автомат Мура сохранён в файл: {full_filename}.png")
    return full_filename


# =============================================================================
# Главное окно приложения
# =============================================================================

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, num_states=9, input_alphabet=('a', 'b')):
        super().__init__()
        self.num_states = num_states
        self.input_alphabet = input_alphabet
        self.dark_mode = False
        self.history = []  # История построений
        self.current_min_mealy = None
        self.current_moore_transitions = None
        self.current_moore_initial = None
        self.iter_info = []  # Итерации разбиения (для пошагового режима)
        self.current_iteration = 0
        self.live_preview_timer = QtCore.QTimer(self)
        self.live_preview_timer.setInterval(3000)
        self.live_preview_timer.timeout.connect(self.on_live_preview)
        self.simulation_timer = QtCore.QTimer(self)
        self.simulation_steps = []
        self.simulation_current_index = 0
        self.setWindowTitle("Генератор автоматов Мили/Мура")
        self.resize(1400, 950)
        self.setFont(QFont("Arial", 10))
        QtWidgets.QApplication.setStyle("Fusion")
        self.apply_custom_stylesheet()
        self.setup_ui()
        self.create_menu()
        self.create_toolbar()
        self.create_statusbar()
        self.create_docks()
        self.create_tray_icon()
        self.statusBar().showMessage("Готов к работе")

    def apply_custom_stylesheet(self):
        # Применяем QSS-стили с градиентами и текстурами для современного вида
        custom_style = """
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2b2b2b, stop:1 #1e1e1e);
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3c3f41, stop:1 #2b2b2b);
        }
        QTabBar::tab {
            font-size: 10pt;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c3f41, stop:1 #2b2b2b);
            color: #f0f0f0;
            padding: 8px;
            margin: 2px;
            border-radius: 4px;
        }
        QTabBar::tab:selected {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a5a5a, stop:1 #3c3f41);
            font-weight: bold;
        }
        QPushButton {
            background-color: #3c3f41;
            color: #f0f0f0;
            border: 1px solid #2b2b2b;
            border-radius: 4px;
            padding: 6px;
        }
        QPushButton:hover {
            background-color: #4c4c4c;
        }
        QTableWidget, QTextEdit {
            background-color: #2b2b2b;
            color: #f0f0f0;
        }
        QDockWidget {
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(undock.png);
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c3f41, stop:1 #2b2b2b);
            border: 1px solid #555555;
        }
        """
        self.setStyleSheet(custom_style)

    def setup_ui(self):
        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Вкладка "Ввод"
        self.input_tab = QtWidgets.QWidget()
        input_layout = QtWidgets.QVBoxLayout(self.input_tab)
        self.live_preview_checkbox = QtWidgets.QCheckBox("Автообновление предпросмотра")
        self.live_preview_checkbox.setToolTip("При включении изменения в таблице автоматически обновляют результаты")
        input_layout.addWidget(self.live_preview_checkbox)
        self.table = QtWidgets.QTableWidget(self.num_states, len(self.input_alphabet))
        self.table.setHorizontalHeaderLabels(list(self.input_alphabet))
        self.table.setVerticalHeaderLabels([str(i) for i in range(1, self.num_states + 1)])
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        input_layout.addWidget(self.table)
        self.table.cellChanged.connect(self.on_cell_changed)
        button_layout = QtWidgets.QHBoxLayout()
        self.build_button = QtWidgets.QPushButton("Сохранить и Построить")
        self.build_button.setToolTip("Сохранить данные и построить автоматы")
        self.clear_button = QtWidgets.QPushButton("Стереть")
        self.clear_button.setToolTip("Очистить все поля ввода")
        button_layout.addWidget(self.build_button)
        button_layout.addWidget(self.clear_button)
        input_layout.addLayout(button_layout)
        self.build_button.clicked.connect(self.on_build)
        self.clear_button.clicked.connect(self.on_clear)
        extra_btn_layout = QtWidgets.QHBoxLayout()
        self.gen_test_btn = QtWidgets.QPushButton("Генерация тестов")
        self.gen_test_btn.setToolTip("Заполнить таблицу случайными значениями (реакция: x или y)")
        self.highlight_btn = QtWidgets.QPushButton("Подсветить эквивалентные")
        self.highlight_btn.setToolTip("Подсветить строки с эквивалентными состояниями")
        extra_btn_layout.addWidget(self.gen_test_btn)
        extra_btn_layout.addWidget(self.highlight_btn)
        input_layout.addLayout(extra_btn_layout)
        self.gen_test_btn.clicked.connect(self.generate_random_automaton)
        self.highlight_btn.clicked.connect(self.highlight_equivalent_states)
        self.tab_widget.addTab(self.input_tab, "Ввод")

        # Вкладка "Результаты"
        self.results_tab = QtWidgets.QWidget()
        results_layout = QtWidgets.QVBoxLayout(self.results_tab)
        self.text_output = QtWidgets.QTextEdit()
        self.text_output.setReadOnly(True)
        results_layout.addWidget(self.text_output)
        image_layout = QtWidgets.QHBoxLayout()
        self.mealy_image_label = QtWidgets.QLabel()
        self.moore_image_label = QtWidgets.QLabel()
        self.mealy_image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.moore_image_label.setAlignment(QtCore.Qt.AlignCenter)
        image_layout.addWidget(self.mealy_image_label)
        image_layout.addWidget(self.moore_image_label)
        results_layout.addLayout(image_layout)
        export_layout = QtWidgets.QHBoxLayout()
        self.export_report_btn = QtWidgets.QPushButton("Экспорт отчёта")
        self.export_report_btn.setToolTip("Сохранить отчёт в текстовом файле")
        self.export_html_btn = QtWidgets.QPushButton("Экспорт HTML")
        self.export_html_btn.setToolTip("Сохранить отчёт в формате HTML")
        self.export_images_btn = QtWidgets.QPushButton("Экспорт изображений")
        self.export_images_btn.setToolTip("Сохранить графики автоматов")
        self.stats_btn = QtWidgets.QPushButton("Показать статистику")
        self.stats_btn.setToolTip("Показать статистику минимизированного автомата")
        self.copy_report_btn = QtWidgets.QPushButton("Копировать отчёт")
        self.copy_report_btn.setToolTip("Скопировать текст отчёта в буфер обмена")
        export_layout.addWidget(self.export_report_btn)
        export_layout.addWidget(self.export_html_btn)
        export_layout.addWidget(self.export_images_btn)
        export_layout.addWidget(self.stats_btn)
        export_layout.addWidget(self.copy_report_btn)
        results_layout.addLayout(export_layout)
        self.export_report_btn.clicked.connect(self.export_report)
        self.export_html_btn.clicked.connect(self.export_report_html)
        self.export_images_btn.clicked.connect(self.export_images)
        self.stats_btn.clicked.connect(self.show_statistics)
        self.copy_report_btn.clicked.connect(self.copy_report_to_clipboard)
        self.tab_widget.addTab(self.results_tab, "Результаты")

        # Вкладка "Симуляция"
        self.simulation_tab = QtWidgets.QWidget()
        sim_layout = QtWidgets.QVBoxLayout(self.simulation_tab)
        sim_control_layout = QtWidgets.QHBoxLayout()
        sim_control_layout.addWidget(QtWidgets.QLabel("Тип автомата:"))
        self.sim_type_combo = QtWidgets.QComboBox()
        self.sim_type_combo.addItems(["Мили", "Мура"])
        sim_control_layout.addWidget(self.sim_type_combo)
        sim_control_layout.addWidget(QtWidgets.QLabel("Входная строка:"))
        self.sim_input_line = QtWidgets.QLineEdit()
        self.sim_input_line.setToolTip("Введите входную строку (символы из алфавита)")
        sim_control_layout.addWidget(self.sim_input_line)
        self.simulate_button = QtWidgets.QPushButton("Симулировать")
        self.simulate_button.setToolTip("Запустить симуляцию полностью")
        self.sim_step_button = QtWidgets.QPushButton("Пошаговая симуляция")
        self.sim_step_button.setToolTip("Запустить пошаговую симуляцию")
        sim_control_layout.addWidget(self.simulate_button)
        sim_control_layout.addWidget(self.sim_step_button)
        # Создаём и настраиваем слайдер скорости
        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_slider.setRange(500, 3000)
        self.speed_slider.setValue(1000)
        self.speed_slider.setToolTip("Регулировка скорости пошаговой симуляции (мс)")
        sim_control_layout.addWidget(QtWidgets.QLabel("Скорость:"))
        sim_control_layout.addWidget(self.speed_slider)
        sim_layout.addLayout(sim_control_layout)
        self.sim_current_state_label = QtWidgets.QLabel("Текущее состояние: -")
        sim_layout.addWidget(self.sim_current_state_label)
        self.sim_log_text = QtWidgets.QTextEdit()
        self.sim_log_text.setReadOnly(True)
        sim_layout.addWidget(self.sim_log_text)
        self.simulate_button.clicked.connect(self.on_simulate)
        self.sim_step_button.clicked.connect(self.on_simulate_step_by_step)
        self.tab_widget.addTab(self.simulation_tab, "Симуляция")

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        open_action = QtWidgets.QAction("Открыть...", self)
        open_action.triggered.connect(self.open_file)
        load_session_action = QtWidgets.QAction("Загрузить сессию", self)
        load_session_action.triggered.connect(self.load_session)
        save_session_action = QtWidgets.QAction("Сохранить сессию", self)
        save_session_action.triggered.connect(self.save_session)
        save_report_action = QtWidgets.QAction("Сохранить отчёт...", self)
        save_report_action.triggered.connect(self.export_report)
        recent_menu = QtWidgets.QMenu("Недавние сессии", self)
        recent_menu.addAction("Пока нет записей")
        exit_action = QtWidgets.QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(open_action)
        file_menu.addAction(load_session_action)
        file_menu.addAction(save_session_action)
        file_menu.addAction(save_report_action)
        file_menu.addMenu(recent_menu)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        settings_menu = menubar.addMenu("Настройки")
        toggle_dark_action = QtWidgets.QAction("Переключить тёмную тему", self)
        toggle_dark_action.triggered.connect(self.toggle_dark_mode)
        settings_action = QtWidgets.QAction("Настройки...", self)
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(toggle_dark_action)
        settings_menu.addAction(settings_action)
        view_menu = menubar.addMenu("Вид")
        dock_history_action = QtWidgets.QAction("Показать/Скрыть Историю", self)
        dock_history_action.triggered.connect(lambda: self.toggle_dock(self.dock_history))
        dock_step_action = QtWidgets.QAction("Показать/Скрыть Пошаговое", self)
        dock_step_action.triggered.connect(lambda: self.toggle_dock(self.dock_step))
        view_menu.addAction(dock_history_action)
        view_menu.addAction(dock_step_action)
        help_menu = menubar.addMenu("Справка")
        about_action = QtWidgets.QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = self.addToolBar("Основные действия")
        toolbar.setMovable(False)
        build_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
        clear_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton)
        open_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
        live_icon = self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        build_action = QtWidgets.QAction(build_icon, "Построить", self)
        build_action.triggered.connect(self.on_build)
        clear_action = QtWidgets.QAction(clear_icon, "Стереть", self)
        clear_action.triggered.connect(self.on_clear)
        open_action = QtWidgets.QAction(open_icon, "Открыть файл", self)
        open_action.triggered.connect(self.open_file)
        live_action = QtWidgets.QAction(live_icon, "Live Preview", self)
        live_action.setToolTip("Включить/выключить автообновление предпросмотра")
        live_action.setCheckable(True)
        live_action.toggled.connect(lambda state: self.live_preview_checkbox.setChecked(state))
        toolbar.addAction(build_action)
        toolbar.addAction(clear_action)
        toolbar.addAction(open_action)
        toolbar.addAction(live_action)

    def create_statusbar(self):
        self.clock_label = QtWidgets.QLabel()
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setValue(0)
        self.statusBar().addPermanentWidget(self.clock_label)
        self.statusBar().addPermanentWidget(self.progress_bar)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_clock)
        timer.start(1000)
        self.update_clock()

    def create_docks(self):
        # Док-панель "История построений"
        self.dock_history = QtWidgets.QDockWidget("История построений", self)
        self.dock_history.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.history_widget = QtWidgets.QWidget()
        history_layout = QtWidgets.QVBoxLayout(self.history_widget)
        self.history_table = QtWidgets.QTableWidget(0, 2)
        self.history_table.setHorizontalHeaderLabels(["Время", "Краткое описание"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.history_table.doubleClicked.connect(self.on_history_item_double_clicked)
        history_layout.addWidget(self.history_table)
        dock_btn_layout = QtWidgets.QHBoxLayout()
        self.clear_history_btn = QtWidgets.QPushButton("Очистить")
        self.export_history_btn = QtWidgets.QPushButton("Экспорт")
        dock_btn_layout.addWidget(self.clear_history_btn)
        dock_btn_layout.addWidget(self.export_history_btn)
        history_layout.addLayout(dock_btn_layout)
        self.clear_history_btn.clicked.connect(self.clear_history)
        self.export_history_btn.clicked.connect(self.export_history)
        self.dock_history.setWidget(self.history_widget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dock_history)
        # Док-панель "Пошаговое минимизирование"
        self.dock_step = QtWidgets.QDockWidget("Пошаговое минимизирование", self)
        self.dock_step.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.step_widget = QtWidgets.QWidget()
        step_layout = QtWidgets.QVBoxLayout(self.step_widget)
        control_layout = QtWidgets.QHBoxLayout()
        self.prev_button = QtWidgets.QPushButton("<< Предыдущий")
        self.prev_button.clicked.connect(self.on_prev_iteration)
        self.next_button = QtWidgets.QPushButton("Следующий >>")
        self.next_button.clicked.connect(self.on_next_iteration)
        self.iter_label = QtWidgets.QLabel("Итерация 0 из 0")
        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.iter_label)
        control_layout.addWidget(self.next_button)
        step_layout.addLayout(control_layout)
        self.iter_text = QtWidgets.QTextEdit()
        self.iter_text.setReadOnly(True)
        step_layout.addWidget(self.iter_text)
        self.dock_step.setWidget(self.step_widget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dock_step)

    def create_tray_icon(self):
        # Устанавливаем иконку для системного трей (создаём pixmap, если иконка не найдена)
        icon = QIcon.fromTheme("applications-system")
        if icon.isNull():
            pixmap = QPixmap(64, 64)
            pixmap.fill(QtGui.QColor("blue"))
            icon = QIcon(pixmap)
        self.tray_icon = QtWidgets.QSystemTrayIcon(icon, self)
        tray_menu = QtWidgets.QMenu()
        show_action = tray_menu.addAction("Показать")
        show_action.triggered.connect(self.show)
        hide_action = tray_menu.addAction("Скрыть")
        hide_action.triggered.connect(self.hide)
        exit_action = tray_menu.addAction("Выход")
        exit_action.triggered.connect(QtWidgets.QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setIcon(icon)
        self.tray_icon.show()

    def update_clock(self):
        current_time = QtCore.QDateTime.currentDateTime().toString("hh:mm:ss")
        self.clock_label.setText(current_time)

    def toggle_dark_mode(self):
        if self.dark_mode:
            self.setStyleSheet("")
            self.dark_mode = False
            self.statusBar().showMessage("Светлая тема")
        else:
            dark_stylesheet = """
                QMainWindow { background-color: #2b2b2b; color: #f0f0f0; }
                QWidget { background-color: #3c3f41; color: #f0f0f0; }
                QMenuBar { background-color: #3c3f41; }
                QMenuBar::item { background-color: #3c3f41; }
                QMenuBar::item:selected { background-color: #2b2b2b; }
                QToolBar { background-color: #3c3f41; }
                QTabWidget::pane { border: 1px solid #2b2b2b; }
                QTabBar::tab { background: #3c3f41; padding: 10px; }
                QTabBar::tab:selected { background: #2b2b2b; }
                QTableWidget { background-color: #2b2b2b; gridline-color: #f0f0f0; }
                QTextEdit { background-color: #2b2b2b; }
                QPushButton { background-color: #3c3f41; border: 1px solid #2b2b2b; padding: 5px; }
                QPushButton:hover { background-color: #2b2b2b; }
            """
            self.setStyleSheet(dark_stylesheet)
            self.dark_mode = True
            self.statusBar().showMessage("Тёмная тема включена")



    def show_about(self):
        QtWidgets.QMessageBox.about(self, "О программе",
                                    "<h3>Генератор автоматов Мили/Мура</h3>"
                                    "<p>Разработано с использованием PyQt5 и Graphviz.</p>"
                                    "<p>Версия 4.0 с расширенным функционалом, интерактивной симуляцией, док-панелями, автообновлением предпросмотра, контекстным меню, экспортом HTML, пошаговой симуляцией, копированием отчёта и системным трей.</p>")

    def show_settings(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Настройки")
        layout = QtWidgets.QVBoxLayout(dlg)
        label = QtWidgets.QLabel("Настройки пока не реализованы.\nБудет доступно в будущих версиях.")
        layout.addWidget(label)
        btn = QtWidgets.QPushButton("Закрыть")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec_()

    def open_file(self):
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Открыть файл", "",
                                                            "Text Files (*.txt *.csv);;All Files (*)", options=options)
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for row, line in enumerate(lines):
                    if row >= self.num_states:
                        break
                    parts = line.strip().split(';')
                    for col, part in enumerate(parts):
                        if col >= len(self.input_alphabet):
                            break
                        self.table.setItem(row, col, QtWidgets.QTableWidgetItem(part.strip()))
                self.statusBar().showMessage(f"Файл {filename} успешно загружен")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл: {e}")

    def export_report(self):
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить отчёт", "",
                                                            "Text Files (*.txt);;All Files (*)", options=options)
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.text_output.toPlainText())
                self.statusBar().showMessage(f"Отчёт сохранён в файл: {filename}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчёт: {e}")

    def export_report_html(self):
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить HTML отчёт", "",
                                                            "HTML Files (*.html);;All Files (*)", options=options)
        if filename:
            try:
                html_content = "<html><head><meta charset='utf-8'><title>Отчёт по автоматам</title></head><body>"
                html_content += self.text_output.toPlainText().replace("\n", "<br>")
                html_content += "</body></html>"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                self.statusBar().showMessage(f"HTML отчёт сохранён в файл: {filename}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить HTML отчёт: {e}")

    def export_images(self):
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения изображений", options=options)
        if directory:
            try:
                for file in os.listdir("data"):
                    if file.endswith(".png"):
                        shutil.copy(os.path.join("data", file), directory)
                self.statusBar().showMessage(f"Изображения сохранены в папку: {directory}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить изображения: {e}")

    def save_session(self):
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить сессию", "",
                                                            "JSON Files (*.json);;All Files (*)", options=options)
        if filename:
            try:
                session_data = {
                    "table": [],
                    "output_text": self.text_output.toPlainText(),
                    "sim_input": self.sim_input_line.text(),
                    "sim_log": self.sim_log_text.toPlainText(),
                    "history": self.history
                }
                for row in range(self.num_states):
                    row_data = []
                    for col in range(len(self.input_alphabet)):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    session_data["table"].append(row_data)
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=4)
                self.statusBar().showMessage(f"Сессия сохранена в файл: {filename}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить сессию: {e}")

    def load_session(self):
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Загрузить сессию", "",
                                                            "JSON Files (*.json);;All Files (*)", options=options)
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                for row, row_data in enumerate(session_data.get("table", [])):
                    for col, cell in enumerate(row_data):
                        self.table.setItem(row, col, QtWidgets.QTableWidgetItem(cell))
                self.text_output.setPlainText(session_data.get("output_text", ""))
                self.sim_input_line.setText(session_data.get("sim_input", ""))
                self.sim_log_text.setPlainText(session_data.get("sim_log", ""))
                self.history = session_data.get("history", [])
                self.update_history_table()
                self.statusBar().showMessage(f"Сессия загружена из файла: {filename}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить сессию: {e}")

    def export_history(self):
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Экспортировать историю", "",
                                                            "JSON Files (*.json);;All Files (*)", options=options)
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=4)
                self.statusBar().showMessage(f"История экспортирована в файл: {filename}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать историю: {e}")

    def clear_history(self):
        self.history = []
        self.update_history_table()
        self.statusBar().showMessage("История очищена")

    def update_history_table(self):
        self.history_table.setRowCount(len(self.history))
        for row, entry in enumerate(self.history):
            timestamp_item = QtWidgets.QTableWidgetItem(entry.get("timestamp", ""))
            desc = entry.get("report", "")[:50] + "..." if len(entry.get("report", "")) > 50 else entry.get("report", "")
            desc_item = QtWidgets.QTableWidgetItem(desc)
            self.history_table.setItem(row, 0, timestamp_item)
            self.history_table.setItem(row, 1, desc_item)
        self.history_table.resizeColumnsToContents()

    def on_history_item_double_clicked(self, index):
        row = index.row()
        if 0 <= row < len(self.history):
            entry = self.history[row]
            details = f"Время: {entry.get('timestamp', '')}\n\nОтчёт:\n{entry.get('report', '')}\n\n" \
                      f"Файл Мили: {entry.get('mealy_file', '')}\nФайл Мура: {entry.get('moore_file', '')}\n\nДанные ввода:\n{entry.get('input_table', '')}"
            QtWidgets.QMessageBox.information(self, "Детали записи", details)

    def update_step_by_step_tab(self):
        if self.iter_info:
            total = len(self.iter_info)
            self.iter_label.setText(f"Итерация {self.current_iteration + 1} из {total}")
            text = ""
            iteration_data = self.iter_info[self.current_iteration]
            for i, block in enumerate(iteration_data):
                text += f"Block {i}: {block}\n"
            self.iter_text.setPlainText(text)
        else:
            self.iter_label.setText("Итерация 0 из 0")
            self.iter_text.clear()

    def on_prev_iteration(self):
        if self.iter_info and self.current_iteration > 0:
            self.current_iteration -= 1
            self.update_step_by_step_tab()

    def on_next_iteration(self):
        if self.iter_info and self.current_iteration < len(self.iter_info) - 1:
            self.current_iteration += 1
            self.update_step_by_step_tab()

    def read_table(self):
        mealy = {}
        for state in range(1, self.num_states + 1):
            mealy[str(state)] = {}
            for j, letter in enumerate(self.input_alphabet):
                item = self.table.item(state - 1, j)
                if item is None or item.text().strip() == "":
                    QtWidgets.QMessageBox.warning(self, "Ошибка ввода",
                                                  f"Заполните ячейку для состояния {state}, вход '{letter}'.")
                    return None
                text = item.text().strip()
                if ',' not in text:
                    QtWidgets.QMessageBox.warning(self, "Ошибка ввода",
                                                  f"Неверный формат в состоянии {state}, вход '{letter}'. Ожидается формат 'dest,out'.")
                    return None
                parts = text.split(',')
                if len(parts) != 2:
                    QtWidgets.QMessageBox.warning(self, "Ошибка ввода",
                                                  f"Неверный формат в состоянии {state}, вход '{letter}'. Ожидается формат 'dest,out'.")
                    return None
                dest_str, out_str = parts[0].strip(), parts[1].strip()
                if not dest_str or not out_str:
                    QtWidgets.QMessageBox.warning(self, "Ошибка ввода",
                                                  f"Неверный формат в состоянии {state}, вход '{letter}'. Пустое значение.")
                    return None
                mealy[str(state)][letter] = (dest_str, out_str)
        return mealy

    def generate_random_automaton(self):
        possible_outputs = ["x", "y"]
        for state in range(1, self.num_states + 1):
            for j, letter in enumerate(self.input_alphabet):
                dest = str(random.randint(1, self.num_states))
                out = random.choice(possible_outputs)
                self.table.setItem(state - 1, j, QtWidgets.QTableWidgetItem(f"{dest},{out}"))
        self.statusBar().showMessage("Случайный автомат сгенерирован")

    def highlight_equivalent_states(self):
        mealy = self.read_table()
        if mealy is None:
            return
        blocks = initial_partition(mealy, self.input_alphabet)
        colors = ["#ffcccc", "#ccffcc", "#ccccff", "#ffffcc", "#ffccff",
                  "#ccffff", "#e6ccff", "#ffe6cc", "#ccffe6", "#e6ffcc"]
        for row in range(self.num_states):
            for col in range(len(self.input_alphabet)):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor("white"))
        for i, block in enumerate(blocks):
            color = colors[i % len(colors)]
            for state in block:
                row = int(state) - 1
                for col in range(len(self.input_alphabet)):
                    item = self.table.item(row, col)
                    if item is None:
                        item = QtWidgets.QTableWidgetItem("")
                        self.table.setItem(row, col, item)
                    item.setBackground(QColor(color))
        self.statusBar().showMessage("Эквивалентные состояния подсвечены")

    def on_build(self):
        self.progress_bar.setValue(0)
        mealy = self.read_table()
        if mealy is None:
            return
        QtCore.QTimer.singleShot(500, lambda: self.progress_bar.setValue(50))
        blocks, minimized_map, min_mealy, iter_info = minimize_mealy(mealy, self.input_alphabet)
        QtCore.QTimer.singleShot(1000, lambda: self.progress_bar.setValue(100))
        moore_states, moore_transitions, moore_initial = build_moore(min_mealy, self.input_alphabet)
        output_text = "=== Отчёт по автоматам ===\n\n"
        output_text += f"Количество итераций разбиения: {len(iter_info)}\n\n"
        output_text += "Промежуточные разбиения:\n"
        for idx, it in enumerate(iter_info, 1):
            output_text += f"  Итерация {idx}: {it}\n"
        output_text += "\nФинальное разбиение:\n"
        for i, block in enumerate(blocks):
            output_text += f"  Block {i}: {sorted(block, key=int)}\n"
        output_text += "\nОтображение состояний в представителей:\n"
        for s in sorted(minimized_map.keys(), key=int):
            output_text += f"  {s} -> {minimized_map[s]}\n"
        output_text += f"\nКоличество состояний минимизированного автомата: {len(min_mealy)}\n"
        output_text += "Минимизированный автомат Мили (нормализованный):\n"
        output_text += "State\t a\t b\n"
        for s in sorted(min_mealy.keys(), key=int):
            da, oa = min_mealy[s]['a']
            db, ob = min_mealy[s]['b']
            output_text += f"  {s}\t {da}/{oa}\t {db}/{ob}\n"
        output_text += f"\nКоличество состояний автомата Мура: {len(moore_states)}\n"
        output_text += "\nПереходы автомата Мура:\n"
        for s in sorted(moore_transitions.keys()):
            row_desc = []
            for letter in self.input_alphabet:
                row_desc.append(f"{letter} -> {moore_transitions[s][letter]}")
            output_text += f"  {s}: " + ",  ".join(row_desc) + "\n"
        output_text += f"\nНачальное состояние автомата Мура: {moore_initial}\n"
        self.text_output.setPlainText(output_text)

        self.current_min_mealy = min_mealy
        self.current_moore_transitions = moore_transitions
        self.current_moore_initial = moore_initial

        mealy_filename = visualize_mealy(min_mealy, self.input_alphabet, filename='minimized_mealy_user_input')
        moore_filename = visualize_moore(moore_states, moore_transitions, moore_initial, filename='moore_user_input')

        mealy_pixmap = QPixmap(mealy_filename + ".png")
        moore_pixmap = QPixmap(moore_filename + ".png")
        self.mealy_image_label.setPixmap(mealy_pixmap.scaled(500, 400, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        self.moore_image_label.setPixmap(moore_pixmap.scaled(500, 400, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

        self.tab_widget.setCurrentWidget(self.results_tab)
        self.statusBar().showMessage("Автоматы успешно построены")
        self.progress_bar.setValue(0)

        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        input_table = []
        for row in range(self.num_states):
            row_data = []
            for col in range(len(self.input_alphabet)):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            input_table.append(row_data)
        history_entry = {
            "timestamp": timestamp,
            "report": output_text,
            "mealy_file": mealy_filename + ".png",
            "moore_file": moore_filename + ".png",
            "input_table": input_table
        }
        self.history.append(history_entry)
        self.update_history_table()

        self.iter_info = iter_info
        self.current_iteration = 0
        self.update_step_by_step_tab()

    def on_clear(self):
        for row in range(self.num_states):
            for col in range(len(self.input_alphabet)):
                self.table.setItem(row, col, QtWidgets.QTableWidgetItem(""))
        self.text_output.clear()
        self.mealy_image_label.clear()
        self.moore_image_label.clear()
        self.sim_input_line.clear()
        self.sim_log_text.clear()
        self.statusBar().showMessage("Ввод очищен")

    def on_simulate(self):
        sim_type = self.sim_type_combo.currentText()
        input_str = self.sim_input_line.text().strip()
        if not input_str:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите входную строку для симуляции")
            return
        if sim_type == "Мили":
            if not self.current_min_mealy:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Сначала постройте автомат")
                return
            current_state = "1" if "1" in self.current_min_mealy else sorted(self.current_min_mealy.keys())[0]
            log = [f"Начальное состояние: {current_state}"]
            for ch in input_str:
                if ch not in self.input_alphabet:
                    log.append(f"Ошибка: символ '{ch}' не входит в алфавит {self.input_alphabet}")
                    break
                next_state, output = self.current_min_mealy[current_state][ch]
                log.append(f"При входе '{ch}': {current_state} -> {next_state}, вывод: {output}")
                current_state = next_state
            log.append(f"Итоговое состояние: {current_state}")
            self.sim_log_text.setPlainText("\n".join(log))
            self.sim_current_state_label.setText(f"Текущее состояние: {current_state}")
        elif sim_type == "Мура":
            if not self.current_moore_transitions:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Сначала постройте автомат")
                return
            current_state = self.current_moore_initial
            log = [f"Начальное состояние: {current_state}"]
            for ch in input_str:
                if ch not in self.input_alphabet:
                    log.append(f"Ошибка: символ '{ch}' не входит в алфавит {self.input_alphabet}")
                    break
                try:
                    next_state = self.current_moore_transitions[current_state][ch]
                except KeyError:
                    log.append(f"Ошибка: нет перехода для символа '{ch}' в состоянии {current_state}")
                    break
                log.append(f"При входе '{ch}': {current_state} -> {next_state}")
                current_state = next_state
            log.append(f"Итоговое состояние: {current_state}")
            self.sim_log_text.setPlainText("\n".join(log))
            self.sim_current_state_label.setText(f"Текущее состояние: {current_state}")

    def on_simulate_step_by_step(self):
        sim_type = self.sim_type_combo.currentText()
        input_str = self.sim_input_line.text().strip()
        if not input_str:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите входную строку для симуляции")
            return
        if sim_type == "Мили":
            if not self.current_min_mealy:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Сначала постройте автомат")
                return
            current_state = "1" if "1" in self.current_min_mealy else sorted(self.current_min_mealy.keys())[0]
            steps = []
            steps.append((current_state, f"Начальное состояние: {current_state}"))
            for ch in input_str:
                if ch not in self.input_alphabet:
                    steps.append((current_state, f"Ошибка: символ '{ch}' не входит в алфавит"))
                    break
                next_state, output = self.current_min_mealy[current_state][ch]
                steps.append((next_state, f"При входе '{ch}': {current_state} -> {next_state}, вывод: {output}"))
                current_state = next_state
            steps.append((current_state, f"Итоговое состояние: {current_state}"))
        else:
            if not self.current_moore_transitions:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Сначала постройте автомат")
                return
            current_state = self.current_moore_initial
            steps = []
            steps.append((current_state, f"Начальное состояние: {current_state}"))
            for ch in input_str:
                if ch not in self.input_alphabet:
                    steps.append((current_state, f"Ошибка: символ '{ch}' не входит в алфавит"))
                    break
                try:
                    next_state = self.current_moore_transitions[current_state][ch]
                except KeyError:
                    steps.append((current_state, f"Ошибка: нет перехода для '{ch}' в состоянии {current_state}"))
                    break
                steps.append((next_state, f"При входе '{ch}': {current_state} -> {next_state}"))
                current_state = next_state
            steps.append((current_state, f"Итоговое состояние: {current_state}"))
        self.simulation_steps = steps
        self.simulation_current_index = 0
        self.sim_log_text.clear()
        self.sim_current_state_label.setText(f"Текущее состояние: {steps[0][0]}")
        self.simulation_timer.timeout.connect(self.simulation_step)
        self.simulation_timer.start(1000)
        self.sim_step_button.setEnabled(False)

    def simulation_step(self):
        if self.simulation_current_index < len(self.simulation_steps):
            state, msg = self.simulation_steps[self.simulation_current_index]
            self.sim_log_text.append(msg)
            self.sim_current_state_label.setText(f"Текущее состояние: {state}")
            self.simulation_current_index += 1
        else:
            self.simulation_timer.stop()
            self.sim_step_button.setEnabled(True)

    def copy_report_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.text_output.toPlainText())
        self.statusBar().showMessage("Отчёт скопирован в буфер обмена", 3000)

    def toggle_dock(self, dock_widget):
        visible = not dock_widget.isVisible()
        dock_widget.setVisible(visible)
        effect = QtWidgets.QGraphicsOpacityEffect()
        dock_widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(500)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def show_statistics(self):
        if self.current_min_mealy is None:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Сначала постройте автомат")
            return
        states_mealy = len(self.current_min_mealy)
        transitions_mealy = states_mealy * len(self.input_alphabet)
        states_moore = len(self.current_moore_transitions)
        transitions_moore = sum(len(transitions) for transitions in self.current_moore_transitions.values())
        message = f"Минимизированный автомат Мили:\n  Состояний: {states_mealy}\n  Переходов: {transitions_mealy}\n\n"
        message += f"Автомат Мура:\n  Состояний: {states_moore}\n  Переходов: {transitions_moore}"
        QtWidgets.QMessageBox.information(self, "Статистика автомата", message)


    def on_cell_changed(self, row, col):
        if self.live_preview_checkbox.isChecked():
            self.table.blockSignals(True)
            self.live_preview_timer.start()
            self.table.blockSignals(False)

    def on_live_preview(self):
        self.live_preview_timer.stop()
        self.on_build()

    def show_table_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if index.isValid():
            menu = QtWidgets.QMenu()
            clear_action = menu.addAction("Очистить ячейку")
            random_action = menu.addAction("Случайное значение")
            action = menu.exec_(self.table.viewport().mapToGlobal(pos))
            if action == clear_action:
                self.table.setItem(index.row(), index.column(), QtWidgets.QTableWidgetItem(""))
            elif action == random_action:
                possible_outputs = ["x", "y"]
                dest = str(random.randint(1, self.num_states))
                out = random.choice(possible_outputs)
                self.table.setItem(index.row(), index.column(), QtWidgets.QTableWidgetItem(f"{dest},{out}"))

    def update_history_table(self):
        self.history_table.setRowCount(len(self.history))
        for row, entry in enumerate(self.history):
            timestamp_item = QtWidgets.QTableWidgetItem(entry.get("timestamp", ""))
            desc = entry.get("report", "")[:50] + "..." if len(entry.get("report", "")) > 50 else entry.get("report", "")
            desc_item = QtWidgets.QTableWidgetItem(desc)
            self.history_table.setItem(row, 0, timestamp_item)
            self.history_table.setItem(row, 1, desc_item)
        self.history_table.resizeColumnsToContents()

    def on_history_item_double_clicked(self, index):
        row = index.row()
        if 0 <= row < len(self.history):
            entry = self.history[row]
            details = f"Время: {entry.get('timestamp', '')}\n\nОтчёт:\n{entry.get('report', '')}\n\n" \
                      f"Файл Мили: {entry.get('mealy_file', '')}\nФайл Мура: {entry.get('moore_file', '')}\n\nДанные ввода:\n{entry.get('input_table', '')}"
            QtWidgets.QMessageBox.information(self, "Детали записи", details)

    def update_step_by_step_tab(self):
        if self.iter_info:
            total = len(self.iter_info)
            self.iter_label.setText(f"Итерация {self.current_iteration + 1} из {total}")
            text = ""
            iteration_data = self.iter_info[self.current_iteration]
            for i, block in enumerate(iteration_data):
                text += f"Block {i}: {block}\n"
            self.iter_text.setPlainText(text)
        else:
            self.iter_label.setText("Итерация 0 из 0")
            self.iter_text.clear()

    def on_prev_iteration(self):
        if self.iter_info and self.current_iteration > 0:
            self.current_iteration -= 1
            self.update_step_by_step_tab()

    def on_next_iteration(self):
        if self.iter_info and self.current_iteration < len(self.iter_info) - 1:
            self.current_iteration += 1
            self.update_step_by_step_tab()

    def read_table(self):
        mealy = {}
        for state in range(1, self.num_states + 1):
            mealy[str(state)] = {}
            for j, letter in enumerate(self.input_alphabet):
                item = self.table.item(state - 1, j)
                if item is None or item.text().strip() == "":
                    QtWidgets.QMessageBox.warning(self, "Ошибка ввода",
                                                  f"Заполните ячейку для состояния {state}, вход '{letter}'.")
                    return None
                text = item.text().strip()
                if ',' not in text:
                    QtWidgets.QMessageBox.warning(self, "Ошибка ввода",
                                                  f"Неверный формат в состоянии {state}, вход '{letter}'. Ожидается формат 'dest,out'.")
                    return None
                parts = text.split(',')
                if len(parts) != 2:
                    QtWidgets.QMessageBox.warning(self, "Ошибка ввода",
                                                  f"Неверный формат в состоянии {state}, вход '{letter}'. Ожидается формат 'dest,out'.")
                    return None
                dest_str, out_str = parts[0].strip(), parts[1].strip()
                if not dest_str or not out_str:
                    QtWidgets.QMessageBox.warning(self, "Ошибка ввода",
                                                  f"Неверный формат в состоянии {state}, вход '{letter}'. Пустое значение.")
                    return None
                mealy[str(state)][letter] = (dest_str, out_str)
        return mealy

    def copy_report_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.text_output.toPlainText())
        self.statusBar().showMessage("Отчёт скопирован в буфер обмена", 3000)

# =============================================================================
# Запуск приложения
# =============================================================================

def main():
    app = QtWidgets.QApplication(sys.argv)
    splash_pix = QPixmap(400, 300)
    splash_pix.fill(QtGui.QColor("black"))
    painter = QtGui.QPainter(splash_pix)
    gradient = QtGui.QLinearGradient(0, 0, 400, 300)
    gradient.setColorAt(0, QtGui.QColor("#2b2b2b"))
    gradient.setColorAt(1, QtGui.QColor("#1e1e1e"))
    painter.fillRect(splash_pix.rect(), gradient)
    painter.setPen(QtGui.QColor("white"))
    painter.setFont(QFont("Arial", 20))
    painter.drawText(splash_pix.rect(), QtCore.Qt.AlignCenter, "Загрузка приложения...")
    painter.end()
    splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()
    main_win = MainWindow(num_states=9, input_alphabet=('a', 'b'))
    QtCore.QTimer.singleShot(2000, splash.close)
    main_win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
