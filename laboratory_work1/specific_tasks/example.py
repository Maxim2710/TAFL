import graphviz
from copy import deepcopy

# =============================================================================
# 1. Задание исходного автомата Мили (состояния 1...9)
# =============================================================================

# Представляем автомат Мили в виде словаря:
#   mealy[state][input] = (destination_state, output)
mealy = {
    '1': {'a': ('4', 'x'), 'b': ('7', 'y')},
    '2': {'a': ('3', 'y'), 'b': ('4', 'y')},
    '3': {'a': ('7', 'x'), 'b': ('9', 'x')},
    '4': {'a': ('5', 'x'), 'b': ('9', 'y')},
    '5': {'a': ('8', 'x'), 'b': ('7', 'y')},
    '6': {'a': ('7', 'x'), 'b': ('9', 'x')},
    '7': {'a': ('2', 'y'), 'b': ('8', 'x')},
    '8': {'a': ('5', 'x'), 'b': ('9', 'y')},
    '9': {'a': ('2', 'y'), 'b': ('5', 'x')}
}

alphabet = ['a', 'b']

# =============================================================================
# 2. Исключение явно эквивалентных состояний (6 и 8)
#    и корректировка переходов:
#
#   - Состояния 3 и 6 имеют одинаковые реакции и переходы ⇒ удаляем 6,
#     заменяя все переходы 6 → 3.
#   - Состояния 4 и 8 эквивалентны ⇒ удаляем 8, заменяя все переходы 8 → 4.
# =============================================================================

# Создадим копию исходного автомата для преобразования
mealy_reduced = deepcopy(mealy)

# Функция замены в переходах: если встречается state_to_replace, заменить на replacement.
def replace_state(transitions, state_to_replace, replacement):
    for s in transitions:
        for letter in transitions[s]:
            dest, out = transitions[s][letter]
            if dest == state_to_replace:
                transitions[s][letter] = (replacement, out)

# Заменяем переходы: 6 -> 3 и 8 -> 4
replace_state(mealy_reduced, '6', '3')
replace_state(mealy_reduced, '8', '4')

# Удаляем состояния 6 и 8 как источники переходов
for s in ['6', '8']:
    if s in mealy_reduced:
        del mealy_reduced[s]

# Итоговый автомат содержит состояния: 1,2,3,4,5,7,9
states = sorted(mealy_reduced.keys(), key=int)

# =============================================================================
# 3. Минимизация автомата Мили алгоритмом Ауфенкампа–Хона (π‑разбиений)
#
#    Шаг 1. Формируем начальное разбиение π1 по «выходным подписям»
#         для каждого состояния: собираем кортеж (out_a, out_b).
#
#    Получаем:
#      • Для state 1: ('x','y')
#      • Для state 2: ('y','y')
#      • Для state 3: ('x','x')
#      • Для state 4: ('x','y')
#      • Для state 5: ('x','y')
#      • Для state 7: ('y','x')
#      • Для state 9: ('y','x')
#
#    Таким образом:
#       AXX = {3}
#       BXY = {1,4,5}
#       CYX = {7,9}
#       DYY = {2}
#
#    Шаг 2. Проверяем, что для каждого входного символа переходы из состояний
#            одного класса попадают в один и тот же класс.
#            (В данном случае расщепление не требуется.)
# =============================================================================

# Начальное разбиение: группировка по кортежу выходов
def initial_partition(mealy_dict, alphabet):
    partition = {}
    for s in mealy_dict:
        # для каждого входного символа получаем выход (reaction)
        signature = tuple(mealy_dict[s][letter][1] for letter in alphabet)
        partition.setdefault(signature, set()).add(s)
    return list(partition.values())

# Функция, создающая отображение state->block_index
def state_to_block_map(blocks):
    mapping = {}
    for i, block in enumerate(blocks):
        for s in block:
            mapping[s] = i
    return mapping

# Функция одного шага расщепления блока
def refine_blocks(blocks, mealy_dict, alphabet):
    new_blocks = []
    state_block = state_to_block_map(blocks)
    for block in blocks:
        # Если блок содержит одно состояние, оставить как есть
        if len(block) == 1:
            new_blocks.append(block)
        else:
            # Группируем состояния из блока по «подписи переходов»
            groups = {}
            for s in block:
                # Для каждого входного символа смотрим, в какой блок попадает целевое состояние
                trans_sig = tuple(state_block[mealy_dict[s][letter][0]] for letter in alphabet)
                groups.setdefault(trans_sig, set()).add(s)
            new_blocks.extend(groups.values())
    return new_blocks

# Инициализируем разбиение π1
blocks = initial_partition(mealy_reduced, alphabet)
print("Начальное разбиение (π1):")
for i, block in enumerate(blocks):
    print(f"  Block {i}: {sorted(block)}")

# Выполняем последовательное расщепление блоков (максимум 8 шагов, здесь требуется 1 шаг)
while True:
    new_blocks = refine_blocks(blocks, mealy_reduced, alphabet)
    # Если разбиение не изменилось – завершаем алгоритм
    if sorted([sorted(b) for b in new_blocks]) == sorted([sorted(b) for b in blocks]):
        break
    blocks = new_blocks

print("\nФинальное разбиение:")
for i, block in enumerate(blocks):
    print(f"  Block {i}: {sorted(block)}")

# Для дальнейшего построения минимизированного автомата выбираем представителя для каждого блока.
# Согласно разбору, целевое разбиение:
#   • Блок AXX: {3}       → назначим представителем '3'
#   • Блок BXY: {1,4,5}    → представителем '1'
#   • Блок CYX: {7,9}      → представителем '7'
#   • Блок DYY: {2}        → представителем '2'
#
# Если в блоке несколько состояний, выбираем минимальное (по int) как представителя.
minimized_map = {}
for block in blocks:
    rep = min(block, key=int)
    for s in block:
        minimized_map[s] = rep

print("\nОтображение состояний на представителя минимизированного автомата:")
for s in sorted(minimized_map.keys(), key=int):
    print(f"  {s} → {minimized_map[s]}")

# =============================================================================
# 4. Построение нормализованного минимизированного автомата Мили
#
#    Для каждого представителя формируем переходы:
#      Из состояния rep по входу letter:
#         (dest, out) = mealy_reduced[rep][letter]
#         Новый dest = minimized_map[dest]
#
#    Получаем таблицу (с прежними обозначениями состояний):
#
#         X\S    1       2       3       7
#         a      1/x     3/y     7/x     2/y
#         b      7/y     1/y     7/x     1/x
# =============================================================================

minimized_states = sorted(set(minimized_map.values()), key=int)
min_mealy = {}

for rep in minimized_states:
    # Найдём произвольное представление из блока (оно единственное, если блок-состояние)
    # Ищем любое s, для которого minimized_map[s] == rep
    s_candidate = [s for s in mealy_reduced if minimized_map[s] == rep][0]
    min_mealy[rep] = {}
    for letter in alphabet:
        dest, out = mealy_reduced[s_candidate][letter]
        # Переход ведёт в представителя блока, куда попадает dest
        new_dest = minimized_map[dest]
        min_mealy[rep][letter] = (new_dest, out)

print("\nМинимизированный автомат Мили:")
print("State\t", "\t".join(alphabet))
for s in sorted(min_mealy.keys(), key=int):
    row = []
    for letter in alphabet:
        dest, out = min_mealy[s][letter]
        row.append(f"{dest}/{out}")
    print(f"  {s}\t" + "\t".join(row))

# =============================================================================
# 5. Визуализация минимизированного автомата Мили с помощью Graphviz
# =============================================================================

mealy_graph = graphviz.Digraph(name='Minimized_Mealy', format='png')
mealy_graph.attr(rankdir='LR', size='8,5')

# Добавляем узлы
for s in sorted(min_mealy.keys(), key=int):
    mealy_graph.node(s)
# Начальное состояние – выбираем state '1'
mealy_graph.node('', shape='none')
mealy_graph.edge('', '1')

# Добавляем переходы с метками "input / output"
for s in sorted(min_mealy.keys(), key=int):
    for letter in alphabet:
        dest, out = min_mealy[s][letter]
        mealy_graph.edge(s, dest, label=f"{letter} / {out}")

# Сохраняем граф (файл "minimized_mealy.png")
mealy_graph.render('minimized_mealy', view=True)

# =============================================================================
# 6. Построение автомата Мура (автомат 2-го рода) на основе минимизированного автомата Мили
#
#    Преобразование по схеме:
#    – Если минимизированное состояние достигается с разными реакциями,
#      оно разбивается на совокупность состояний в автомате Мура.
#
#    В нашем случае:
#       * Состояние 1 (блок BXY) появляется с выходами:
#             при переходе: 1 --a--> 1 даёт x, а 2 --b--> 1 даёт y.
#             → создаём два состояния: "11" (выход x) и "12" (выход y)
#       * Состояние 7 (блок CYX) появляется с переходами, дающими x и y:
#             → создаём "71" (выход x) и "72" (выход y)
#       * Состояния 2 и 3 однозначны (выход y) и остаются без разбиения.
#
#    Далее для каждого состояния Мура (кортеж (q, reaction)) устанавливаем переходы:
#       Если в минимизированном автомате из q по входу letter переходим в (r, out),
#       то в автомате Мура из копии (q, *) по letter переход идет в ту копию r, у которой выход равен out.
# =============================================================================

# Сначала собираем для каждого минимизированного состояния все реакции,
# которыми оно достигается как целевое в переходах минимизированного автомата.
moore_reactions = { s: set() for s in min_mealy }
for s in min_mealy:
    for letter in alphabet:
        dest, out = min_mealy[s][letter]
        moore_reactions[dest].add(out)

# Для состояния, являющегося начальным (minimized state '1'), оно может не иметь входящих переходов,
# поэтому добавим произвольное значение (выберем, например, реакцию 'x')
if not moore_reactions['1']:
    moore_reactions['1'].add('x')

# Для наглядности будем именовать копии следующим образом:
#   Если для состояния s имеются два выхода, то:
#       при выходе 'x' → имя: s1   (например, для 1: "11")
#       при выходе 'y' → имя: s2   (например, для 1: "12")
#   Если только один выход, оставляем имя s.
def get_moore_name(state, reaction):
    # Предполагаем, что реакции только 'x' и 'y'
    mapping = {'x': '1', 'y': '2'}
    # Если у state несколько вариантов – создаём новое имя, иначе возвращаем state
    if len(moore_reactions[state]) > 1:
        return state + mapping[reaction]
    else:
        return state

# Создадим список (и словарь) состояний автомата Мура:
# Ключ – кортеж (minimized_state, reaction), значение – имя нового состояния
moore_states = {}
for s in min_mealy:
    for reaction in moore_reactions[s]:
        moore_states[(s, reaction)] = get_moore_name(s, reaction)

print("\nКопии состояний для автомата Мура:")
for key, name in moore_states.items():
    print(f"  {key} → {name}")

# Теперь определяем переходы автомата Мура.
# Для каждого нового состояния (q, r) и для каждого входного символа letter:
#   смотрим переход в минимизированном автомате: q --(letter/out)--> (dest, out)
#   и назначаем: (q, r) --letter--> (dest, out)
moore_transitions = {}
for (q, r) in moore_states:
    current_name = moore_states[(q, r)]
    moore_transitions[current_name] = {}
    for letter in alphabet:
        dest, out = min_mealy[q][letter]
        target_name = moore_states[(dest, out)]
        moore_transitions[current_name][letter] = target_name

print("\nПереходы автомата Мура:")
for s in sorted(moore_transitions.keys()):
    print(f"  {s}: ", end='')
    for letter in alphabet:
        print(f"{letter} → {moore_transitions[s][letter]}  ", end='')
    print()

# Выбор начального состояния автомата Мура.
# Согласно разбору, начальному состоянию минимизированного автомата (1) соответствуют копии "11" и "12",
# выбираем произвольную, например, "11".
moore_initial = moore_states[('1', 'x')]

# =============================================================================
# 7. Визуализация автомата Мура с помощью Graphviz
# =============================================================================

moore_graph = graphviz.Digraph(name='Moore', format='png')
moore_graph.attr(rankdir='LR', size='8,5')

# Добавляем узлы автомата Мура: имя узла и выход, указанный в подписи
for (s, r), name in moore_states.items():
    label = f"{name}\n({r})" if len(moore_reactions[s]) > 1 else f"{name}\n({list(moore_reactions[s])[0]})"
    moore_graph.node(name, label=label)

# Начальное состояние – moore_initial
moore_graph.node('', shape='none')
moore_graph.edge('', moore_initial)

# Добавляем переходы (помечаем только входной символ, т.к. выход – ассоциирован с узлом)
for s in moore_transitions:
    for letter in alphabet:
        moore_graph.edge(s, moore_transitions[s][letter], label=letter)

# Сохраняем граф (файл "moore.png")
moore_graph.render('moore', view=True)
